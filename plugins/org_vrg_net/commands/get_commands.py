import plugins.org_vrg_net.const as const
import plugins.org_vrg_net.ip as ip
from plugins.org_vrg_net.plugin import NetPlugin
from sdk.interface import Interface, InterfaceCommand


class CommandGetCommands(InterfaceCommand):
  _plugin: NetPlugin

  def __init__(self, plugin: NetPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, interface: Interface, payload, args):
    ips = self._get_ip_map()
    wifi_blocked = self._plugin.state.get(const.KEY_WIFI_BLOCKED, False)

    bot_message = f"""Network:

WG: {ips["wg0"]}
WiFi: {ips["wlan0"]}
Modem: {ips["wwan0"]}

WiFi blocked: {wifi_blocked}

https://{ip.get_current_ip()}:8443
"""

    await interface.send_text(
      payload=payload,
      text=bot_message,
      keyboard=[
        [{"text": "Get connections", "callback_data": "command__net__connections"}],
        [
          {"text": "WiFi: unblock", "callback_data": "command__net__wifi_unblock"},
          {"text": "WiFi: block", "callback_data": "command__net__wifi_block"},
        ],
      ],
    )

  def _get_ip_map(self):
    ips = {"wg0": None, "wlan0": None, "wwan0": None}

    for interface in ips:
      try:
        ips[interface] = ip.get_interface_ip(interface)
      except:
        ips[interface] = "error"

    return ips
