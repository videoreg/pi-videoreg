from plugins.org_vrg_gps.modem import Modem


class ModemImpl(Modem):
  def is_enabled(self) -> bool:
    return True

  @property
  def modem_id(self) -> str:
    return 1

  async def enable(self) -> bool:
    return True

  async def enable_gps(self) -> bool:
    return True

  async def get_location_gps(self) -> dict:
    return {
      "longitude": "30.325850479289837",
      "latitude": "59.936090169086306",
      "datetime": None,
      "speed": "60",
    }

  async def disable_gps(self) -> bool:
    return True

  async def enable_lbs(self) -> bool:
    return True

  async def get_location_lbs(self) -> dict:
    return {
      "longitude": "30.365276",
      "latitude": "59.754425",
    }
