from plugins.org_vrg_net.methods.set_wifi_mode import MethodSetWifiMode
from sdk.gateway import Gateway, GatewayCommand


class CommandSetWifiMode(GatewayCommand):
  """Switches WiFi to a fixed mode ("client", "ap" or "off") from a bot command or button.

  Delegates to the net.set_wifi_mode api-method so the bot and the web UI share one
  implementation.
  """

  _method: MethodSetWifiMode
  _mode: str

  def __init__(self, method: MethodSetWifiMode, mode: str):
    super().__init__()
    self._method = method
    self._mode = mode

  async def exec(self, gateway: Gateway, payload, args):
    response = await self._method.exec({"mode": self._mode})

    if response.get("status") == "ok":
      await gateway.send_text(payload, response.get("bot_message"))
    else:
      await gateway.send_text(payload, response.get("error"))
