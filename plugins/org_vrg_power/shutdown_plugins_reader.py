"""Reading which plugins must be asked before shutdown.

Each plugin may declare a `power` settings group in `plugins/<id>/manifest.yaml`:

    power:
      ask_before_shutdown: true

When enabled, the power plugin calls that plugin's `is_ready_to_die` videoreg-api
method before shutting down, letting it defer the shutdown if it is busy. The
power plugin scans every plugin directory at start to build this list, instead of
hardcoding the plugins to ask. Declaring the `is_ready_to_die` method itself
remains the plugin developer's responsibility.
"""

from pathlib import Path

import yaml


def read_ask_before_shutdown_plugins(
  plugins_dir: Path, plugins_manifest: list[dict]
) -> list[str]:
  """Return short names of enabled plugins with `power.ask_before_shutdown: true`.

  Args:
    plugins_dir: path to the `plugins` directory.
    plugins_manifest: the `plugins` list from `videoreg.manifest.yaml`, used to map
      a plugin id (directory name) to its short `name` and to skip disabled plugins
      (a disabled plugin is not running, so asking it would only time out).

  Returns:
    A sorted list of short plugin names whose manifest enables ask_before_shutdown.
  """
  name_by_id = {
    p.get("id"): p.get("name") for p in plugins_manifest if p.get("enabled", True)
  }

  names: list[str] = []
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

    power = manifest.get("power")
    if isinstance(power, dict) and power.get("ask_before_shutdown"):
      names.append(plugin_name)

  names.sort()
  return names
