import asyncio
from typing import Callable

import plugins.org_vrg_botvk.backoff as backoff
import plugins.org_vrg_botvk.const as const
from plugins.org_vrg_botvk.dispatcher import Dispatcher
from plugins.org_vrg_botvk.keep_alive import KeepAlive
from plugins.org_vrg_botvk.main import Bot, BotChat, BotHealth
from plugins.org_vrg_botvk.vk_api import VkApi
from sdk.service import Plugin

SETTINGS_SYNC_INTERVAL_SEC = 10


class BotvkPlugin(Plugin):
  dispatcher: Dispatcher
  vk_api: VkApi = None
  bot: Bot = None
  chats_loader: Callable[[], list[BotChat]] = None
  keep_alive: KeepAlive
  health: BotHealth
  _pooling_task: asyncio.Task = None
  _sync_task: asyncio.Task = None
  _waiting_settings_logged = False

  def __init__(self, id, name, runner):
    super().__init__(id, name, runner)
    self.keep_alive = KeepAlive()
    self.health = BotHealth()

  async def start(self):
    await super().start()
    self.keep_alive.have_to_wait(
      const.KEEP_ALIVE_WAIT_NETWORK_KEY, const.KEEP_ALIVE_WAIT_NETWORK_SEC
    )  # release in dispatcher

    self._sync_task = asyncio.create_task(self._sync_settings_loop())

  async def _sync_settings_loop(self):
    while self.runner.is_running():
      try:
        self._sync_credentials()
        self._sync_chats()
      except Exception as e:
        self.logger.error(f"Botvk settings sync failed: {e}")
      await asyncio.sleep(SETTINGS_SYNC_INTERVAL_SEC)

  def _sync_credentials(self):
    if self._pooling_task is not None:
      return
    self.state.reload()
    token = self.state.get("vk_bot_token")
    group_id = self.state.get("vk_group_id")
    if not token or not group_id:
      if not self._waiting_settings_logged:
        self.logger.info(
          f"Waiting for bot settings (vk_bot_token / vk_group_id not set). "
          f"Polling every {SETTINGS_SYNC_INTERVAL_SEC}s..."
        )
        self._waiting_settings_logged = True
      return
    self.bot.token = token
    self.bot.group_id = str(group_id)
    self._pooling_task = asyncio.create_task(
      self.dispatcher.start_pooling(backoff.NormalBackoff())
    )

  def _sync_chats(self):
    self.bot.set_chats(self.chats_loader())

  async def stop(self):
    await super().stop()
    await self._stop_pooling()

  async def _stop_pooling(self):
    if self._sync_task and not self._sync_task.done():
      self._sync_task.cancel()
      await asyncio.gather(self._sync_task, return_exceptions=True)
    if self._pooling_task is None:
      return
    await self.vk_api.abort()
    await self.dispatcher.stop_pooling()
    if not self._pooling_task.done():
      self._pooling_task.cancel()
      await asyncio.gather(self._pooling_task, return_exceptions=True)
