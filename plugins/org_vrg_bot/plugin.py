import asyncio
from typing import Callable

import plugins.org_vrg_bot.backoff as backoff
import plugins.org_vrg_bot.const as const
from plugins.org_vrg_bot.dispatcher import Dispatcher
from plugins.org_vrg_bot.keep_alive import KeepAlive
from plugins.org_vrg_bot.main import Bot, BotChat
from plugins.org_vrg_bot.telegram_api import TelegramApi
from sdk.service import Plugin

CHATS_RELOAD_INTERVAL_SEC = 10


class BotPlugin(Plugin):
  dispatcher: Dispatcher
  tg_api: TelegramApi = None
  bot: Bot = None
  chats_loader: Callable[[], list[BotChat]] = None
  keep_alive: KeepAlive
  _last_chargin_state = None
  _pooling_task: asyncio.Task = None
  _wait_token_task: asyncio.Task = None
  _chats_reload_task: asyncio.Task = None

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

    self._wait_token_task = asyncio.create_task(self._wait_token_and_start_pooling())
    self._chats_reload_task = asyncio.create_task(self._reload_chats_loop())

  async def _reload_chats_loop(self):
    while self.runner.is_running():
      await asyncio.sleep(CHATS_RELOAD_INTERVAL_SEC)
      try:
        self.bot.set_chats(self.chats_loader())
      except Exception as e:
        self.logger.error(f"Failed to reload bot chats: {e}")

  async def _wait_token_and_start_pooling(self):
    while self.runner.is_running():
      self.state.reload()
      token = self.state.get("tg_bot_token")
      if token:
        self.bot.base_url = f"https://api.telegram.org/bot{token}"
        self._pooling_task = asyncio.create_task(
          self.dispatcher.start_pooling(backoff.NormalBackoff())
        )
        return
      self.logger.info("Waiting for bot settings (tg_bot_token not set). Retrying in 5 seconds...")
      await asyncio.sleep(5)

  async def stop(self):
    await super().stop()
    await self._stop_pooling()

  async def _stop_pooling(self):
    if self._chats_reload_task and not self._chats_reload_task.done():
      self._chats_reload_task.cancel()
      await asyncio.gather(self._chats_reload_task, return_exceptions=True)
    if self._wait_token_task and not self._wait_token_task.done():
      self._wait_token_task.cancel()
      await asyncio.gather(self._wait_token_task, return_exceptions=True)
    if self._pooling_task is None:
      return
    await self.tg_api.abort()
    await self.dispatcher.stop_pooling()
    if not self._pooling_task.done():
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
