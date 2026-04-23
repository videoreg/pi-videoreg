import json

from plugins.org_vrg_net.net_controls import NetControls
from plugins.org_vrg_net.plugin import NetPlugin
from sdk.interface import Interface, InterfaceCommand


class CommandGetConnection(InterfaceCommand):
  _plugin: NetPlugin
  _net_controls: NetControls

  def __init__(self, plugin: NetPlugin, net_controls: NetControls):
    super().__init__()
    self._plugin = plugin
    self._net_controls = net_controls

  async def exec(self, interface: Interface, payload, args):
    connection_id = str(args)

    if not connection_id:
      self._plugin.logger.warning(
        f"Command CommandGetConnection: connection id not provided args={args}"
      )
      return

    connections = self._net_controls.get_nm_connections()

    for connection in connections:
      if connection_id == connection.get("id"):
        await interface.send_text(payload, text=json.dumps(connection, indent=2))

    self._plugin.logger.warning(
      f"Command CommandGetConnection: connection not found connection_id={connection_id}"
    )
