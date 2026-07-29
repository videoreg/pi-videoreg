"""Same-batch command cancellation.

A gateway (`bot`, `sms`) reads user commands in batches — one iteration of its receive
loop yields the list of commands that were fetched together. A plugin can declare in its
`manifest.yaml` that one command cancels another when both land in the same batch:

    commands:
      - name: "no"
        title: Cancel scheduled shutdown
        cancels:
          - shutdown

If `/shutdown` and `/no` arrive in the same batch, `/no` cancels the `/shutdown` and it is
never dispatched. This covers a shutdown command sent to a device that is offline: once it
reconnects both messages arrive together (one iteration) and the cancellation takes effect.
Commands that arrive in different iterations are unaffected — a lone `/no` is dispatched
normally (its handler just reports there was nothing to cancel).
"""

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def read_command_cancellations(plugins: list[dict]) -> dict[str, set[str]]:
  """Build the canceller -> {target command names} map from the merged manifest.

  Reads the optional `cancels` list on each plugin command (see the module docstring).

  Args:
    plugins: the merged manifest's `plugins` list.

  Returns:
    A dict mapping a canceller command name to the set of command names it cancels.
  """
  from sdk.command_reader import read_plugin_commands

  cancel_map: dict[str, set[str]] = {}
  for cmd in read_plugin_commands(plugins):
    name = cmd.get("name")
    cancels = cmd.get("cancels")
    if not name or not cancels:
      continue
    targets = {str(target) for target in cancels if target}
    if targets:
      cancel_map.setdefault(name, set()).update(targets)
  return cancel_map


def apply_command_cancellations(
  commands: list[T], cancel_map: dict[str, set[str]], name_getter: Callable[[T], str]
) -> list[T]:
  """Drop commands cancelled by a canceller present in the same batch.

  For every canceller in `commands` whose target(s) are also present, the targets are
  removed; a canceller that actually cancelled something is itself removed (consumed) so it
  never reaches its handler. A canceller with no target present is kept and dispatched as
  usual. Cancellation is presence-based within the batch and ignores arrival order.

  Args:
    commands: the batch of commands read in one receive-loop iteration.
    cancel_map: canceller -> targets map from `read_command_cancellations`.
    name_getter: extracts the command name from a batch item.

  Returns:
    The batch with cancelled targets and fired cancellers removed.
  """
  if not cancel_map:
    return commands

  present = {name_getter(command) for command in commands}

  cancelled: set[str] = set()
  fired: set[str] = set()
  for name in present:
    targets = cancel_map.get(name)
    if not targets:
      continue
    hits = targets & present
    if hits:
      cancelled |= hits
      fired.add(name)

  if not fired:
    return commands

  return [
    command
    for command in commands
    if name_getter(command) not in cancelled and name_getter(command) not in fired
  ]
