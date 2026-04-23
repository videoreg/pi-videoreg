import asyncio
import json
from functools import wraps
from logging import Logger
from typing import Any

import aiohttp

import plugins.org_vrg_bot.const as const
from plugins.org_vrg_bot.main import Bot, BotCommand


def track_task(func):
  """Decorator for automatic task tracking"""

  @wraps(func)
  async def wrapper(self, *args, **kwargs):
    task = asyncio.current_task()
    if task:
      self._tasks.add(task)

    try:
      return await func(self, *args, **kwargs)
    finally:
      if task:
        self._tasks.discard(task)

  return wrapper


class TelegramApi:
  _bot: Bot
  _logger: Logger
  _tasks: set[asyncio.Task]

  def __init__(self, bot: Bot, logger: Logger):
    self._bot = bot
    self._logger = logger
    self._tasks = set()

  async def abort(self):
    """Cancels all active tasks"""
    self._logger.info(f"Aborting {len(self._tasks)} active tasks")
    tasks = list(self._tasks)
    for task in tasks:
      if not task.done():
        task.cancel()

    if tasks:
      await asyncio.gather(*tasks, return_exceptions=True)

    self._tasks.clear()
    self._logger.info("All tasks aborted")

  @track_task
  async def get_updates(self, offset, http_timeout: int, tg_timeout: int):
    method = "getUpdates"
    url = f"{self._bot.base_url}/{method}"
    params = {
      "timeout": tg_timeout,
      "offset": offset,
      "allowed_updates": '["update_id","message","callback_query"]',
    }

    self._log_request(method, params)

    timeout = aiohttp.ClientTimeout(total=http_timeout)
    try:
      async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, params=params) as response:
          response_json = await response.json()

      self._log_response(method, response_json)
      return response_json

    except asyncio.CancelledError:
      self._bot.context.http_logger.info(f"{method}: request cancelled")
      raise

  @track_task
  async def send_message(
    self, chat_id: str, text, reply_markup: Any = None, parse_mode: str = None
  ):
    method = "sendMessage"
    url = f"{self._bot.base_url}/{method}"
    params = {"chat_id": chat_id, "text": text, "timeout": "0"}
    if reply_markup:
      params["reply_markup"] = reply_markup
    if parse_mode:
      params["parse_mode"] = parse_mode

    self._log_request(method, params)

    try:
      timeout = aiohttp.ClientTimeout(total=const.TIMEOUT_SEND_MESSAGE)
      async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, data=params) as response:
          response_json = await response.json()

      self._log_response(method, response_json)
      return response_json

    except asyncio.CancelledError:
      self._bot.context.http_logger.info(f"{method}: request cancelled")
      raise

  @track_task
  async def send_photo(self, chat_id: str, photo_path, reply_markup: Any = None):
    method = "sendPhoto"
    url = f"{self._bot.base_url}/{method}"

    try:
      data = aiohttp.FormData()
      data.add_field("chat_id", chat_id)
      data.add_field("photo", open(photo_path, "rb"), filename="photo.jpg")

      self._log_request(method, {"chat_id": chat_id, "photo": photo_path})

      timeout = aiohttp.ClientTimeout(total=const.TIMEOUT_SEND_PHOTO)
      async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, data=data) as response:
          response_json = await response.json()

      self._log_response(method, response_json)
      return response_json

    except asyncio.CancelledError:
      self._bot.context.http_logger.info(f"{method}: request cancelled")
      raise

  @track_task
  async def send_video(self, chat_id: str, video_path, width, height):
    method = "sendVideo"
    url = f"{self._bot.base_url}/{method}"

    try:
      data = aiohttp.FormData()
      data.add_field("chat_id", chat_id)
      data.add_field("width", str(width))
      data.add_field("height", str(height))
      data.add_field("video", open(video_path, "rb"), filename="video.mp4")

      self._log_request(
        method, {"chat_id": chat_id, "width": width, "height": height, "video": video_path}
      )

      timeout = aiohttp.ClientTimeout(total=const.TIMEOUT_SEND_VIDEO)
      async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, data=data) as response:
          response_json = await response.json()

      self._log_response(method, response_json)
      return response_json

    except asyncio.CancelledError:
      self._bot.context.http_logger.info(f"{method}: request cancelled")
      raise

  @track_task
  async def send_document(self, chat_id: str, document_path):
    method = "sendDocument"
    url = f"{self._bot.base_url}/{method}"

    try:
      data = aiohttp.FormData()
      data.add_field("chat_id", chat_id)
      data.add_field("document", open(document_path, "rb"))

      self._log_request(method, {"chat_id": chat_id, "document": document_path})

      timeout = aiohttp.ClientTimeout(total=const.TIMEOUT_SEND_DOCUMENT)
      async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, data=data) as response:
          response_json = await response.json()

      self._log_response(method, response_json)
      return response_json

    except asyncio.CancelledError:
      self._bot.context.http_logger.info(f"{method}: request cancelled")
      raise

  @track_task
  async def send_chat_action(self, chat_id: str, action: str):
    method = "sendChatAction"
    url = f"{self._bot.base_url}/{method}"
    params = {"chat_id": chat_id, "action": action}

    self._log_request(method, params)

    try:
      timeout = aiohttp.ClientTimeout(total=const.TIMEOUT_SEND_MESSAGE)
      async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, data=params) as response:
          response_json = await response.json()

      self._log_response(method, response_json)
      return response_json

    except asyncio.CancelledError:
      self._bot.context.http_logger.info(f"{method}: request cancelled")
      raise

  @track_task
  async def set_my_name(self, name: str):
    method = "setMyName"
    url = f"{self._bot.base_url}/{method}"
    data = {"name": name}

    self._log_request(method, data)

    try:
      timeout = aiohttp.ClientTimeout(total=const.TIMEOUT_SEND_MESSAGE)
      async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, data=data) as response:
          response_json = await response.json()

      self._log_response(method, response_json)
      return response_json

    except asyncio.CancelledError:
      self._bot.context.http_logger.info(f"{method}: request cancelled")
      raise

  @track_task
  async def set_my_commands(self, chat_id: str, commands: list[BotCommand]):
    method = "setMyCommands"
    url = f"{self._bot.base_url}/{method}"

    commands_json: list = []
    for command in commands:
      commands_json.append({"command": command.command, "description": command.description})

    data = {
      "chat_id": chat_id,
      "commands": json.dumps(commands_json),
      "scope": json.dumps({"type": "default"}),
    }

    self._log_request(method, data)

    try:
      timeout = aiohttp.ClientTimeout(total=const.TIMEOUT_SEND_MESSAGE)
      async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, data=data) as response:
          response_json = await response.json()

      self._log_response(method, response_json)
      return response_json

    except asyncio.CancelledError:
      self._bot.context.http_logger.info(f"{method}: request cancelled")
      raise

  def _log_request(self, method: str, data: dict):
    self._logger.debug(f"request: method={method}, data={json.dumps(data)}")

  def _log_response(self, method: str, response_json: dict):
    is_ok = response_json.get("ok", False)
    log_method = self._logger.debug if is_ok else self._logger.error
    log_method(f"response: method={method} json={response_json}")
