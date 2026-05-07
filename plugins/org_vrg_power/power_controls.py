
from logging import Logger


class PowerControls:

  def __init__(self, logger: Logger):
    self._logger = logger

  async def start_charging_target(self):
    raise NotImplementedError()
  
  async def stop_charging_target(self):
    raise NotImplementedError()