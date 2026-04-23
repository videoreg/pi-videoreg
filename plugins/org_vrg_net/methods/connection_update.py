from logging import Logger

from plugins.org_vrg_net.net_controls import NetControls
from sdk.socket.api import ApiMethod


class MethodConnectionUpdate(ApiMethod):
  _logger: Logger
  _net_controls: NetControls
  _enabled: bool

  def __init__(self, logger: Logger, net_controls: NetControls):
    super().__init__()
    self._logger = logger
    self._net_controls = net_controls

  async def exec(self, args):
    if not isinstance(args, dict):
      return {"status": "error", "error": "Arguments should be JSON"}

    connection_type = args.get("type")

    if connection_type not in ["ap", "wifi", "modem"]:
      return {"status": "error", "error": 'Invalid connection type. Must be "ap" or "wifi"'}

    try:
      # Update connection parameters
      if "ssid" in args:
        ssid = args["ssid"].strip()
        if ssid:
          await self._net_controls.set_connection_property(
            connection_type, "802-11-wireless.ssid", ssid
          )

      if "password" in args:
        password = args["password"].strip()
        if password:
          await self._net_controls.set_connection_property(
            connection_type, "802-11-wireless-security.psk", password
          )

      if "autoconnect" in args:
        autoconnect = "yes" if args["autoconnect"] else "no"
        await self._net_controls.set_connection_property(
          connection_type, "connection.autoconnect", autoconnect
        )

      if "apn" in args:
        apn = args["apn"].strip()
        await self._net_controls.set_connection_property("modem", "gsm.apn", apn)

      self._logger.info(f"{connection_type} configuration updated successfully")

      return {"status": "ok"}

    except Exception as e:
      self._logger.error(f"Error setting WiFi config {type(e).__name__}: {e}")
      return {"status": "error", "error": "Failed to set connection configuration"}
