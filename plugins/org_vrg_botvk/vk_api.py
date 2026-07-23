import asyncio
import json
import random
from functools import wraps
from logging import Logger
from typing import Any

import aiohttp

import plugins.org_vrg_botvk.const as const
from plugins.org_vrg_botvk.main import Bot

VK_API_BASE = "https://api.vk.com/method"


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


class VkApi:
  """Async client for the VK community (group) bot API.

  Uses the Bots Long Poll API for receiving updates and messages.* / photos.* /
  docs.* methods for sending. Credentials (community token, group id) are read
  from the shared Bot instance, so they can change at runtime.
  """

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

  # --- low level helpers -------------------------------------------------

  async def _call_method(self, method: str, params: dict, timeout: int) -> dict:
    url = f"{VK_API_BASE}/{method}"
    data = {
      **{k: v for k, v in params.items() if v is not None},
      "access_token": self._bot.token,
      "v": const.VK_API_VERSION,
    }

    self._log_request(method, {k: v for k, v in data.items() if k != "access_token"})

    client_timeout = aiohttp.ClientTimeout(total=timeout)
    try:
      async with aiohttp.ClientSession(timeout=client_timeout) as session:
        async with session.post(url, data=data) as response:
          response_json = await response.json(content_type=None)

      self._log_response(method, response_json)
      return response_json

    except asyncio.CancelledError:
      self._bot.context.http_logger.info(f"{method}: request cancelled")
      raise

  async def _upload_file(self, upload_url: str, field: str, file_path, filename: str) -> dict:
    timeout = aiohttp.ClientTimeout(total=const.TIMEOUT_UPLOAD)
    data = aiohttp.FormData()
    data.add_field(field, open(file_path, "rb"), filename=filename)

    self._log_request("upload", {"url": upload_url, "field": field, "file": str(file_path)})

    try:
      async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(upload_url, data=data) as response:
          response_json = await response.json(content_type=None)

      self._log_response("upload", response_json)
      return response_json

    except asyncio.CancelledError:
      self._bot.context.http_logger.info("upload: request cancelled")
      raise

  # --- long poll ---------------------------------------------------------

  @track_task
  async def get_long_poll_server(self) -> dict:
    return await self._call_method(
      "groups.getLongPollServer",
      {"group_id": self._bot.group_id},
      timeout=const.TIMEOUT_SEND_MESSAGE,
    )

  @track_task
  async def poll(self, server: str, key: str, ts, http_timeout: int, wait: int) -> dict:
    params = {"act": "a_check", "key": key, "ts": ts, "wait": wait}

    self._log_request("a_check", {"server": server, "ts": ts, "wait": wait})

    client_timeout = aiohttp.ClientTimeout(total=http_timeout)
    try:
      async with aiohttp.ClientSession(timeout=client_timeout) as session:
        async with session.get(server, params=params) as response:
          response_json = await response.json(content_type=None)

      self._log_response("a_check", response_json)
      return response_json

    except asyncio.CancelledError:
      self._bot.context.http_logger.info("a_check: request cancelled")
      raise

  # --- sending -----------------------------------------------------------

  @track_task
  async def send_message(
    self, peer_id, text, keyboard: Any = None, attachment: str = None
  ) -> dict:
    params = {
      "peer_id": peer_id,
      "message": text,
      "random_id": random.randint(1, 2_000_000_000),
      "keyboard": keyboard,
      "attachment": attachment,
    }
    return await self._call_method("messages.send", params, timeout=const.TIMEOUT_SEND_MESSAGE)

  @track_task
  async def edit_message(
    self, peer_id, conversation_message_id, text, keyboard: Any = None
  ) -> dict:
    params = {
      "peer_id": peer_id,
      "conversation_message_id": conversation_message_id,
      "message": text,
      "keyboard": keyboard,
    }
    return await self._call_method("messages.edit", params, timeout=const.TIMEOUT_SEND_MESSAGE)

  @track_task
  async def set_activity(self, peer_id, activity_type: str = "typing") -> dict:
    params = {"peer_id": peer_id, "type": activity_type}
    return await self._call_method("messages.setActivity", params, timeout=const.TIMEOUT_SEND_MESSAGE)

  @track_task
  async def send_message_event_answer(self, event_id: str, user_id, peer_id) -> dict:
    """Acknowledge a callback button press (message_event)."""
    params = {"event_id": event_id, "user_id": user_id, "peer_id": peer_id}
    return await self._call_method(
      "messages.sendMessageEventAnswer", params, timeout=const.TIMEOUT_SEND_MESSAGE
    )

  @track_task
  async def upload_photo(self, peer_id, photo_path) -> "str | None":
    """Full photo upload flow; returns an attachment string like photo{owner}_{id}."""
    server = await self._call_method(
      "photos.getMessagesUploadServer", {"peer_id": peer_id}, timeout=const.TIMEOUT_SEND_MESSAGE
    )
    upload_url = server.get("response", {}).get("upload_url")
    if not upload_url:
      return None

    uploaded = await self._upload_file(upload_url, "photo", photo_path, "photo.jpg")
    if not uploaded.get("photo"):
      return None

    saved = await self._call_method(
      "photos.saveMessagesPhoto",
      {
        "photo": uploaded.get("photo"),
        "server": uploaded.get("server"),
        "hash": uploaded.get("hash"),
      },
      timeout=const.TIMEOUT_SEND_MESSAGE,
    )
    items = saved.get("response")
    if not items:
      return None

    item = items[0]
    return f"photo{item['owner_id']}_{item['id']}"

  @track_task
  async def upload_document(self, peer_id, document_path, title: str = None) -> "str | None":
    """Full document upload flow; returns an attachment string like doc{owner}_{id}."""
    from pathlib import Path

    title = title or Path(document_path).name

    server = await self._call_method(
      "docs.getMessagesUploadServer",
      {"type": "doc", "peer_id": peer_id},
      timeout=const.TIMEOUT_SEND_MESSAGE,
    )
    upload_url = server.get("response", {}).get("upload_url")
    if not upload_url:
      return None

    uploaded = await self._upload_file(upload_url, "file", document_path, title)
    if not uploaded.get("file"):
      return None

    saved = await self._call_method(
      "docs.save",
      {"file": uploaded.get("file"), "title": title},
      timeout=const.TIMEOUT_SEND_MESSAGE,
    )
    doc = saved.get("response", {}).get("doc")
    if not doc:
      return None

    return f"doc{doc['owner_id']}_{doc['id']}"

  # --- logging -----------------------------------------------------------

  def _log_request(self, method: str, data: dict):
    self._logger.debug(f"request: method={method}, data={json.dumps(data, default=str)}")

  def _log_response(self, method: str, response_json: dict):
    is_ok = isinstance(response_json, dict) and "error" not in response_json
    log_method = self._logger.debug if is_ok else self._logger.error
    log_method(f"response: method={method} json={response_json}")
