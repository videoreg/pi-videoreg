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
    connections = self._net_controls.get_nm_connections()

    bot_buttons = []

    for connection in connections:
      id = connection.get("id")
      name = connection.get("name")
      emoji = "🟢" if connection.get("state") == "activated" else "🔴"

      bot_buttons.append(
        [{"text": f"{name} {emoji}", "callback_data": f"command__net__connection__{id}"}]
      )

    await interface.send_text(payload=payload, text="Connections", keyboard=bot_buttons)
