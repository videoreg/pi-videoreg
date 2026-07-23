"""Reading the per-plugin `http` blocks from the merged manifest.

Each plugin may declare a web-facing configuration in `plugins/<id>/manifest.yaml`
under the `http` key (menu / menu_settings / components / api); `org_vrg_core` folds
those into the merged manifest at startup, from which the http plugin reads them.
"""


def read_plugin_http_configs(plugins: list[dict]) -> list[dict]:
  """Return the `http` config of each enabled plugin from the merged `plugins` list.

  Args:
    plugins: the merged manifest's `plugins` list. Each entry carries its `enabled`
      flag and its folded `http` block.

  Returns:
    A list of dicts `{"id": <plugin_id>, "http": <http block>}` for every enabled
    plugin that defines a non-empty `http` block, sorted by plugin id so menu and
    bundle order stay stable.
  """
  configs: list[dict] = []

  for entry in plugins or []:
    if not entry.get("enabled", True):
      continue

    http = entry.get("http")
    if not http:
      continue

    configs.append({"id": entry.get("id"), "http": http})

  configs.sort(key=lambda c: c["id"] or "")
  return configs


def collect_dashboard_blocks(http_manifests: list) -> list[dict]:
  """Flatten every plugin's `http.dashboard` entries into ordered descriptors.

  Args:
    http_manifests: the list returned by `read_plugin_http_configs`.

  Returns:
    Descriptors `{key, component, method, order, timeout}` sorted by ascending
    `order`. `key` is `"<plugin_id>:<component>"`. `timeout` is the optional
    per-block data-resolution timeout in seconds (`None` when not declared, so
    the handler applies its default). Entries without a `component` are skipped.
    Only the static dashboard structure lives in the manifest; blocks added
    imperatively at runtime (e.g. freshly captured media) are not declared here
    — their component just needs to be bundled.
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
          "timeout": entry.get("timeout"),
        }
      )
  blocks.sort(key=lambda b: b["order"])
  return blocks
