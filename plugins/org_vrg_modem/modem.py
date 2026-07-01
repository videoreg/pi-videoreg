class Modem:
  @property
  def modem_id(self) -> str:
    raise NotImplementedError()

  def is_enabled(self) -> bool:
    raise NotImplementedError()

  async def enable(self) -> bool:
    raise NotImplementedError()

  async def enable_gps(self) -> bool:
    raise NotImplementedError()

  async def disable_gps(self) -> bool:
    raise NotImplementedError()

  async def get_location_gps(self) -> dict:
    raise NotImplementedError()

  async def enable_lbs(self) -> bool:
    raise NotImplementedError()

  async def get_location_lbs(self) -> dict:
    raise NotImplementedError()
