import asyncio
import importlib
import pathlib
import signal
from argparse import ArgumentParser
from asyncio import AbstractEventLoop
from logging.handlers import RotatingFileHandler
from threading import Event

import yaml

import sdk.log as log
from sdk.i18n import I18n
from sdk.journal import JournalClient
from sdk.media_manager import MediaManager
from sdk.pisugar import PiSugar
from sdk.socket.api import ApiClient, ApiMethod, ApiServer, create_api_client, create_api_server
from sdk.socket.client import ConnectionListener, DefaultConnectionListener, EasyConnection
from sdk.socket.mux_connection import MuxConnection
from sdk.socket.requests import RequestsController
from sdk.state import State
from sdk.videoreg import Manifest, Videoreg


class PluginConnectionListener(DefaultConnectionListener):
  """Default connection listener bound to a plugin instance."""

  plugin: "Plugin"

  def __init__(self, plugin: "Plugin"):
    super().__init__()
    self.plugin = plugin


class ConnectionListenerFactory:
  """Creates a ConnectionListener for a plugin; override to inject custom listener."""

  def create(self, plugin: "Plugin") -> ConnectionListener:
    return PluginConnectionListener(plugin)


class Plugin:
  """Base class for all videoreg plugins; holds shared state and socket/API helpers."""

  id: str
  name: str
  runner: "ServiceRunner"
  state: State
  _connection: "MuxConnection" = None  # shared service connection (set by init_socket)
  _easy_connection: EasyConnection
  _requests_controller: RequestsController = None
  _api_server: ApiServer = None
  api_client: ApiClient = None
  journal_client: JournalClient = None
  _stop_event: Event
  _rotating_log_file_handler: RotatingFileHandler
  _socket_client_id: str = None  # plugin's own channel name (for unregister)

  def __init__(self, id: str, name: str, runner: "ServiceRunner"):
    self.id = id
    self.name = name
    self.runner = runner
    self._easy_connection = EasyConnection()
    self._stop_event = asyncio.Event()
    self._tasks = set()
    state_file_path = self.runner.videoreg.private_path(f"data/plugins/{self.id}/state.json")
    state_file_path.parent.mkdir(parents=True, exist_ok=True)
    self.state = State(state_file_path)

  async def start(self):
    pass  # shared connection is started by ServiceRunner after all plugins are built

  async def stop(self):
    if self.logger:
      self.logger.info("stop plugin")

    if self._rotating_log_file_handler:
      self._rotating_log_file_handler.flush()

    if self._connection and self._socket_client_id:
      self._connection.unregister(self._socket_client_id)

  def init_logger(self, log_level: str):
    log_file = self.runner.videoreg.private_path(f"log/plugins/{self.id}.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    self._rotating_log_file_handler = log.create_rotating_file_handler(
      log_file, tag=f"{self.name}:"
    )
    self.logger = log.create_logger(
      name=f"logger_plugin_{self.name}",
      log_level=log_level,
      rotating_file_handler=self._rotating_log_file_handler,
      tag=f"{self.name}:",
    )
    self.logger.info("=== NEW SESSION STARTED ===")

  def init_socket(
    self,
    client_id: str,
    channels: list[str],
    socket_path: str = None,
    connection_listener_factory: ConnectionListenerFactory = None,
  ):
    if not connection_listener_factory:
      connection_listener_factory = ConnectionListenerFactory()

    mux_conn = self.runner.get_mux_connection(socket_path)

    plugin_listener = connection_listener_factory.create(self)
    self._requests_controller = RequestsController(
      mux_conn.send_data, plugin_listener, own_channel=client_id
    )

    # Register plugin channels with shared connection; client_id is the default channel
    mux_conn.register(client_id, channels, self._requests_controller.listener)

    self._connection = mux_conn
    self._easy_connection.connection = mux_conn
    self._socket_client_id = client_id

  def init_api_servier(self, methods: dict[str, ApiMethod]) -> ApiServer:
    self._api_server = create_api_server(
      self._requests_controller, self.logger, self.runner.loop, methods
    )
    return self._api_server

  def init_api_client(self) -> ApiClient:
    self.api_client = create_api_client(self._requests_controller, self.logger)
    return self.api_client

  def init_journal_client(self) -> JournalClient:
    self.journal_client = JournalClient(self.id, self._easy_connection)
    return self.journal_client


# RUNNER


class ServiceRunner:
  """Loads plugins from the manifest and runs them inside a single asyncio event loop."""

  loop: AbstractEventLoop = None
  videoreg: Videoreg
  pisugar: PiSugar
  media_manager: MediaManager
  i18n: I18n
  stop_event: asyncio.Event
  runnung_plugins: list[Plugin]
  log_level: str
  _service_name: str = None
  _mux_connection: MuxConnection = None

  def __init__(self):
    self.stop_event = asyncio.Event()
    self.runnung_plugins = []

  def get_mux_connection(self, socket_path: str = None) -> MuxConnection:
    """Lazy-init the shared service connection. Called from Plugin.init_socket()."""
    if self._mux_connection is None:
      if not socket_path:
        socket_path = str(self.videoreg.private_path("event-bus.socket"))
      self._mux_connection = MuxConnection(
        service_id=self._service_name, socket_path=socket_path, loop=self.loop, logger=self.logger
      )
    return self._mux_connection

  def stop(self):
    self.stop_event.set()

  def init_logger(self, log_level: str, systemd_service_name: str):
    log_file = self.videoreg.private_path(f"log/services/{systemd_service_name}.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    rotating_file_handler = log.create_rotating_file_handler(
      log_file, tag=f"{systemd_service_name}:"
    )
    self.logger = log.create_logger(
      "logger_service", log_level, rotating_file_handler, tag=f"{systemd_service_name}:"
    )

  def _signal_stop(self, sig: signal.Signals):
    self.logger.warning(f"signal {sig}")
    self.stop()

  async def run(self):
    self.loop = asyncio.get_running_loop()

    self.loop.add_signal_handler(signal.SIGTERM, self._signal_stop, signal.SIGTERM)
    self.loop.add_signal_handler(signal.SIGINT, self._signal_stop, signal.SIGINT)

    parser = ArgumentParser()
    parser.add_argument(
      "--videoreg-project-home",
      dest="project_home",
      type=pathlib.Path,
      help="Working directory full path",
      required=True,
    )
    parser.add_argument(
      "--service", dest="service", type=str, help="Systemd service name", required=True
    )
    parser.add_argument(
      "--log-level",
      dest="log_level",
      type=str,
      help="Log level: DEBUG,INFO,WARNING,ERROR",
      default="WARNING",
      required=False,
    )
    parser.add_argument(
      "--env",
      dest="env",
      type=str,
      help="Environment: dev, prod, test, etc. If passed, the corresponding manifest file will be loaded (eg. 'videoreg.manifest.dev.yaml'). Exception: for 'prod' manifest will be 'videoreg.manifest.yaml'",
      default="prod",
      required=False,
    )

    args, unknown = parser.parse_known_args()

    if args.env == "prod":
      manifest_file_name = "videoreg.manifest.yaml"
    else:
      manifest_file_name = f"videoreg.manifest.{args.env}.yaml"

    manifest_file_path = args.project_home / manifest_file_name

    with open(manifest_file_path) as f:
      manifest_dict = yaml.safe_load(f)

    manifest = Manifest(**manifest_dict)

    self.videoreg = Videoreg(home=args.project_home, manifest=manifest)
    self.log_level = args.log_level
    self._service_name = args.service

    self.init_logger(args.log_level, systemd_service_name=args.service)

    self.pisugar = PiSugar(self.videoreg, self.logger)
    self.media_manager = MediaManager(self.videoreg)

    sdk_path = args.project_home / "sdk"
    self.i18n = I18n(locale=manifest.locale)
    self.i18n.load_global(sdk_path)

    if args.service not in manifest.services:
      raise ValueError(f"Missing systemd service in manifest: {args.service}")

    plugins = [
      vrg_plugin for vrg_plugin in manifest.plugins if vrg_plugin.get("service") == args.service
    ]

    for plugin_manifest in plugins:
      id = plugin_manifest.get("id")
      module = f"plugins.{id}.plugin_builder"

      self.logger.info(f"load module id {id}")

      plugin_module = importlib.import_module(module)

      build_plugin = plugin_module.build_plugin

      plugin: Plugin = await build_plugin(self, args, plugin_manifest)

      self.i18n.load_plugin(args.project_home / "plugins" / id)
      self.runnung_plugins.append(plugin)

    # Start shared bus connection after all plugins have registered their channels
    if self._mux_connection is not None:
      self._mux_connection.start()

    for plugin in self.runnung_plugins:
      await plugin.start()

    try:
      await self.stop_event.wait()
    finally:
      self.logger.info("stop systemd service")
      await self.on_stop()

  def is_running(self) -> bool:
    return not self.stop_event.is_set()

  async def on_stop(self):
    for plugin in self.runnung_plugins:
      await plugin.stop()
    if self._mux_connection is not None:
      await self._mux_connection.disconnect()
