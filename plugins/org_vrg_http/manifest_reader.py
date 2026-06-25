"""Reading the per-plugin `manifest.yaml` `http` blocks.

Each plugin may declare a web-facing configuration in `plugins/<id>/manifest.yaml`
under the `http` key (menu / menu_settings / components / api). The http plugin
runs in its own service, so it scans every plugin directory itself rather than
relying on the per-service plugin list from `videoreg.manifest.yaml`.
"""

from pathlib import Path

import yaml


def enabled_plugin_ids(manifest) -> set[str]:
  """Return the ids of plugins marked enabled in the central manifest.

  A missing `enabled` key defaults to enabled (matches core.get_system).
  """
  return {p["id"] for p in manifest.plugins if p.get("enabled", True)}


def read_plugin_http_configs(
  plugins_dir: Path, enabled_ids: "set[str] | None" = None
) -> list[dict]:
  """Scan `plugins/*/manifest.yaml` and return the `http` config of each plugin.

  Args:
    plugins_dir: path to the `plugins` directory.
    enabled_ids: when provided, only plugins whose id is in this set are
      included; plugins disabled in the central manifest are skipped. When
      `None`, no filtering is applied.

  Returns:
    A list of dicts `{"id": <plugin_id>, "http": <http block>}` for every plugin
    that defines a non-empty `http` block. Plugins without a manifest, without
    an `http` key, or disabled in the central manifest are skipped.
  """
  configs: list[dict] = []

  for manifest_path in sorted(plugins_dir.glob("*/manifest.yaml")):
    plugin_id = manifest_path.parent.name

    if enabled_ids is not None and plugin_id not in enabled_ids:
      continue

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
