#!/usr/bin/env python3
"""Source patch: a plugin card says which of its settings are set again at every start of the add-on.

GitHub issue #1 (1.6.2): "activated plugins deactivate themselves over night". Commands -> Enable/Disable and Extra
config lines in the add-on Configuration, and override.ini, are applied at every start and win over the card, so a
plugin switched on there went off again at the next (nightly) restart without a word. generate_config.py now writes
/data/startup_overrides.json; the Plugins API adds those rows per card ("startup_overrides") and the page shows them
under the description, with where they come from.
"""
import pathlib
import sys

ROOT = pathlib.Path.cwd()


def patch(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = p.read_text()
    count = text.count(old)
    if count != 1:
        sys.exit(
            f"PATCH FAILED - anchor text found {count} time(s) in {path} "
            f"(expected 1; upstream code likely changed):\n{old!r}"
        )
    p.write_text(text.replace(old, new))
    print(f"Patched {path}")


patch(
    "modules/settings_schema.py",
    """        "dynamic_sections": _read_dynamic_sections(config, cls),""",
    """        "dynamic_sections": _read_dynamic_sections(config, cls),
        "startup_overrides": _addon_startup_overrides(section),""",
)

p = ROOT / "modules/settings_schema.py"
p.write_text(p.read_text() + """

def _addon_startup_overrides(section):
    \"\"\"(add-on) Rows of /data/startup_overrides.json for this section: settings an add-on option or override.ini
    sets again at every start (written by generate_config.py). Empty when the file is missing or unreadable.\"\"\"
    import json as _json
    import os as _os
    path = _os.path.join(_os.environ.get("MESHCORE_DATA_DIR", "/data"), "startup_overrides.json")
    try:
        with open(path, encoding="utf-8") as fh:
            rows = _json.load(fh)
    except (OSError, ValueError):
        return []
    return [r for r in rows if isinstance(r, dict) and str(r.get("section", "")).lower() == str(section or "").lower()]
""")
print("Patched modules/settings_schema.py (startup overrides)")

patch(
    "modules/web_viewer/templates/plugins.html",
    """        headText.append(title, section, description);
""",
    """        headText.append(title, section, description);
        // (add-on) settings that an add-on option or override.ini sets again at every start: a change on the card
        // does not last (GitHub issue #1). Fixed texts in their own text nodes, so the page translation finds them.
        if (Array.isArray(plugin.startup_overrides) && plugin.startup_overrides.length) {
            const warn = document.createElement('div');
            warn.className = 'small text-warning mt-1 addon-startup-overrides';
            const icon = document.createElement('i');
            icon.className = 'fas fa-exclamation-triangle me-1';
            icon.setAttribute('aria-hidden', 'true');
            const lead = document.createElement('span');
            lead.textContent = 'Set again at every start of the add-on, so a change here does not last:';
            warn.append(icon, lead);
            plugin.startup_overrides.forEach((row) => {
                const line = document.createElement('div');
                const code = document.createElement('code');
                code.textContent = `${String(row.key ?? '')} = ${String(row.value ?? '')}`;
                const sep = document.createTextNode(' · ');
                const src = document.createElement('span');
                src.textContent = String(row.source ?? '');
                line.append(code, sep, src);
                warn.appendChild(line);
            });
            headText.appendChild(warn);
        }
""",
)
