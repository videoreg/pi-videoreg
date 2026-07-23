"""Reading the per-plugin `commands` blocks from the merged manifest.

Each plugin declares its user-facing (entry) commands in `plugins/<id>/manifest.yaml`
under the `commands` key; `org_vrg_core` folds those into the merged manifest at
startup. Gateway plugins (`bot`, `sms`) build their command lists from that merged
view, so this reader lives in the SDK shared by both.
"""


def read_plugin_commands(plugins: list[dict]) -> list[dict]:
  """Return all declared commands from the merged manifest's `plugins` list.

  Args:
    plugins: the merged manifest's `plugins` list. Each entry carries the plugin's
      short `name` and its folded `commands` block.

  Returns:
    A flat list of command dicts. Each command keeps its manifest fields
    (`name`, `title`, `hidden`, `args`, `weigh`, ...) and gains a `plugin` key holding
    the owning plugin's short name. The list is sorted by `weigh` descending; commands
    with an equal weight (in particular those without a `weigh`, treated as 0) are
    sorted alphabetically by command `name`.
  """
  commands: list[dict] = []
  for entry in plugins or []:
    plugin_name = entry.get("name")
    if not plugin_name:
      continue

    for cmd in entry.get("commands", []) or []:
      if not isinstance(cmd, dict):
        continue
      command = dict(cmd)
      command["plugin"] = plugin_name
      commands.append(command)

  commands.sort(key=lambda c: (-(c.get("weigh") or 0), c.get("name") or ""))
  return commands
