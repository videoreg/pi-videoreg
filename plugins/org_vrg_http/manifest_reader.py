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


def collect_dashboard_blocks(http_manifests: list) -> list[dict]:
  """Flatten every plugin's `http.dashboard` entries into ordered descriptors.

  Args:
    http_manifests: the list returned by `read_plugin_http_configs`.

  Returns:
    Descriptors `{key, component, method, order}` sorted by ascending `order`.
    `key` is `"<plugin_id>:<component>"`. Entries without a `component` are
    skipped. Only the static dashboard structure lives in the manifest; blocks
    added imperatively at runtime (e.g. freshly captured media) are not declared
    here — their component just needs to be bundled.
  """
  blocks: list[dict] = []
  for config in http_manifests or []:
    plugin_id = config["id"]
    for entry in config["http"].get("dashboard") or []:
      component = entry.get("component")
      if not component:
        continue
      blocks.append(
        {
          "key": f"{plugin_id}:{component}",
          "component": component,
          "method": entry.get("method"),
          "order": entry.get("order", 0),
        }
      )
  blocks.sort(key=lambda b: b["order"])
  return blocks
