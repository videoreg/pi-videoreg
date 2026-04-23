import asyncio
import json
import os
import time
from asyncio import Server, StreamReader, StreamWriter

from sdk.service import Plugin


class Client:
  writer: StreamWriter
  id: str
  channels: list[str]

  def __init__(self, writer: StreamWriter):
    super().__init__()
    self.writer = writer
    self.id = None
    self.channels = []

  async def write(self, data):
    encoded_data = f"{data}\n".encode()
    self.writer.write(encoded_data)
    await self.writer.drain()


class BusPlugin(Plugin):
  _clients: list[Client]
  _server: Server
  _waiting_list: dict[str, list[dict]]  # channel_name => list of data messages
  _waiting_list_lock: asyncio.Lock

  def __init__(self, id, name, runner):
    super().__init__(id, name, runner)
    self._clients = []
    self._waiting_list = {}
    self._waiting_list_lock = asyncio.Lock()

  async def start(self):
    await super().start()
    asyncio.create_task(self._start_server())
    asyncio.create_task(self._start_clear_waiting_list_loop())

  async def stop(self):
    await super().stop()
    if self._server:
      await self._stop_server()

  async def _start_server(self):
    socket_path = self.runner.videoreg.private_path("event-bus.socket")

    if socket_path.exists():
      os.remove(str(socket_path))

    self._server = await asyncio.start_unix_server(
      self._handle_client, path=str(socket_path), limit=4 * 1024 * 1024
    )

    self.logger.info("started")

    async with self._server:
      await self._server.serve_forever()

    self.logger.info("stopped")

  async def _stop_server(self):
    for client in self._clients:
      try:
        client.writer.close()
        await asyncio.wait_for(client.writer.wait_closed(), timeout=1)
      except TimeoutError:
        self.logger.error(f"client close timeout {client.id}")

    self._server.close()

    try:
      await asyncio.wait_for(self._server.wait_closed(), timeout=1)
      self.logger.info("server closed")
    except TimeoutError:
      self.logger.error("server close timeout")

    self._clients = []
    self._server = None

  async def _handle_client(self, reader: StreamReader, writer: StreamWriter):
    self.logger.info("client connected")

    client = Client(writer)
    self._clients.append(client)

    try:
      while self.runner.is_running():
        line = await reader.readline()

        if not line:
          break

        message = line.decode("utf-8").strip()
        self.logger.debug(f"client {client.id} message: {message}")
        await self._handle_message(client, message)
    finally:
      self.logger.info(f"client {client.id} disconnected")
      try:
        self._clients.remove(client)  # here could be concurrency error when stopping service
        writer.close()
        await writer.wait_closed()
      except:
        pass

  async def _handle_message(self, client: Client, message):
    message_json = None

    try:
      message_json = json.loads(message)
    except json.JSONDecodeError as e:
      json_to_send = json.dumps({"type": "error", "data": {"message": f"json error: {e}"}})
      await client.write(json_to_send)

      self.logger.error(f"message json error: {e}")
      return

    try:
      type = message_json.get("type")

      # eg: { "type": "init", "id": "vrg-core" }
      if type == "init":
        id = message_json.get("id")

        if not id or not isinstance(id, str):
          self.logger.warning(f'missing or wrong "id" in message: {message}')
          return

        client.id = id
        # Auto-subscribe to own service channel so responses can be routed back
        client.channels = [client.id]

        self.logger.info(f"client {client.id} init")

        await self._deliver_waiting(client, client.channels)

      # eg: { "type": "subscribe", "channels": ["net", "power"] }
      elif type == "subscribe":
        if client.id is None:
          self.logger.warning("subscribe before init from unidentified client")
          return

        channels = message_json.get("channels", None)
        if not isinstance(channels, list):
          self.logger.warning(f'missing or wrong "channels" in subscribe message: {message}')
          return

        new_channels = [ch for ch in channels if ch not in client.channels]
        client.channels.extend(new_channels)

        self.logger.info(f"client {client.id} subscribed: {new_channels}, total={client.channels}")

        await self._deliver_waiting(client, new_channels)

      # eg: { "type": "unsubscribe", "channels": ["net"] }
      elif type == "unsubscribe":
        if client.id is None:
          self.logger.warning("unsubscribe before init from unidentified client")
          return

        channels = message_json.get("channels", None)
        if not isinstance(channels, list):
          self.logger.warning(f'missing or wrong "channels" in unsubscribe message: {message}')
          return

        client.channels = [ch for ch in client.channels if ch not in channels]
        self.logger.info(
          f"client {client.id} unsubscribed: {channels}, remaining={client.channels}"
        )

      # eg: { "type": "data", "to": "camera", "data": {"foo": "bar"} }
      elif type == "data":
        to_channel = message_json.get("to")

        if not to_channel or not isinstance(to_channel, str):
          self.logger.warning(f'missing or wrong "to" in message: {message}')
          return

        to_channel_clear = to_channel.removeprefix("@")
        clients_to_send = [clnt for clnt in self._clients if to_channel_clear in clnt.channels]

        # if to_channel.startswith("@"):
        #   clients_to_send = clients_to_send[:1]

        json_to_send = json.dumps(
          {
            "type": "data",
            "from": client.id,
            "to": to_channel,
            "data": message_json["data"],
            "timestamp": time.time(),
          }
        )

        if not clients_to_send:
          self.logger.debug("not found clients to send: add to waiting list")

          async with self._waiting_list_lock:
            if to_channel_clear in self._waiting_list:
              self._waiting_list[to_channel_clear].append(json_to_send)
            else:
              self._waiting_list[to_channel_clear] = [json_to_send]
        else:
          client_ids_to_send = [c.id for c in clients_to_send]

          self.logger.debug(f"found clients to send data: {client_ids_to_send}")

          for client in clients_to_send:
            await client.write(json_to_send)

      else:
        self.logger.warning(f'missing or wrong "type" in message: {message}')

    except Exception as e:
      self.logger.error(f"message error {e}")
      json_to_send = json.dumps({"type": "error", "data": {"message": f"error: {e}"}})
      await client.write(json_to_send)

  async def _deliver_waiting(self, client: "Client", channels: list[str]):
    """Deliver queued messages for the given channels to this client."""
    async with self._waiting_list_lock:
      for channel in channels:
        if channel in self._waiting_list:
          messages_to_process = self._waiting_list[channel]

          self.logger.debug(
            f"delivering {len(messages_to_process)} queued messages for channel {channel} to {client.id}"
          )

          while messages_to_process:
            msg = messages_to_process.pop()
            try:
              await client.write(msg)
            except Exception as e:
              self.logger.warning(f"write to {client.id} error: {e}")

          del self._waiting_list[channel]

  async def _start_clear_waiting_list_loop(self):
    await asyncio.sleep(30)
    while self.runner.is_running():
      async with self._waiting_list_lock:
        cur_time = time.time()

        try:
          for channel, messages in self._waiting_list.items():
            self._waiting_list[channel] = [
              message
              for message in messages
              if cur_time - json.loads(message).get("timestamp", 16) < 15
            ]
        except Exception as e:
          self.logger.warning(f"error while clear waiting list loop: {e}")

      await asyncio.sleep(30)
