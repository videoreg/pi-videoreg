"""Reading which plugins must be asked before shutdown.

Each plugin may declare a `power` settings group in `plugins/<id>/manifest.yaml`:

    power:
      ask_before_shutdown: true

`org_vrg_core` folds that into the merged manifest at startup. When enabled, the
power plugin calls that plugin's `is_ready_to_die` videoreg-api method before
shutting down, letting it defer the shutdown if it is busy. Declaring the
`is_ready_to_die` method itself remains the plugin developer's responsibility.
"""


def read_ask_before_shutdown_plugins(plugins: list[dict]) -> list[str]:
  """Return short names of enabled plugins with `power.ask_before_shutdown: true`.

  Args:
    plugins: the merged manifest's `plugins` list. Disabled plugins are skipped
      (a disabled plugin is not running, so asking it would only time out).

  Returns:
    A sorted list of short plugin names whose manifest enables ask_before_shutdown.
  """
  names: list[str] = []
  for entry in plugins or []:
    if not entry.get("enabled", True):
      continue
    plugin_name = entry.get("name")
    if not plugin_name:
      continue

    power = entry.get("power")
    if isinstance(power, dict) and power.get("ask_before_shutdown"):
      names.append(plugin_name)

  names.sort()
  return names
