import plugins.org_vrg_net.const as const
from plugins.org_vrg_net.net_controls import NetControls
from sdk.socket.api import ApiMethod
from sdk.state import State


class MethodSetWifiMode(ApiMethod):
  """Switch WiFi between three high-level modes: "client", "ap" or "off".

  A single control replaces the separate module/AP/client toggles: each mode
  fully reconciles the radio, the per-connection autoconnect flag and the active
  connection so the user configures WiFi in one step.

  - client: unblock the module, enable client autoconnect, bring the client up
  - ap:     unblock the module, enable AP autoconnect, bring the AP up
  - off:    bring both connections down, disable their autoconnect, block the module
  """

  _net_controls: NetControls
  _state: State

  def __init__(self, net_controls: NetControls, state: State):
    super().__init__()
    self._net_controls = net_controls
    self._state = state

  async def exec(self, args):
    mode = args.get("mode") if isinstance(args, dict) else None

    if mode not in ("client", "ap", "off"):
      return {"status": "error", "error": 'Invalid mode. Must be "client", "ap" or "off"'}

    try:
      if mode == "off":
        # Bring both connections down, drop their autoconnect, then block the radio.
        await self._net_controls.set_connection_enabled(const.NM_CONNECTION_WIFI, False)
        await self._net_controls.set_connection_enabled(const.NM_CONNECTION_AP, False)
        await self._set_autoconnect(const.NM_CONNECTION_WIFI, False)
        await self._set_autoconnect(const.NM_CONNECTION_AP, False)
        await self._block_radio(True)
      else:
        client, ap = const.NM_CONNECTION_WIFI, const.NM_CONNECTION_AP
        active = client if mode == "client" else ap
        inactive = ap if mode == "client" else client

        # Tear down the other mode first so only one connection stays up.
        await self._net_controls.set_connection_enabled(inactive, False)
        await self._set_autoconnect(inactive, False)

        # Enable the radio before bringing the selected connection up.
        await self._block_radio(False)
        await self._set_autoconnect(active, True)
        await self._net_controls.set_connection_enabled(active, True)

      return {"status": "ok", "bot_message": f"WiFi mode: {mode}"}

    except Exception as e:
      return {"status": "error", "error": f"Failed to set WiFi mode: {e}"}

  async def _set_autoconnect(self, connection: str, enabled: bool):
    await self._net_controls.set_connection_property(
      connection, "connection.autoconnect", "yes" if enabled else "no"
    )

  async def _block_radio(self, blocked: bool):
    self._state.save({const.KEY_WIFI_BLOCKED: blocked})
    await self._net_controls.set_wifi_blocked(blocked)
