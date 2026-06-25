import asyncio
import json

import plugins.org_vrg_botvk.const as const
from plugins.org_vrg_botvk.backoff import Backoff
from plugins.org_vrg_botvk.keep_alive import KeepAlive
from plugins.org_vrg_botvk.main import Bot, BotChat, Callback, Command
from plugins.org_vrg_botvk.vk_api import VkApi


class Dispatcher:
  _bot: Bot
  _vk_api: VkApi
  _commands: list[Command]
  _callbacks: list[Callback]
  _stop_event: asyncio.Event
  _keep_alive: KeepAlive

  def __init__(
    self,
    bot: Bot,
    vk_api: VkApi,
    commands: list[Command],
    callbacks: list[Callback],
    keep_alive: KeepAlive,
  ):
    super().__init__()
    self._bot = bot
    self._vk_api = vk_api
    self._commands = commands
    self._callbacks = callbacks
    self._keep_alive = keep_alive
    self._stop_event = asyncio.Event()
    self._stop_event.set()  # initially not polling

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

    server = None
    key = None
    ts = self._bot.context.state.get("vk_ts")

    while not self._stop_event.is_set():
      has_user_interaction = False
      commands_to_exec: list[tuple[BotChat, str, str]] = []
      callbacks_to_exec: list[tuple[BotChat, str, int]] = []
      events_to_ack: list[tuple[str, int, int]] = []

      try:
        # Obtain (or refresh) the Long Poll server when needed.
        if not server or not key or ts is None:
          lp = await self._vk_api.get_long_poll_server()
          resp = lp.get("response") if isinstance(lp, dict) else None
          if not resp:
            self._bot.context.http_logger.error(f"getLongPollServer failed: {lp}")
            backoff.consider_connection_error()
            await self._delay(backoff)
            continue
          server = resp["server"]
          key = resp["key"]
          if ts is None:
            ts = resp["ts"]
          self._bot.context.state.save({"vk_ts": ts})

        updates = await self._vk_api.poll(
          server,
          key,
          ts,
          http_timeout=backoff.get_http_timeout(),
          wait=backoff.get_wait_timeout(),
        )

        # VK signals expired key/ts via the `failed` field.
        failed = updates.get("failed") if isinstance(updates, dict) else None
        if failed:
          self._bot.context.http_logger.warning(f"a_check failed={failed}")
          if failed == 1:
            ts = updates.get("ts", ts)
            self._bot.context.state.save({"vk_ts": ts})
          else:
            # 2: key expired -> new key; 3: also new ts
            server = None
            key = None
            if failed == 3:
              ts = None
          continue

        ts = updates.get("ts", ts)
        self._bot.context.state.save({"vk_ts": ts})

        for update in updates.get("updates", []):
          utype = update.get("type")
          obj = update.get("object", {}) or {}

          if utype == "message_new":
            has_user_interaction = True

            # API 5.103+: the message lives under object.message
            message = obj.get("message", obj)
            from_id = message.get("from_id")
            chat = self._bot.find_chat(from_id)

            if not chat:
              self._bot.context.logger.warning(f"chat id not allowed: {from_id}")
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
              asyncio.create_task(self._vk_api.send_message(chat.chat_id, "No command"))

          elif utype == "message_event":
            has_user_interaction = True

            user_id = obj.get("user_id")
            chat = self._bot.find_chat(user_id)

            if not chat:
              self._bot.context.logger.warning(f"chat id not allowed: {user_id}")
              continue

            # VK may return the button payload either as an object or as a JSON string.
            payload = obj.get("payload")
            if isinstance(payload, str):
              try:
                payload = json.loads(payload)
              except Exception:
                payload = {}
            callback_data = payload.get("cb", "") if isinstance(payload, dict) else ""
            message_id = obj.get("conversation_message_id")
            event_id = obj.get("event_id")
            peer_id = obj.get("peer_id")

            self._bot.context.logger.info(f"receive message_event payload: {payload}")

            if event_id:
              events_to_ack.append((event_id, user_id, peer_id))
            callbacks_to_exec.append((chat, callback_data, message_id))

      except TimeoutError:
        self._bot.context.http_logger.warning("a_check: timeout")
        backoff.consider_timeout()
        await self._delay(backoff)
        continue

      except asyncio.CancelledError:
        self._bot.context.http_logger.info("a_check: cancelled, stopping pooling")
        break

      except Exception as e:
        self._bot.context.http_logger.error(f"a_check error {type(e).__name__}: {e}")
        # Force a server refresh on the next iteration.
        server = None
        key = None
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

      for event_id, user_id, peer_id in events_to_ack:
        asyncio.create_task(self._vk_api.send_message_event_answer(event_id, user_id, peer_id))

      for chat, command_name, command_args in commands_to_exec:
        asyncio.create_task(self._handle_command(chat, command_name, command_args))

      for chat, callback_data, message_id in callbacks_to_exec:
        asyncio.create_task(self._handle_callback(chat, callback_data, message_id))

      await self._delay(backoff)

    self._bot.context.logger.warning("stop pooling")

  async def _handle_command(self, chat: BotChat, name: str, args: str):
    for command in self._commands:
      if command.name == name:
        asyncio.create_task(self._vk_api.set_activity(chat.chat_id, "typing"))
        await command.invoke(self._bot, chat, args)
        return

  async def _handle_callback(self, chat: BotChat, data: str, message_id: int = None):
    for callback_handler in self._callbacks:
      if data.startswith(callback_handler.prefix):
        await callback_handler.invoke(self._bot, chat, data, message_id)
        return
