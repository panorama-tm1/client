"""Build client/tm1/Panorama.Push.v11|v12 (.ti code + .json REST body).

Run after editing anything in this folder:  python tm1/src/build.py
Then copy the two .json files to front/app/src/lib/tm1/.

The results are templates: the Update data dialog of Panorama fills in
{{PANORAMA_URL}}, {{INSTANCE_ID}} and {{TOKEN}}. The v11 Prolog embeds
panorama_push.ps1, one ASCIIOutput per line, so the script and the process
can never drift apart.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent


def ti_literal(line):
    return "'" + line.replace("'", "''") + "'"


def load(template, **subst):
    out = []
    for line in (HERE / template).read_text(encoding="utf-8").splitlines():
        out += subst.get(line.strip(), [line])
    return out


def build(name, prolog, epilog):
    ti = [
        f"# {name}: template, Panorama fills in the {{{{...}}}} values (Update data).",
        "# No parameter, no data source. Metadata and Data tabs: empty.",
        "",
        "#=== PROLOG " + "=" * 66, *prolog, "",
        "#=== EPILOG " + "=" * 66, *epilog, "",
    ]
    (OUT / f"{name}.ti").write_text("\n".join(ti), encoding="utf-8")
    rest = {
        "Name": name,
        "HasSecurityAccess": False,
        "PrologProcedure": "\r\n".join(prolog) + "\r\n",
        "MetadataProcedure": "",
        "DataProcedure": "",
        "EpilogProcedure": "\r\n".join(epilog) + "\r\n",
        "DataSource": {"Type": "None"},
        "Parameters": [],
        "Variables": [],
    }
    (OUT / f"{name}.json").write_text(json.dumps(rest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


script = (HERE / "panorama_push.ps1").read_text(encoding="utf-8").splitlines()
assert all(ord(c) < 128 for line in script for c in line), "keep the script ASCII"
assert not any('"' in line for line in script), "no double quote in the script"

build(
    "Panorama.Push.v11",
    load("v11_prolog.ti", **{"{{SCRIPT}}": [f"ASCIIOutput(sScript, {ti_literal(l)});" for l in script]}),
    load("v11_epilog.ti"),
)
build("Panorama.Push.v12", load("v12_prolog.ti"), load("v12_epilog.ti"))
print("built", sorted(p.name for p in OUT.iterdir()))
