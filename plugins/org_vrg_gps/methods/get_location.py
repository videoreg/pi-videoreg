from plugins.org_vrg_gps.plugin import GpsPlugin
from sdk.socket.api import ApiMethod


class MethodGetLocation(ApiMethod):
  _plugin: GpsPlugin

  def __init__(self, plugin: GpsPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      if not self._plugin.modem.is_enabled():
        return {"status": "error", "bot_message": "Missing GPS modem"}

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

      return {
        "status": "ok",
        "data": {
          "gps": {"latitude": gps_lat, "longitude": gps_lng, "datetime": gps_datetime},
          "lbs": {
            "latitude": lbs_lat,
            "longitude": lbs_lng,
          },
        },
        "bot_message": f"GPS: {gps_lat},{gps_lng}\nGPS time: {gps_datetime}\nhttps://yandex.ru/maps/?mode=search&text={gps_lat}%2C{gps_lng}\n\nLBS: {lbs_lat},{lbs_lng}\nhttps://yandex.ru/maps/?mode=search&text={lbs_lat}%2C{lbs_lng}",
      }

    except Exception as e:
      self._plugin.logger.warning(f"get gps error: {e}")
      return {"status": "error", "bot_message": "Get GPS error: see logs"}
