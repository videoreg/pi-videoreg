from plugins.org_vrg_net.net_controls import NetControls
from sdk.socket.api import ApiMethod


class MethodSetConnectionEnabled(ApiMethod):
  _net_controls: NetControls
  _enabled: bool

  def __init__(self, net_controls: NetControls, enabled: bool):
    super().__init__()
    self._net_controls = net_controls
    self._enabled = enabled

  async def exec(self, args):
    # Accept either a bare connection name or {"type": <name>} (the http generic
    # handler passes the JSON body as a dict).
    connection = args.get("type") if isinstance(args, dict) else (str(args) if args else "")

    if not connection:
      return {"status": "error", "error": "Connection name not provided"}

    rc = await self._net_controls.set_connection_enabled(connection, self._enabled)

    if rc.returncode == 0:
      return {"status": "ok", "bot_message": f"Connection {connection} enabled: {self._enabled}"}
    else:
      return {"status": "error", "bot_message": "Error"}
