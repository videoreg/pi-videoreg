import asyncio
import json
from asyncio import AbstractEventLoop
from logging import Logger
from typing import Any

from sdk.socket.requests import InRequest, InResponse, RequestsController, RequestsListener

TAG = "api:"


class ApiMethod:
  """Base class for a single API method; subclasses implement exec()."""

  async def exec(self, args: Any) -> Any:
    pass


class ApiServer:
  """Dispatches incoming API requests to registered ApiMethod handlers."""

  methods: dict[str, ApiMethod]
  loop: AbstractEventLoop
  requests_controller: RequestsController
  logger: Logger

  def __init__(
    self,
    methods: dict[str, ApiMethod],
    requests_controller: RequestsController,
    logger: Logger,
    loop: AbstractEventLoop,
  ):
    self.methods = methods
    self.requests_controller = requests_controller
    self.logger = logger
    self.loop = loop

  async def exec(self, method_name: str, args: Any, request: InRequest):
    asyncio.create_task(self._exec_task(method_name, args, request))

  async def _exec_task(self, method_name: str, args: Any, request: InRequest):
    method = self.methods.get(method_name, None)
    if method is None:
      return None
    result = await method.exec(args)
    await self.requests_controller.send_response(request, result)


class ApiServerRequestsListener(RequestsListener):
  """Bridges RequestsController events to ApiServer.exec()."""

  server: ApiServer

  def __init__(self, server: ApiServer):
    self.server = server

  async def on_request(self, request: InRequest):
    self.server.logger.debug(f"{TAG} on_request: {request.body}")

    if not isinstance(request.body, dict):
      return

    if "api" not in request.body:
      return

    api = request.body["api"]

    if "method" not in api:
      return

    method_name = str(api["method"])
    args = api.get("args", {})

    await self.server.exec(method_name, args, request)


class ApiResponse:
  """Wraps an InResponse from ApiClient.exec() with convenience accessors (is_ok, get_data, get_error)."""

  method: str
  args: Any
  response: InResponse

  def __init__(self, method: str, args: Any, response: InResponse):
    self.method = method
    self.args = args
    self.response = response

  def __str__(self):
    return json.dumps(self.to_dict(), indent=2)

  def to_dict(self) -> dict:
    return {"method": self.method, "args": self.args, "response": self.response.to_dict()}

  def is_ok(self) -> bool:
    if not self.response or not self.response.body:
      return False

    if not isinstance(self.response.body, dict):
      return False

    status = self.response.body.get("status", None)
    if status != "ok":
      return False

    return True

  def get_data(self) -> dict:
    if not self.response or not self.response.body:
      return None

    if not isinstance(self.response.body, dict):
      return None

    return self.response.body.get("data", None)

  def get_error(self) -> str:
    if not self.response or not self.response.body:
      return None

    if not isinstance(self.response.body, dict):
      return None

    return self.response.body.get("error", None)


class ApiClient:
  """Sends API requests over the bus and awaits typed responses."""

  requests_controller: RequestsController
  logger: Logger

  def __init__(self, requests_controller: RequestsController, logger: Logger):
    self.requests_controller = requests_controller
    self.logger = logger

  async def exec(self, method: str, args: Any, timeout: float = None) -> ApiResponse:
    prefix, method_name = method.split(".")

    response: InResponse = await self.requests_controller.send_request(
      to_channel=f"{prefix}", body={"api": {"method": method_name, "args": args}}, timeout=timeout
    )

    return ApiResponse(method, args, response)


def create_api_server(
  requests_controller: RequestsController,
  logger: Logger,
  loop: AbstractEventLoop,
  methods: dict[str, ApiMethod],
) -> ApiServer:

  server = ApiServer(methods, requests_controller, logger, loop)
  requests_listener = ApiServerRequestsListener(server)

  requests_controller.listeners.append(requests_listener)

  return server


def create_api_client(requests_controller: RequestsController, logger: Logger) -> ApiClient:
  client = ApiClient(requests_controller, logger)
  return client
