import asyncio

from plugins.org_vrg_botvk.keyboard import menu_keyboard
from plugins.org_vrg_botvk.main import Bot, BotChat, Command, MenuButton
from plugins.org_vrg_botvk.plugin import BotvkPlugin
from plugins.org_vrg_botvk.vk_api import VkApi


class CommandStart(Command):
  _plugin: BotvkPlugin
  _menu_buttons: list[MenuButton]
  _vk_api: VkApi

  def __init__(
    self, plugin: BotvkPlugin, vk_api: VkApi, name, menu_buttons: list[MenuButton]
  ):
    super().__init__(name)
    self._plugin = plugin
    self._menu_buttons = menu_buttons
    self._vk_api = vk_api

  async def invoke(self, bot: Bot, chat: BotChat, args: str):
    try:
      # VK has no native command menu; show the commands as a persistent keyboard.
      keyboard = menu_keyboard(self._menu_buttons)
      await self._vk_api.send_message(chat.chat_id, "Welcome to videoreg!", keyboard=keyboard)

    except asyncio.CancelledError:
      self._plugin.logger.debug("command start cancelled")

    except Exception as e:
      self._plugin.logger.error(f"command start exception {type(e).__name__}: {e}")
