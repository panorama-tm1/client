"""Push an encrypted TM1 export straight to a Panorama server.

Command-line alternative to the "Update data" modal of the web app: same
channel (worker-io Socket.IO, event `start_import`), same checks, same
import queue. Logs stream in the terminal until the import ends.

Install:
    pip install "python-socketio[client]" requests

Usage:
    python push_data.py --list
    python push_data.py --file MyServer_2026-10-11.txt --instance my_server

Parameters can also come from the environment:
    PANORAMA_URL       default https://dev-demo.panorama-tm1.com
    PANORAMA_TOKEN     session token, skips the login
    PANORAMA_EMAIL     login email
    PANORAMA_PASSWORD  login password (prompted when missing)

Exit code: 0 import completed, 1 import failed, 2 bad input or connection.
"""

import argparse
import getpass
import os
import sys
import threading
import time

import requests
import socketio

DEFAULT_URL = "https://dev-demo.panorama-tm1.com"
SOCKET_PATH = "worker/socket.io"

# Same ceiling as the front and worker-io (MAX_ENCRYPTED_IMPORT_BYTES).
MAX_BYTES = 100 * 1024 * 1024

# Same labels as the front's ImportModal (worker-io currentStep 0..4).
IMPORT_STEPS = ["Nodes", "Dependencies", "Rules", "Processes", "Cleanup"]


def fail(message, code=2):
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(code)


# ─── data-api (HTTP) ────────────────────────────────────────────────────────

def login(base_url, email, password):
    r = requests.post(f"{base_url}/api/auth/login",
                      json={"email": email, "password": password}, timeout=30)
    if r.status_code != 200:
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        fail(f"login refused ({r.status_code}): {body.get('message', r.text[:200])}")
    return r.json()["token"]


def logout(base_url, token):
    try:
        requests.post(f"{base_url}/api/auth/logout", json={"token": token}, timeout=10)
    except requests.RequestException:
        pass


def list_instances(base_url, token):
    r = requests.get(f"{base_url}/api/instances",
                     headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if r.status_code == 401:
        fail("token invalid or expired")
    r.raise_for_status()
    return r.json()


def print_instances(instances):
    if not instances:
        print("No server accessible with this account.")
        return
    width = max(len(i["instance_id"]) for i in instances)
    for i in instances:
        print(f"  {i['instance_id']:<{width}}  {i.get('name') or ''}")


def pick_instance(instances):
    if not sys.stdin.isatty():
        fail("--instance is required (run with --list to see the ids)")
    for n, i in enumerate(instances, 1):
        print(f"  {n}. {i['instance_id']}  {i.get('name') or ''}")
    choice = input("Server number: ").strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(instances):
        fail("invalid choice")
    return instances[int(choice) - 1]["instance_id"]


# ─── File ───────────────────────────────────────────────────────────────────

def read_export(path):
    if not os.path.isfile(path):
        fail(f"file not found: {path}")
    size = os.path.getsize(path)
    if size > MAX_BYTES:
        fail(f"file too large ({size / 1048576:.1f} MB, maximum 100 MB)")
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    # The client's output is a JSON array of base64 RSA chunks. Catch the
    # obvious mistake (raw JSON, wrong file) before it takes a queue slot.
    stripped = data.strip()
    if not (stripped.startswith("[") and stripped.endswith("]")):
        fail("not an encrypted TM1 export (expected the .txt produced by the client)")
    return data, size


# ─── worker-io (Socket.IO) ──────────────────────────────────────────────────

def push(base_url, token, instance_id, data, timeout):
    sio = socketio.Client(reconnection=False)
    first_status = threading.Event()
    done = threading.Event()
    state = {"busy": False, "step": None, "queue": None, "result": None, "error": None}

    @sio.event
    def connect_error(err):
        reason = err.get("message") if isinstance(err, dict) else err
        state["error"] = ("token invalid or expired" if reason == "unauthorized"
                          else f"connection refused by worker-io ({reason})")
        done.set()

    @sio.on("status")
    def on_status(status):
        current = status.get("currentServer")
        queue = status.get("queue") or []
        if not first_status.is_set():
            state["busy"] = current == instance_id or instance_id in queue
            first_status.set()
            return
        if current == instance_id:
            step = status.get("currentStep", 0)
            if step != state["step"] and 0 <= step < len(IMPORT_STEPS):
                state["step"] = step
                print(f"[{step + 1}/{len(IMPORT_STEPS)}] {IMPORT_STEPS[step]}")
        elif instance_id in queue:
            position = queue.index(instance_id) + 1
            if position != state["queue"]:
                state["queue"] = position
                print(f"Queued, position {position}")

    @sio.on("log")
    def on_log(payload):
        if payload.get("instanceId") == instance_id:
            for line in str(payload.get("message", "")).splitlines():
                print(f"  {line}")

    @sio.on(f"error:{instance_id}")
    def on_error(payload):
        state["error"] = payload.get("error") or payload.get("message") or "import failed"
        done.set()

    @sio.on("task_completed")
    def on_completed(task):
        if task.get("instanceId") == instance_id and task.get("type") == "IMPORT":
            state["result"] = task.get("status")
            if task.get("status") == "failed" and not state["error"]:
                state["error"] = task.get("error") or "import failed"
            done.set()

    try:
        sio.connect(base_url, socketio_path=SOCKET_PATH, auth={"token": token},
                    transports=["websocket"], wait_timeout=30)
    except socketio.exceptions.ConnectionError as e:
        fail(state["error"] or f"cannot reach worker-io: {e}")

    try:
        sio.emit("get_status")
        if not first_status.wait(15):
            fail("no status received from worker-io")
        if state["busy"]:
            fail(f"an import is already running or queued for '{instance_id}', retry once it ends")

        sio.emit("subscribe_logs", {"instanceId": instance_id})
        sio.emit("start_import", {"instanceId": instance_id, "data": data})
        print("File sent, waiting for the server")

        if not done.wait(timeout):
            fail(f"no result after {timeout}s, the import may still be running (check the web app)")
    finally:
        try:
            sio.emit("unsubscribe_logs", {"instanceId": instance_id})
        except Exception:
            pass
        sio.disconnect()

    if state["error"]:
        fail(state["error"], code=1)
    return state["result"] == "completed"


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Push an encrypted TM1 export to Panorama.")
    parser.add_argument("--url", default=os.environ.get("PANORAMA_URL", DEFAULT_URL),
                        help=f"Panorama base URL (default {DEFAULT_URL})")
    parser.add_argument("--file", help="encrypted export (.txt) produced by the client")
    parser.add_argument("--instance", help="target instance_id (see --list)")
    parser.add_argument("--list", action="store_true", help="list accessible servers and exit")
    parser.add_argument("--token", default=os.environ.get("PANORAMA_TOKEN"),
                        help="session token (skips the login)")
    parser.add_argument("--email", default=os.environ.get("PANORAMA_EMAIL"), help="login email")
    parser.add_argument("--timeout", type=int, default=3600,
                        help="seconds to wait for the import to end (default 3600)")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    if not args.list and not args.file:
        parser.error("--file is required (or --list)")

    # Read the file before logging in, so a wrong path costs nothing.
    data, size = read_export(args.file) if args.file else (None, 0)

    token, logged_in = args.token, False
    if not token:
        email = args.email or input("Email: ").strip()
        password = os.environ.get("PANORAMA_PASSWORD") or getpass.getpass("Password: ")
        token, logged_in = login(base_url, email, password), True

    try:
        instances = list_instances(base_url, token)
        if args.list:
            print_instances(instances)
            return 0

        instance_id = args.instance or pick_instance(instances)
        if instance_id not in {i["instance_id"] for i in instances}:
            fail(f"unknown instance '{instance_id}' or no access (run with --list)")

        print(f"Pushing {os.path.basename(args.file)} ({size / 1048576:.2f} MB) to {instance_id} on {base_url}")
        started = time.time()
        push(base_url, token, instance_id, data, args.timeout)
        print(f"Import completed in {time.time() - started:.0f}s")
        return 0
    finally:
        if logged_in:
            logout(base_url, token)


if __name__ == "__main__":
    sys.exit(main())
