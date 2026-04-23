import asyncio

import plugins.org_vrg_bot.backoff as backoff
import plugins.org_vrg_bot.const as const
from plugins.org_vrg_bot.dispatcher import Dispatcher
from plugins.org_vrg_bot.keep_alive import KeepAlive
from plugins.org_vrg_bot.telegram_api import TelegramApi
from sdk.service import Plugin


class BotPlugin(Plugin):
  dispatcher: Dispatcher
  tg_api: TelegramApi = None
  keep_alive: KeepAlive
  _last_chargin_state = None
  _pooling_task: asyncio.Task = None

  def __init__(self, id, name, runner):
    super().__init__(id, name, runner)
    self.keep_alive = KeepAlive()

  async def start(self):
    await super().start()
    self.keep_alive.have_to_wait(
      const.KEEP_ALIVE_WAIT_NETWORK_KEY, const.KEEP_ALIVE_WAIT_NETWORK_SEC
    )  # release in dispatcher
    
    # TODO: Delete if NormalBackoff is ok, and PowerSaveBackoff is not needed
    # asyncio.create_task(self._start_power_loop())

    self._pooling_task = asyncio.create_task(
      self.dispatcher.start_pooling(backoff.NormalBackoff())
    )

  async def stop(self):
    await super().stop()
    await self._stop_pooling()

  async def _stop_pooling(self):
    await self.tg_api.abort()
    await self.dispatcher.stop_pooling()
    if self._pooling_task and not self._pooling_task.done():
      self._pooling_task.cancel()
      await asyncio.gather(self._pooling_task, return_exceptions=True)

  # TODO: Delete if NormalBackoff is ok, and PowerSaveBackoff is not needed
  #
  # async def _start_power_loop(self):
  #   while self.runner.is_running():
  #     is_charging_status = await self.runner.pisugar.get_charging_status_slow_but_safe()
  #     is_charging = False if is_charging_status == -1 else True

  #     if is_charging == self._last_chargin_state:
  #       await asyncio.sleep(5)
  #       continue

  #     self._last_chargin_state = is_charging
  #     await self._stop_pooling()

  #     if is_charging:
  #       self.logger.info("Charging on: switch to normal backoff")
  #       bckoff = backoff.NormalBackoff()
  #     else:
  #       self.logger.info("Charging off: switch to power safe backoff")
  #       bckoff = backoff.PowerSaveBackoff()

  #     self._pooling_task = asyncio.create_task(self.dispatcher.start_pooling(bckoff))

  #     await asyncio.sleep(5)
