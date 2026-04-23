from plugins.org_vrg_gps.plugin import GpsPlugin
from sdk.socket.api import ApiMethod


class MethodGetCommands(ApiMethod):
  _plugin: GpsPlugin

  def __init__(self, plugin: GpsPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    location_gps = await self._plugin.modem.get_location_gps()
    location_lbs = await self._plugin.modem.get_location_lbs()

    if location_gps:
      gps_lat = location_gps["latitude"]
      gps_lng = location_gps["longitude"]
      gps_datetime = location_gps["datetime"]
    else:
      gps_lat = "unknown"
      gps_lng = "unknown"
      gps_datetime = "unknown"

    if location_lbs:
      lbs_lat = location_lbs["latitude"]
      lbs_lng = location_lbs["longitude"]
    else:
      lbs_lat = "unknown"
      lbs_lng = "unknown"

    bot_message = f"Location:\n\nGPS: {gps_lat},{gps_lng}\nGPS time: {gps_datetime}\nhttps://yandex.ru/maps/?mode=search&text={gps_lat}%2C{gps_lng}\n\nLBS: {lbs_lat},{lbs_lng}\nhttps://yandex.ru/maps/?mode=search&text={lbs_lat}%2C{lbs_lng}"

    return {
      "status": "ok",
      "bot_message": bot_message,
      "bot_buttons": [
        [{"text": "Get location", "callback_data": "button_plugin__gps.get_location"}],
        [{"text": "List tracks", "callback_data": "button_plugin__gps.list_tracks"}],
      ],
    }
