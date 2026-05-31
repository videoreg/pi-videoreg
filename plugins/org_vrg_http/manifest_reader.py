"""Reading the per-plugin `manifest.yaml` `http` blocks.

Each plugin may declare a web-facing configuration in `plugins/<id>/manifest.yaml`
under the `http` key (menu / menu_settings / components / api). The http plugin
runs in its own service, so it scans every plugin directory itself rather than
relying on the per-service plugin list from `videoreg.manifest.yaml`.
"""

from pathlib import Path

import yaml


def read_plugin_http_configs(plugins_dir: Path) -> list[dict]:
  """Scan `plugins/*/manifest.yaml` and return the `http` config of each plugin.

  Args:
    plugins_dir: path to the `plugins` directory.

  Returns:
    A list of dicts `{"id": <plugin_id>, "http": <http block>}` for every plugin
    that defines a non-empty `http` block. Plugins without a manifest or without
    an `http` key are skipped.
  """
  configs: list[dict] = []

  for manifest_path in sorted(plugins_dir.glob("*/manifest.yaml")):
    plugin_id = manifest_path.parent.name

    try:
      with open(manifest_path, encoding="utf-8") as f:
        manifest = yaml.safe_load(f)
    except Exception:
      continue

    if not isinstance(manifest, dict):
      continue

    http = manifest.get("http")
    if not http:
      continue

    configs.append({"id": plugin_id, "http": http})

  return configs
