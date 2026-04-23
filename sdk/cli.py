import asyncio
import json
import logging
import pathlib
import signal
import sys
from argparse import ArgumentParser, Namespace
from asyncio import AbstractEventLoop

from sdk.socket.api import ApiClient, ApiResponse, create_api_client
from sdk.socket.client import Connection, DefaultConnectionListener
from sdk.socket.requests import RequestsController
from sdk.videoreg import Videoreg


class MyConnectionListener(DefaultConnectionListener):
  runner: "CliRunner"

  def __init__(self, runner: "CliRunner"):
    super().__init__()
    self.runner = runner

  async def on_connected(self, connection):
    asyncio.create_task(self.runner.perform_user_request_on_socket_connected())


class CliRunner:
  """Connects to the bus socket and executes a single API call from the command line."""

  loop: AbstractEventLoop = None
  videoreg: Videoreg
  args: Namespace
  stop_event: asyncio.Event
  connection: Connection
  api_client: ApiClient

  def __init__(self):
    self.stop_event = asyncio.Event()

  def _signal_stop(self, sig: signal.Signals):
    self.logger.warning(f"signal {sig}")
    self.stop_event.set()

  async def run(self):
    self.loop = asyncio.get_running_loop()

    self.loop.add_signal_handler(signal.SIGTERM, self._signal_stop, signal.SIGTERM)
    self.loop.add_signal_handler(signal.SIGINT, self._signal_stop, signal.SIGINT)

    self.logger = create_logger()

    parser = ArgumentParser()
    parser.add_argument(
      "--videoreg-project-home",
      dest="project_home",
      type=pathlib.Path,
      help="Working directory full path",
      required=True,
    )
    parser.add_argument(
      "--skill", dest="skill", type=str, help="Skill", choices=["api"], required=True
    )
    parser.add_argument("params", nargs="+", help="Arguments")

    self.args = parser.parse_args()

    self.videoreg = Videoreg(home=self.args.project_home)

    await self.init_socket("cli")

    await self.stop_event.wait()

    await self.connection.disconnect(reconnect=False)

  async def init_socket(self, client_id: str):
    my_listener = MyConnectionListener(self)
    self.connection = Connection(
      client_id=client_id,
      listener=my_listener,
      logger=self.logger,
      loop=self.loop,
      socket_path=self.videoreg.private_path("event-bus.socket"),
    )

    requests_controller = RequestsController.for_connection(self.connection)

    self.api_client = create_api_client(requests_controller, self.logger)

    await self.connection.connect()

  async def perform_user_request_on_socket_connected(self):
    if self.args.skill == "api":
      await self._exec_api(self.args)

  async def _exec_api(self, args):
    if len(args.params) < 1:
      raise Exception("Missing API method argument")

    method_name = args.params[0]
    method_args = args.params[1] if len(args.params) > 1 else ""

    try:
      # await asyncio.sleep(0.1)
      try:
        response: ApiResponse = await self.api_client.exec(method_name, json.loads(method_args))
      except json.JSONDecodeError:
        response: ApiResponse = await self.api_client.exec(method_name, method_args)

      print(response)
    except Exception as e:
      self.logger.exception(e)
    finally:
      self.stop_event.set()


def create_logger():
  logger = logging.getLogger("cli")
  logger.setLevel(logging.WARNING)
  stream_handler = logging.StreamHandler(stream=sys.stdout)
  stream_handler.setFormatter(logging.Formatter("%(message)s"))
  logger.addHandler(stream_handler)
  return logger
