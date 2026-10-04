import asyncio

from plugins.org_vrg_net.methods.set_wifi_mode import MethodSetWifiMode
from sdk.gateway import Gateway, GatewayCommand
from sdk.i18n import I18n

# Time for the confirmation to reach the user before the switch: leaving the WiFi client
# mode may cut the connection the gateway sends it through.
CONFIRMATION_DELAY = 3


class CommandSetWifiMode(GatewayCommand):
  """Switches WiFi to a fixed mode ("client", "ap" or "off") from a bot command or button.

  Delegates to the net.set_wifi_mode api-method so the bot and the web UI share one
  implementation. The confirmation is sent before the switch, since afterwards the
  device may be unreachable.
  """

  _method: MethodSetWifiMode
  _i18n: I18n
  _mode: str

  def __init__(self, method: MethodSetWifiMode, i18n: I18n, mode: str):
    super().__init__()
    self._method = method
    self._i18n = i18n
    self._mode = mode

  async def exec(self, gateway: Gateway, payload, args):
    await gateway.send_text(payload, self._i18n.t(f"net.wifi_mode.will_switch_{self._mode}"))
    await asyncio.sleep(CONFIRMATION_DELAY)

    response = await self._method.exec({"mode": self._mode})

    if response.get("status") != "ok":
      await gateway.send_text(payload, response.get("error"))
