from dataclasses import dataclass
from logging import Logger

from sdk.state import State


class Context:
  logger: Logger
  http_logger: Logger
  state: State

  def __init__(self, state: State, logger: Logger, http_logger: Logger):
    self.logger = logger
    self.http_logger = http_logger
    self.state = state


class BotChat:
  username: str
  chat_id: str

  def __init__(self, username: str, chat_id):
    self.username = username
    self.chat_id = str(chat_id)


class Bot:
  """Holds VK community bot credentials and the list of authorized chats.

  For a VK community bot a user direct-message peer_id equals the user id, so a
  chat_id stored here is the VK user id (vk_user_id) used as peer_id.
  """

  token: str
  group_id: str
  chats: list[BotChat]
  context: Context

  def __init__(self, token, group_id, chats: list[BotChat], context):
    self.token = token
    self.group_id = group_id
    self.chats = chats
    self.context = context

  def set_chats(self, chats: list[BotChat]) -> None:
    self.chats = chats

  def find_chat(self, chat_id) -> "BotChat | None":
    chat_id_str = str(chat_id)
    return next((c for c in self.chats if c.chat_id == chat_id_str), None)

  def get_admin_chat(self) -> "BotChat | None":
    return next((c for c in self.chats if c.username == "admin"), None)


class Command:
  def __init__(self, name: str):
    self.name = name

  async def invoke(self, bot: Bot, chat: BotChat, args: str):
    pass


@dataclass
class MenuButton:
  """A single command exposed in the VK keyboard menu.

  label is shown to the user; callback_data follows the Telegram-compatible
  scheme command__<plugin>__<command> and is carried inside the VK button payload.
  """

  label: str
  callback_data: str


class Callback:
  prefix: str

  def __init__(self, prefix: str):
    self.prefix = prefix

  async def invoke(self, bot: Bot, chat: BotChat, callback_data: str, message_id: int = None):
    pass
