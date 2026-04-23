import asyncio
import json
from asyncio import AbstractEventLoop, Queue, StreamReader, StreamWriter
from logging import Logger
from threading import Event
from typing import Any

EXIT_MESSAGE = "exit"
TAG = "socket:"


class ForceDisconnectException(Exception):
  def __init__(self):
    super().__init__()


class Connection:
  """Async Unix-socket client with auto-reconnect and a write queue."""

  _stop_event = Event()
  client_id: str
  reader: StreamReader = None
  writer: StreamWriter = None
  read_queue: Queue = None
  write_queue: Queue = None
  on_disconnect: Any
  socket_path: str
  logger: Logger
  loop: AbstractEventLoop
  listener: "ConnectionListener"

  def __init__(
    self,
    client_id: str,
    listener: "ConnectionListener",
    loop: AbstractEventLoop,
    logger: Logger,
    socket_path: str,
  ):
    self.client_id = client_id
    self.listener = listener
    self.loop = loop
    self.logger = logger
    self.socket_path = socket_path

  def is_connecting(self):
    return not self._stop_event.is_set() and self.writer is None

  def is_connected(self):
    return not self._stop_event.is_set() and self.writer is not None

  def is_disconnected(self):
    return self._stop_event.is_set()

  async def send_message(self, message: Any):
    if self.is_connected():
      await self.write_queue.put(message)

  async def send_message_json(self, json_to_send: dict):
    await self.send_message(json.dumps(json_to_send))

  async def send_init(self):
    await self.send_message_json({"type": "init", "id": self.client_id})

  async def send_subscribe(self, channels: list[str]):
    await self.send_message_json({"type": "subscribe", "channels": channels})

  async def send_unsubscribe(self, channels: list[str]):
    await self.send_message_json({"type": "unsubscribe", "channels": channels})

  async def send_data(self, to_channel: str, data: Any):
    await self.send_message_json({"type": "data", "to": to_channel, "data": data})

  async def connect(self):
    try:
      if self.is_disconnected():
        self.logger.info(f"{TAG} disconnected")
        await self.listener.on_disconnected(self)

      self._stop_event = Event()
      self.read_queue = Queue()
      self.write_queue = Queue()

      while self.is_connecting():
        try:
          reader, writer = await asyncio.open_unix_connection(
            self.socket_path, limit=4 * 1024 * 1024
          )
          self.logger.info(f"{TAG} connected")

          self.reader = reader
          self.writer = writer

          asyncio.create_task(self._handle_connection())

          await self.send_init()
          await self.listener.on_connected(self)

          break
        except (ConnectionRefusedError, FileNotFoundError):
          self.logger.error(f"{TAG} connection failed. Retry in 5 seconds")
          await asyncio.sleep(1)  # wait 1 second before retrying
        except Exception:
          self.logger.exception(f"{TAG} unexpected error")
          break

    except asyncio.CancelledError:
      await self.disconnect(reconnect=False)

  async def disconnect(self, reconnect: bool):
    if not self.is_connected():
      return

    writer = self.writer
    self.writer = None
    self.reader = None
    writer.close()
    try:
      await writer.wait_closed()
    except Exception:
      pass
    self._stop_event.set()

    # Unblock write_to_socket which may be suspended on write_queue.get()
    if self.write_queue:
      await self.write_queue.put(EXIT_MESSAGE)

    if reconnect:
      await self.connect()

  async def _handle_connection(self):
    async def read_from_socket(connection: Connection):
      try:
        while connection.is_connected():
          data = await connection.reader.readline()
          if not data:
            raise Exception("Received empty data")
          decoded = data.decode().strip()
          await connection.listener.on_message(connection, decoded)
      except Exception:
        await connection.disconnect(reconnect=True)
      finally:
        pass

    async def write_to_socket(connection: Connection):
      try:
        while connection.is_connected():
          data = await connection.write_queue.get()
          if data == EXIT_MESSAGE:
            raise ForceDisconnectException()
          connection.writer.write(f"{data}\n".encode())
          await connection.writer.drain()
      except ForceDisconnectException:
        connection.logger.info(f"{TAG} force disconnect")
        await connection.disconnect(reconnect=False)
      except Exception:
        await connection.disconnect(reconnect=True)
      finally:
        pass

    await asyncio.gather(read_from_socket(self), write_to_socket(self))


class EasyConnection:
  """Thin wrapper that delays send_data until a connection is available."""

  connection: Connection = None  # Connection or MuxConnection

  async def send_data(self, to_channel: str, data, wait: float = None) -> bool:
    if wait is not None:
      loop = asyncio.get_running_loop()
      deadline = loop.time() + wait
      while self.connection is None or not self.connection.is_connected():
        remaining = deadline - loop.time()
        if remaining <= 0:
          return False
        await asyncio.sleep(min(0.1, remaining))
    if self.connection is not None and self.connection.is_connected():
      await self.connection.send_data(to_channel, data)
      return True
    return False


class ConnectionListener:
  """Interface for receiving connection lifecycle and message events."""

  async def on_connected(self, connection: Connection):
    pass

  async def on_disconnected(self, connection: Connection):
    pass

  async def on_message(self, connection: Connection, message: str):
    pass


class DefaultConnectionListener(ConnectionListener):
  """ConnectionListener that parses incoming JSON and delegates to on_data()."""

  async def on_connected(self, connection: Connection):
    pass

  async def on_disconnected(self, connection: Connection):
    pass

  async def on_message(self, connection: Connection, message: str):
    # connection.logger.debug(f"{TAG} received message: {message}")
    try:
      message_json: dict = json.loads(message)
      if "data" in message_json:
        await self.on_data(
          message_json.get("data"), message_json.get("to"), message_json.get("from")
        )
    except Exception as e:
      connection.logger.exception(f"{TAG} error wile parsing message: {e}")

  async def on_data(self, data: Any, to: Any, from_: Any = None):
    pass
