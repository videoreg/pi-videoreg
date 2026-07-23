"""Shared `/more` and `/status` gateway menu commands.

These two commands are handled by the bot gateways themselves (Telegram `bot`, VK
`botvk`), not by a feature plugin. To keep them working independently of each other —
one gateway plugin may be disabled while another runs — the logic lives here in the SDK
and each gateway registers its own copy through its own `<gateway>.command` method,
instead of routing to a single owner.

Both commands aggregate their contents from every plugin's `bot` manifest section, so
feature plugins opt in without the gateways hardcoding them:

    bot:
      status_method: power.get_status_text  # videoreg-api method returning status text
      more_buttons:                         # inline buttons for the `/more` menu
        - text: Power
          callback_data: command__power__power
          weigh: 30                         # optional; higher sorts earlier (default 0)

The `bot` key names the family of bot-type gateways (both Telegram and VK read it); its
button `callback_data` and status method names are gateway-neutral.
"""

import asyncio

from sdk.command_reader import read_plugin_commands
from sdk.gateway import Gateway, GatewayCommand
from sdk.socket.api import ApiClient, ApiResponse
from sdk.socket.requests import RequestTimeoutError

# Menu metadata for the built-in gateway commands, injected into each gateway's menu
# with `plugin` set to the owning gateway so they route to `<gateway>.command`.
GATEWAY_MENU_COMMANDS: list[dict] = [
  {"name": "status", "title": "Status", "weigh": 80},
  {"name": "more", "title": "More", "weigh": -10},  # keep the catch-all menu at the bottom
]


def _iter_bot_sections(plugins: list[dict]):
  """Yield (plugin_name, bot_section) for every enabled plugin declaring a `bot` group."""
  for entry in plugins or []:
    if not entry.get("enabled", True):
      continue
    plugin_name = entry.get("name")
    if not plugin_name:
      continue

    bot = entry.get("bot")
    if isinstance(bot, dict):
      yield plugin_name, bot


def read_more_buttons(plugins: list[dict]) -> list[list[dict]]:
  """Collect `bot.more_buttons` from all plugins into an inline keyboard.

  Returns a keyboard (list of rows) with one button per row, sorted by button `weigh`
  descending (equal weights sorted alphabetically by `text`). Each button keeps only the
  `text` and `callback_data` fields expected by the gateway.
  """
  buttons: list[dict] = []
  for _plugin_name, bot in _iter_bot_sections(plugins):
    for button in bot.get("more_buttons", []) or []:
      if not isinstance(button, dict):
        continue
      text = button.get("text")
      callback_data = button.get("callback_data")
      if not text or not callback_data:
        continue
      buttons.append(
        {"text": text, "callback_data": callback_data, "weigh": button.get("weigh") or 0}
      )

  buttons.sort(key=lambda b: (-b["weigh"], b["text"]))
  return [[{"text": b["text"], "callback_data": b["callback_data"]}] for b in buttons]


def read_status_methods(plugins: list[dict]) -> list[str]:
  """Collect `bot.status_method` names from all plugins for the `/status` summary.

  Returns a list of videoreg-api method names (e.g. `power.get_status_text`), sorted by
  the owning plugin's short name for a deterministic order.
  """
  methods: list[tuple[str, str]] = []
  for plugin_name, bot in _iter_bot_sections(plugins):
    method = bot.get("status_method")
    if isinstance(method, str) and method:
      methods.append((plugin_name, method))

  methods.sort(key=lambda m: m[0])
  return [method for _plugin_name, method in methods]


class CommandMore(GatewayCommand):
  """Shows a menu of links to commands hidden from the main gateway menu.

  The keyboard is aggregated from every plugin's `bot.more_buttons` manifest section
  (see `read_more_buttons`), so plugins opt into this menu without hardcoding.
  """

  _keyboard: list[list[dict]]

  def __init__(self, keyboard: list[list[dict]]):
    super().__init__()
    self._keyboard = keyboard

  async def exec(self, gateway: Gateway, payload, args):
    if not self._keyboard:
      await gateway.send_text(payload=payload, text="No commands")
      return

    await gateway.send_text(payload=payload, text="More", keyboard=self._keyboard)


class CommandStatus(GatewayCommand):
  """Sends a short summary of the current system state.

  The summary is aggregated from every plugin's `bot.status_method` manifest section
  (see `read_status_methods`): each method is a videoreg-api method returning
  `{"status": "ok", "data": {"text": "..."}}`. Methods are queried in parallel and their
  texts are joined into a single message.
  """

  _api_client: ApiClient
  _status_methods: list[str]

  def __init__(self, api_client: ApiClient, status_methods: list[str]):
    super().__init__()
    self._api_client = api_client
    self._status_methods = status_methods

  async def exec(self, gateway: Gateway, payload, args):
    if not self._status_methods:
      await gateway.send_text(payload=payload, text="No status")
      return

    texts = await asyncio.gather(*(self._fetch(method) for method in self._status_methods))
    parts = [text for text in texts if text]

    await gateway.send_text(
      payload=payload, text="\n\n".join(parts) if parts else "No status"
    )

  async def _fetch(self, method: str) -> "str | None":
    try:
      response: ApiResponse = await self._api_client.exec(method, args=None)
    except RequestTimeoutError:
      return f"{method}: timeout"
    except Exception:
      return None

    if not response.is_ok():
      return None

    data = response.get_data()
    if isinstance(data, dict):
      text = data.get("text")
      if isinstance(text, str) and text:
        return text

    return None


def build_menu_gateway_commands(
  api_client: ApiClient, plugins: list[dict]
) -> dict[str, GatewayCommand]:
  """Build the `{command_name: handler}` map for a gateway's `<gateway>.command` method."""
  return {
    "more": CommandMore(read_more_buttons(plugins)),
    "status": CommandStatus(api_client, read_status_methods(plugins)),
  }


def read_menu_commands(plugins: list[dict], gateway_name: str) -> list[dict]:
  """Return the gateway's menu commands: plugin manifest commands plus `/more` & `/status`.

  The built-in commands are tagged with `plugin=gateway_name` so the gateway routes them
  to its own `<gateway>.command`. The result is sorted like `read_plugin_commands`
  (by `weigh` descending, then command name).
  """
  commands = read_plugin_commands(plugins)
  commands.extend({**cmd, "plugin": gateway_name} for cmd in GATEWAY_MENU_COMMANDS)
  commands.sort(key=lambda c: (-(c.get("weigh") or 0), c.get("name") or ""))
  return commands
