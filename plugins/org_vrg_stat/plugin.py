import asyncio

from plugins.org_vrg_stat.tracker import Tracker
from sdk.service import Plugin


class StatPlugin(Plugin):
  _tracker: Tracker

  def init_tracker(self, tracker: Tracker):
    self._tracker = tracker

  async def start(self):
    await super().start()
    asyncio.create_task(self._tracker.start_loop())

  async def stop(self):
    self._tracker.stop_loop()
    return await super().stop()
