"""Reading the per-plugin `manifest.yaml` `commands` blocks.

Each plugin declares its user-facing (entry) commands in `plugins/<id>/manifest.yaml`
under the `commands` key. Interface plugins (`bot`, `sms`) scan every plugin directory
to build their command lists, so this reader lives in the SDK shared by both.
"""

from pathlib import Path

import yaml


def read_plugin_commands(plugins_dir: Path, plugins_manifest: list[dict]) -> list[dict]:
  """Scan `plugins/*/manifest.yaml` and return all declared commands.

  Args:
    plugins_dir: path to the `plugins` directory.
    plugins_manifest: the `plugins` list from `videoreg.manifest.yaml`, used to map a
      plugin id (directory name) to its short `name`.

  Returns:
    A flat list of command dicts. Each command keeps its manifest fields
    (`name`, `title`, `hidden`, `args`, `weigh`, ...) and gains a `plugin` key holding
    the owning plugin's short name. The list is sorted by `weigh` descending; commands
    with an equal weight (in particular those without a `weigh`, treated as 0) are
    sorted alphabetically by command `name`.
  """
  name_by_id = {p.get("id"): p.get("name") for p in plugins_manifest}

  commands: list[dict] = []
  for manifest_path in sorted(plugins_dir.glob("*/manifest.yaml")):
    plugin_id = manifest_path.parent.name
    plugin_name = name_by_id.get(plugin_id)
    if not plugin_name:
      continue

    try:
      with open(manifest_path, encoding="utf-8") as f:
        manifest = yaml.safe_load(f)
    except Exception:
      continue

    if not isinstance(manifest, dict):
      continue

    for cmd in manifest.get("commands", []) or []:
      if not isinstance(cmd, dict):
        continue
      entry = dict(cmd)
      entry["plugin"] = plugin_name
      commands.append(entry)

  commands.sort(key=lambda c: (-(c.get("weigh") or 0), c.get("name") or ""))
  return commands
