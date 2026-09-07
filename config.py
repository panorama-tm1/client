"""Application configuration and constants."""

import sys
from pathlib import Path


# ── instance key ────────────────────────────────────────────────────────────
# The public key is NOT hardcoded. Every Panorama instance generates its own
# RSA pair when it is deployed (little-brother, Scripts/Initialize/04), and
# worker-io rejects an export encrypted for a different instance. So the key
# travels as a data file that the build stamps:
#
#   from source  -> panorama_key.pem as committed here (the dev-demo pair)
#   per instance -> .github/workflows/build-client.yml overwrites it with that
#                   instance's public_key.pem, then packs it into the exe
#
# PyInstaller --onefile unpacks bundled data under sys._MEIPASS at startup;
# running from source there is no _MEIPASS and the file sits next to us.
def _bundled(name: str) -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / name


def _read_key() -> str:
    path = _bundled("panorama_key.pem")
    try:
        key = path.read_text(encoding="utf-8").strip()
    except OSError as e:
        raise SystemExit(
            "Panorama: import key missing from this build. Download the "
            f"executable again from your Panorama instance. ({e})"
        )
    # An empty or truncated stamp would only surface at step 6, after the user
    # has already typed their TM1 credentials and waited through the fetch.
    if "BEGIN RSA PUBLIC KEY" not in key:
        raise SystemExit(
            f"Panorama: import key at {path} is not a PKCS1 RSA public key. "
            "This build is unusable - download the executable again."
        )
    return key


def _read_instance() -> str:
    """Which Panorama this build encrypts for. Stamped by the build; shown in
    the UI so a support call can match an exe to a server."""
    try:
        return _bundled("panorama_instance.txt").read_text(encoding="utf-8").strip() or "dev"
    except OSError:
        return "dev"


PUBLIC_KEY = _read_key()
INSTANCE = _read_instance()

STEPS = ['Method', 'Admin Host', 'Server', 'Security Mode', 'Authentication', 'Download']

# Security modes
SECURITY_MODES = {
    1: 'TM1',
    2: 'Integrated',
    3: 'CAM',
    4: 'CAM SSO',
    5: 'LDAP'
}

DEFAULT_SERVER = "localhost"
DEFAULT_PORT = "8010"
DEFAULT_USER = "admin"
DEFAULT_ADMIN_PORT = "5895"
DEFAULT_NAMESPACE = ""
