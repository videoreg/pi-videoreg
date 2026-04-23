import asyncio
import json
import uuid
from asyncio import AbstractEventLoop, Future
from collections.abc import Callable
from typing import Any

from sdk.socket.client import Connection, ConnectionListener


class RequestTimeoutError(Exception):
  pass


class OutRequest:
  """An outgoing request pending a response, identified by a short UUID."""

  id: str
  body: Any
  loop: AbstractEventLoop = None
  timeout: int
  response_future: Future

  def __init__(self, id: str, body: Any, timeout: float = 10.0):
    self.id = id
    self.body = body
    self.timeout = timeout
    pass

  def to_dict(self) -> dict:
    return {"id": self.id, "body": self.body}


class InRequest:
  """An incoming request received from the bus, carrying sender and reply metadata."""

  from_: str
  reply_to: str  # explicit reply channel (plugin's own channel)
  id: str
  body: Any

  def __init__(self, from_: str, reply_to: str, id: str, body: Any):
    self.from_ = from_
    self.reply_to = reply_to
    self.id = id
    self.body = body

  @staticmethod
  def parse(from_: str, reply_to: str, data: dict) -> "InRequest":
    if "id" not in data or "body" not in data:
      raise Exception("Wrong format")
    return InRequest(from_, reply_to, data["id"], data["body"])


class OutResponse:
  """A response being sent back to the caller of an InRequest."""

  request_id: str
  body: Any

  def __init__(self, request_id: str, body: Any):
    self.request_id = request_id
    self.body = body

  @staticmethod
  def from_request(request: InRequest, body: Any) -> "OutResponse":
    return OutResponse(request_id=request.id, body=body)

  def to_dict(self) -> dict:
    return {"request_id": self.request_id, "body": self.body}


class InResponse:
  """A response received from the bus for a previously sent OutRequest."""

  request_id: str
  body: Any

  def __init__(self, request_id: str, body: Any):
    self.request_id = request_id
    self.body = body

  def to_dict(self) -> dict:
    return {"request_id": self.request_id, "body": self.body}

  def is_ok(self) -> bool:
    if not self.body:
      return False

    if not isinstance(self.body, dict):
      return False

    status = self.body.get("status", None)
    if status != "ok":
      return False

    return True

  @staticmethod
  def parse(data: dict) -> "InResponse":
    if "request_id" not in data or "body" not in data:
      raise Exception("Wrong format")
    return InResponse(data["request_id"], data["body"])


class RequestsListener:
  """Callback interface for handling incoming requests."""

  async def on_request(self, request: InRequest):
    pass


class RequestsController:
  """Manages the request/response lifecycle: sends requests, resolves futures, and routes incoming requests to listeners."""

  _send_data: Callable
  _waiting: dict[str, OutRequest]
  listeners: list[RequestsListener]
  listener: "RequestsConnectionListener"

  def __init__(
    self, send_data: Callable, parent_listener: ConnectionListener, own_channel: str = None
  ):
    self._send_data = send_data
    self._own_channel = own_channel
    self._waiting = {}
    self.listeners = []
    self.listener = RequestsConnectionListener(self, parent_listener)

  @classmethod
  def for_connection(cls, connection: Connection) -> "RequestsController":
    """Convenience factory for standalone Connection usage (e.g. CLI)."""
    parent_listener = connection.listener
    controller = cls(connection.send_data, parent_listener, own_channel=connection.client_id)
    connection.listener = controller.listener
    return controller

  async def send_request(self, to_channel: str, body: Any, timeout: float = None) -> InResponse:
    loop = asyncio.get_running_loop()
    request_id = str(uuid.uuid4())[:8]
    request = OutRequest(request_id, body, timeout=timeout if timeout is not None else 10.0)
    request.loop = loop
    request.response_future = loop.create_future()

    self._waiting[request.id] = request

    await self._send_data(to_channel, {"request": request.to_dict(), "reply_to": self._own_channel})

    try:
      await asyncio.wait_for(request.response_future, timeout=request.timeout)
      self._waiting.pop(request.id, None)
      return request.response_future.result()
    except TimeoutError:
      self._waiting.pop(request.id, None)
      raise RequestTimeoutError()

  async def send_response(self, request: InRequest, body: Any):
    reply_to = request.reply_to or request.from_
    if reply_to is None:
      raise Exception("Cannot determine reply channel for request!")

    response = OutResponse.from_request(request, body)

    await self._send_data(reply_to, {"response": response.to_dict()})

  async def handle_request(self, request: InRequest):
    for l in self.listeners:
      await l.on_request(request)

  async def handle_response(self, response: InResponse):
    if response.request_id in self._waiting:
      request = self._waiting[response.request_id]
      request.response_future.set_result(response)


class RequestsConnectionListener(ConnectionListener):
  """ConnectionListener that intercepts request/response envelopes and delegates the rest to a parent listener."""

  _controller: RequestsController
  _parent_listener: ConnectionListener

  def __init__(self, controller: RequestsController, parent_listener: ConnectionListener):
    super().__init__()
    self._controller = controller
    self._parent_listener = parent_listener

  async def on_connected(self, connection):
    await self._parent_listener.on_connected(connection)

  async def on_disconnected(self, connection):
    await self._parent_listener.on_disconnected(connection)

  async def on_message(self, connection: Connection, message: str):
    handled = False
    try:
      message_json: dict = json.loads(message)
      if "data" in message_json:
        handled = await self.on_data(
          data=message_json["data"], from_=message_json.get("from", None)
        )
    except Exception as e:
      connection.logger.exception(f"{TAG} error wile parsing message: {e}")
    if not handled:
      await self._parent_listener.on_message(connection, message)

  async def on_data(self, data: Any, from_: str) -> bool:
    if "request" in data:
      reply_to = data.get("reply_to", None) or from_
      request = InRequest.parse(from_, reply_to, data.get("request", {}))
      if request is not None:
        await self._controller.handle_request(request)
      return True
    elif "response" in data:
      response = InResponse.parse(data.get("response", {}))
      if response is not None:
        await self._controller.handle_response(response)
      return True
    else:
      return False


TAG = "request:"
