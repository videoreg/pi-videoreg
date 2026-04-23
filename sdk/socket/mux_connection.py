import asyncio
import json
from asyncio import AbstractEventLoop
from logging import Logger

from sdk.socket.client import Connection, ConnectionListener


class _Dispatcher(ConnectionListener):
  """Routes incoming bus messages to the right plugin listener based on 'to' field."""

  def __init__(self, mux_conn: "MuxConnection"):
    self._mux_conn = mux_conn

  async def on_connected(self, connection: Connection):
    await self._mux_conn._on_connected(connection)

  async def on_disconnected(self, connection: Connection):
    pass

  async def on_message(self, connection: Connection, message: str):
    await self._mux_conn._dispatch(message)


class MuxConnection:
  """Single shared bus connection for all plugins in a service."""

  _connection: Connection
  # plugin_name -> (all_channels, top_listener)
  _registrations: dict[str, tuple[list[str], ConnectionListener]]
  # channel -> top_listener (for fast lookup)
  _channel_listeners: dict[str, ConnectionListener]
  _started: bool

  def __init__(self, service_id: str, socket_path: str, loop: AbstractEventLoop, logger: Logger):
    self._registrations = {}
    self._channel_listeners = {}
    self._started = False
    self._connection = Connection(
      client_id=service_id,
      listener=_Dispatcher(self),
      loop=loop,
      logger=logger,
      socket_path=socket_path,
    )

  def is_connected(self) -> bool:
    return self._connection.is_connected()

  async def send_data(self, to_channel: str, data):
    await self._connection.send_data(to_channel, data)

  def register(self, plugin_name: str, channels: list[str], listener: ConnectionListener):
    """Register plugin channels and listener. Called from Plugin.init_socket()."""
    all_channels = list(channels) + [plugin_name]
    self._registrations[plugin_name] = (all_channels, listener)
    for ch in all_channels:
      self._channel_listeners[ch] = listener
    if self._connection.is_connected():
      asyncio.create_task(self._connection.send_subscribe(all_channels))

  def unregister(self, plugin_name: str):
    """Unregister plugin channels. Called from Plugin.stop()."""
    reg = self._registrations.pop(plugin_name, None)
    if reg:
      channels, _ = reg
      for ch in channels:
        self._channel_listeners.pop(ch, None)
      if self._connection.is_connected():
        asyncio.create_task(self._connection.send_unsubscribe(channels))

  def start(self):
    """Start the connection (called once by ServiceRunner after all plugins are built)."""
    if not self._started:
      self._started = True
      asyncio.create_task(self._connection.connect())

  async def disconnect(self):
    await self._connection.disconnect(reconnect=False)

  async def _on_connected(self, connection: Connection):
    """Subscribe all registered channels after (re)connect."""
    all_channels = []
    for channels, _ in self._registrations.values():
      all_channels.extend(channels)
    if all_channels:
      await self._connection.send_subscribe(all_channels)
    for _, listener in self._registrations.values():
      try:
        await listener.on_connected(connection)
      except Exception:
        pass

  async def _dispatch(self, message: str):
    """Route received message to the matching plugin listener by 'to' channel."""
    try:
      message_json: dict = json.loads(message)
      to = message_json.get("to")
      if not to:
        return
      listener = self._channel_listeners.get(to)
      if listener:
        await listener.on_message(self._connection, message)
    except Exception:
      pass
