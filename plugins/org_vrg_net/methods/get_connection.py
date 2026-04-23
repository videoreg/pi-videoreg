import json

from plugins.org_vrg_net.net_controls import NetControls
from sdk.socket.api import ApiMethod


class MethodGetConnection(ApiMethod):
  _net_controls: NetControls

  def __init__(self, net_controls: NetControls):
    super().__init__()
    self._net_controls = net_controls

  async def exec(self, args):
    connection_id = str(args)

    if not connection_id:
      return {"status": "ok", "error": "Connection id not provided"}

    connections = self._net_controls.get_nm_connections()

    for connection in connections:
      if connection_id == connection.get("id"):
        return {
          "status": "ok",
          "connection": connection,
          "bot_message": json.dumps(connection, indent=2),
        }

    return {"status": "ok", "error": f"Not found connection {connection_id}"}
