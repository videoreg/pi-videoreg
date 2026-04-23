import asyncio

import plugins.org_vrg_bot.const as const
from plugins.org_vrg_bot.backoff import Backoff
from plugins.org_vrg_bot.keep_alive import KeepAlive
from plugins.org_vrg_bot.main import Bot, BotChat, Callback, Command
from plugins.org_vrg_bot.telegram_api import TelegramApi


class Dispatcher:
  _bot: Bot
  _tg_api: TelegramApi
  _commands: list[Command]
  _callbacks: list[Callback]
  _stop_event: asyncio.Event
  _keep_alive: KeepAlive

  def __init__(
    self,
    bot: Bot,
    tg_api: TelegramApi,
    commands: list[Command],
    callbacks: list[Callback],
    keep_alive: KeepAlive,
  ):
    super().__init__()
    self._bot = bot
    self._tg_api = tg_api
    self._commands = commands
    self._callbacks = callbacks
    self._keep_alive = keep_alive
    self._stop_event = asyncio.Event()
    self._stop_event.set()  # initially not polling
    self._apitask = None

  async def stop_pooling(self):
    self._stop_event.set()

  async def _delay(self, backoff: Backoff):
    delay = backoff.next_delay()

    self._bot.context.logger.debug(
      "Sleep for %f seconds and try again... (tryings = %d)",
      backoff.get_current_delay(),
      backoff.get_current_counter(),
    )

    await asyncio.sleep(delay)

  async def start_pooling(self, backoff: Backoff):
    if self._stop_event and not self._stop_event.is_set():
      raise Exception("Bot pooling is already started")

    self._stop_event = asyncio.Event()
    is_first_loop = True
    offset = self._bot.context.state.get("offset", 0)

    while not self._stop_event.is_set():
      has_user_interaction = False
      commands_to_exec: list[tuple[BotChat, str, str]] = []
      callbacks_to_exec: list[tuple[BotChat, str]] = []

      try:
        updates = await self._tg_api.get_updates(
          offset=offset,
          http_timeout=backoff.get_http_timeout(),
          tg_timeout=backoff.get_tg_timeout(),
        )

        if updates and "result" in updates:
          for update in updates["result"]:
            if "message" in update:
              has_user_interaction = True

              message = update["message"]
              chat_id = message["chat"]["id"]
              chat = self._bot.find_chat(chat_id)

              if not chat:
                self._bot.context.logger.warning(f"chat id not allowed: {chat_id}")
                continue

              text = message.get("text", "")

              self._bot.context.logger.info(f"receive message text: {text}")

              if text.startswith("/") and len(text) > 1:
                inputs = text.split(" ", 1)
                command_name = inputs[0][1:]
                command_args = inputs[1] if len(inputs) > 1 else ""

                self._bot.context.logger.info(
                  f"detected command: name={command_name}, args={command_args}"
                )

                commands_to_exec.append((chat, command_name, command_args))
              else:
                asyncio.create_task(self._tg_api.send_message(chat.chat_id, "No command"))

            if "callback_query" in update:
              has_user_interaction = True

              callback_query = update["callback_query"]
              chat_id = callback_query["from"]["id"]
              chat = self._bot.find_chat(chat_id)

              if not chat:
                self._bot.context.logger.warning(f"chat id not allowed: {chat_id}")
                continue

              data = callback_query.get("data", "")

              self._bot.context.logger.info(f"receive callback_query data: {data}")

              callbacks_to_exec.append((chat, data))

            offset = update["update_id"] + 1
            self._bot.context.state.save({"offset": offset})

      # except requests.exceptions.ConnectionError:
      #   self._bot.context.http_logger.warning(f"getUpdates: connection error")
      #   backoff.consider_connection_error()
      #   await self._delay(backoff)
      #   continue

      except TimeoutError:
        self._bot.context.http_logger.warning("getUpdates: timeout")
        backoff.consider_timeout()
        await self._delay(backoff)
        continue

      except asyncio.CancelledError:
        self._bot.context.http_logger.info("getUpdates: cancelled, stopping pooling")
        break

      except Exception as e:
        self._bot.context.http_logger.error(f"getUpdates error {type(e).__name__}: {e}")
        backoff.consider_connection_error()
        await self._delay(backoff)
        continue

      # after parsing response

      if is_first_loop:
        self._keep_alive.no_more_need_to_wait(const.KEEP_ALIVE_WAIT_NETWORK_KEY)
        is_first_loop = False

      if has_user_interaction:
        self._keep_alive.have_to_wait(
          const.KEEP_ALIVE_WAIT_USER_INTERACTION_KEY, const.KEEP_ALIVE_WAIT_USER_INTERACTION_SEC
        )

      backoff.consider_user_interaction(has_user_interaction)

      for chat, command_name, command_args in commands_to_exec:
        asyncio.create_task(self._handle_command(chat, command_name, command_args))

      for chat, callback_data in callbacks_to_exec:
        asyncio.create_task(self._handle_callback(chat, callback_data))

      await self._delay(backoff)

    self._bot.context.logger.warning("stop pooling")

  async def _handle_command(self, chat: BotChat, name: str, args: str):
    for command in self._commands:
      if command.name == name:
        asyncio.create_task(self._tg_api.send_chat_action(chat.chat_id, "typing"))
        await command.invoke(self._bot, chat, args)
        return

  async def _handle_callback(self, chat: BotChat, data: str):
    for callback_handler in self._callbacks:
      if data.startswith(callback_handler.prefix):
        await callback_handler.invoke(self._bot, chat, data)
        return
