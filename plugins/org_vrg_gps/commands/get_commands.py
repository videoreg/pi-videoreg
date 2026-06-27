from plugins.org_vrg_gps.plugin import GpsPlugin
from sdk.gateway import Gateway, GatewayCommand


class CommandGetCommands(GatewayCommand):
  _plugin: GpsPlugin

  def __init__(self, plugin: GpsPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, gateway: Gateway, payload, args):
    location_gps = await self._plugin.modem.get_location_gps()
    location_lbs = await self._plugin.modem.get_location_lbs()

    if location_gps:
      gps_lat = location_gps["latitude"]
      gps_lng = location_gps["longitude"]
      # gps_datetime = location_gps["datetime"]
    else:
      gps_lat = "unknown"
      gps_lng = "unknown"
      # gps_datetime = "unknown"

    if location_lbs:
      lbs_lat = location_lbs["latitude"]
      lbs_lng = location_lbs["longitude"]
    else:
      lbs_lat = "unknown"
      lbs_lng = "unknown"

    bot_message = f"Location:\n\nGPS: {gps_lat},{gps_lng}\nhttps://yandex.ru/maps/?mode=search&text={gps_lat}%2C{gps_lng}\n\nLBS: {lbs_lat},{lbs_lng}\nhttps://yandex.ru/maps/?mode=search&text={lbs_lat}%2C{lbs_lng}"

    await gateway.send_text(
      payload=payload,
      text=bot_message,
      keyboard=[
        [{"text": "List tracks", "callback_data": "command__gps__list_tracks"}],
      ],
    )
