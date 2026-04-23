import plugins.org_vrg_net.const as const
from plugins.org_vrg_net.net_controls import NetControls
from sdk.socket.api import ApiMethod
from sdk.state import State


class MethodSetWifiBlocked(ApiMethod):
  _net_controls: NetControls
  _state: State
  _blocked: bool

  def __init__(self, net_controls: NetControls, state: State, blocked: bool):
    super().__init__()
    self._net_controls = net_controls
    self._state = state
    self._blocked = blocked

  async def exec(self, args):
    self._state.save({const.KEY_WIFI_BLOCKED: self._blocked})

    await self._net_controls.set_wifi_blocked(self._blocked)

    return {"status": "ok", "bot_message": f"Wifi blocked: {self._blocked}"}
