"""Plugin cards show what an add-on option or override.ini sets again at every start (GitHub issue #1, 1.6.2:
"activated plugins deactivate themselves over night").

generate_config.py writes startup_overrides.json; the patched settings_schema adds the rows per card; plugins.html
shows them. Usage: test_startup_overrides.py <simulated tree>.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

TESTS = pathlib.Path(__file__).resolve().parent
GEN = str(TESTS.parent / "meshcore-bot" / "generate_config.py")
FIXTURES = TESTS / "fixtures"
TREE = sys.argv[1] if len(sys.argv) > 1 else os.environ["SIM_TREE"]

fails = []


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


opts = json.load(open(FIXTURES / "options_sample.json"))
opts.setdefault("commands", {})
opts["commands"]["enable"] = ["joke"]
opts["commands"]["disable"] = ["aurora"]
opts.setdefault("advanced", {})
opts["advanced"]["extra_config"] = ["Sports_Command.enabled = false"]

data, user = tempfile.mkdtemp(), tempfile.mkdtemp()
with open(f"{data}/options.json", "w") as fh:
    json.dump(opts, fh)


def start():
    r = subprocess.run([sys.executable, GEN, f"{data}/options.json", f"{data}/config.ini", data, user],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


start()
with open(f"{user}/override.ini", "a") as fh:
    fh.write("\n[Path_Command]\nenabled = false\nmax_hops_shown = 3\n")
start()
rows = json.load(open(f"{data}/startup_overrides.json", encoding="utf-8"))
by = {(r["section"], r["key"]): r for r in rows}
check(by.get(("Joke_Command", "enabled"), {}).get("source", "").startswith("Commands → Enable")
      and by[("Joke_Command", "enabled")]["value"] == "true", "Commands → Enable is listed, with its value")
check(by.get(("Aurora_Command", "enabled"), {}).get("source", "").startswith("Commands → Disable")
      and by[("Aurora_Command", "enabled")]["value"] == "false", "Commands → Disable is listed")
check(by.get(("Sports_Command", "enabled"), {}).get("source", "").startswith("Advanced → Extra config lines"),
      "an Extra config line is listed")
check(by.get(("Path_Command", "enabled"), {}).get("source", "").startswith("override.ini")
      and by.get(("Path_Command", "max_hops_shown"), {}).get("value") == "3", "override.ini is listed, every key")
check(not any(s == "Bot" and k == "bot_name" for s, k in by), "ordinary generated options are not listed")

opts["commands"]["disable"] = []
with open(f"{data}/options.json", "w") as fh:
    json.dump(opts, fh)
open(f"{user}/override.ini", "w").write("")
start()
rows = json.load(open(f"{data}/startup_overrides.json", encoding="utf-8"))
check(not any(r["section"] in ("Aurora_Command", "Path_Command") for r in rows), "removed from the option: no longer listed")

# ------------------------------------------------------------------ the card API (patched settings_schema)
os.environ["MESHCORE_DATA_DIR"] = data
sys.path.insert(0, TREE)
os.chdir(TREE)
from modules import settings_schema as S  # noqa: E402

check([r["key"] for r in S._addon_startup_overrides("Joke_Command")] == ["enabled"], "card API: rows of its own section")
check(S._addon_startup_overrides("joke_command") and not S._addon_startup_overrides("Path_Command"),
      "card API: section name in any case, nothing for other cards")
os.environ["MESHCORE_DATA_DIR"] = tempfile.mkdtemp()
check(S._addon_startup_overrides("Joke_Command") == [], "card API: no file, no rows (and no error)")
src = open(os.path.join(TREE, "modules/settings_schema.py"), encoding="utf-8").read()
check('"startup_overrides": _addon_startup_overrides(section),' in src, "every card entry carries startup_overrides")

page = open(os.path.join(TREE, "modules/web_viewer/templates/plugins.html"), encoding="utf-8").read()
check("plugin.startup_overrides" in page and "Set again at every start of the add-on" in page,
      "Plugins page shows the rows under the description")

i18n = json.load(open(TESTS.parent / "meshcore-bot/local_shared/local_data/ui_i18n.json", encoding="utf-8"))
gen_src = open(GEN, encoding="utf-8").read()
texts = ["Set again at every start of the add-on, so a change here does not last:"] + [
    line.split('"')[1] for line in gen_src.splitlines() if line.startswith("SOURCE_")]
check(len(texts) == 5 and all(t in i18n[lang] for t in texts for lang in ("nl", "de", "fr", "da")),
      "all fixed texts translated (nl, de, fr, da)")

print(f"\n{len(fails)} failures")
sys.exit(1 if fails else 0)
