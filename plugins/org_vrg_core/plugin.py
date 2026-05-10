import asyncio

from sdk.journal import JournalRecord, JournalServer
from sdk.power import ChargingStatus
from sdk.service import Plugin


class CorePlugin(Plugin):
  journal_server: JournalServer = None
  _last_charging_status = None

  def __init__(self, id, name, runner):
    super().__init__(id, name, runner)

  async def start(self):
    await super().start()
    self.journal_server.write(self.id, JournalRecord(type="start", data=None))
    asyncio.create_task(self._check_charging_loop())

  async def stop(self):
    self.journal_server.write(self.id, JournalRecord(type="stop", data=None))
    await super().stop()

  def init_journal_server(self):
    self.journal_server = JournalServer(self.id, self.runner.videoreg)

  async def _check_charging_loop(self):
    while self.runner.is_running():
      try:
        charging_status = await self.runner.power_supply.get_charging_status_slow_but_safe()
        if charging_status != self._last_charging_status and charging_status != ChargingStatus.UNKNOWN:
          event_type = "charging_on" if charging_status == ChargingStatus.CHARGING else "charging_off"
          self.journal_server.write("org_vrg_power", JournalRecord(type=event_type, data=None))
        self._last_charging_status = charging_status
      except Exception as e:
        self.logger.debug(f"charging status check error: {e}")
      await asyncio.sleep(5)
