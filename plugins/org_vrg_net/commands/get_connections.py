from math import ceil

from plugins.org_vrg_net.net_controls import NetControls
from plugins.org_vrg_net.plugin import NetPlugin
from sdk.interface import Interface, InterfaceCommand


class CommandGetConnections(InterfaceCommand):
  _plugin: NetPlugin
  _net_controls: NetControls

  def __init__(self, plugin: NetPlugin, net_controls: NetControls):
    super().__init__()
    self._plugin = plugin
    self._net_controls = net_controls

  async def exec(self, interface: Interface, payload, args):
    page = 1
    try:
      page = int(args)
    except:
      pass

    connections = self._net_controls.get_nm_connections()

    if not connections:
      await interface.send_text(payload=payload, text="There are no connections")
      return

    per_page = interface.list_page_size or 6
    count_pages = int(ceil(len(connections) / per_page))

    if page < 1 or page > count_pages:
      page = 1

    offset = per_page * (page - 1)

    bot_buttons = []
    for connection in connections[offset : offset + per_page]:
      id = connection.get("id")
      name = connection.get("name")
      emoji = "🟢" if connection.get("state") == "activated" else "🔴"

      bot_buttons.append(
        [{"text": f"{name} {emoji}", "callback_data": f"command__net__connection__{id}"}]
      )

    buttons_row = []

    if page < count_pages:
      next_page = page + 1
      x5_page = min(count_pages, page + 5)
      if x5_page > next_page:
        buttons_row.append(
          {
            "text": "⏪ Much earlier" if page == 1 else "⏪",
            "callback_data": f"command__net__connections__{x5_page}",
          }
        )

      buttons_row.append(
        {"text": "⬅️ Earlier", "callback_data": f"command__net__connections__{next_page}"}
      )
    if page > 1:
      prev_page = page - 1
      buttons_row.append(
        {"text": "Later ➡️", "callback_data": f"command__net__connections__{prev_page}"}
      )
      x5_page = max(page - 5, 1)
      if x5_page < prev_page:
        buttons_row.append(
          {
            "text": "Much later ⏩" if page == count_pages else "⏩",
            "callback_data": f"command__net__connections__{x5_page}",
          }
        )

    if buttons_row:
      bot_buttons.append(buttons_row)

    text = "Connections"
    if count_pages > 1:
      text += f" (page {page} of {count_pages})"

    await interface.send_text(payload=payload, text=text, keyboard=bot_buttons)
