import asyncio
from dataclasses import dataclass
from enum import Enum
from logging import Logger
from typing import Any

from sdk.socket.api import ApiClient, ApiMethod
from sdk.socket.requests import RequestTimeoutError


class GatewayInteractions(Enum):
  TEXT = "text"
  EDIT_TEXT = "edit_text"
  STATUS = "status"
  IMAGE = "image"
  VIDEO = "video"
  DOCUMENT = "document"


class Gateway:
  """Sends user-facing responses (text, image, video, etc.) to a gateway plugin via the API."""

  interactions: dict[GatewayInteractions, str]
  list_page_size: "int | None"
  _api_client: ApiClient
  _logger: Logger

  @staticmethod
  def parse_gateways(
    gateways_manifest: list[dict], logger: Logger, api_client: ApiClient
  ) -> dict[str, "Gateway"]:
    result: dict[str, Gateway] = {}

    for gateway_manifest in gateways_manifest:
      name = gateway_manifest.get("name")
      interactions = gateway_manifest.get("interactions")
      list_page_size = gateway_manifest.get("list_page_size")

      if not name or not interactions:
        continue

      result[name] = Gateway(interactions, api_client, logger, list_page_size)

    return result

  def __init__(
    self,
    interactions: dict[GatewayInteractions, str],
    api_client: ApiClient,
    logger: Logger,
    list_page_size: "int | None" = None,
  ):
    self.interactions = interactions
    self.list_page_size = list_page_size
    self._api_client = api_client
    self._logger = logger

  def support(self, interaction: GatewayInteractions) -> bool:
    return interaction in self.interactions

  async def send_text(self, payload: Any, text: str, keyboard: Any = None) -> bool:
    method = self.interactions[GatewayInteractions.TEXT.value]
    if not method:
      raise Exception("Unsopported interaction: text")
    args = {"payload": payload, "text": text, "keyboard": keyboard}
    return await self._interact(method, args)

  async def edit_message(self, payload: Any, text: str, keyboard: Any = None) -> bool:
    method = self.interactions.get(GatewayInteractions.EDIT_TEXT.value)
    if not method:
      raise Exception("Unsupported interaction: edit_text")
    args = {"payload": payload, "text": text, "keyboard": keyboard}
    return await self._interact(method, args)

  async def send_status(self, payload: Any, status: str):
    method = self.interactions[GatewayInteractions.STATUS.value]
    if not method:
      raise Exception("Unsopported interaction: status")
    args = {"payload": payload, "status": status}
    return await self._interact(method, args)

  async def send_image(self, payload: Any, path: str):
    method = self.interactions[GatewayInteractions.IMAGE.value]
    if not method:
      raise Exception("Unsopported interaction: image")
    args = {"payload": payload, "path": path}
    return await self._interact(method, args)

  async def send_video(self, payload: Any, path: str, width: int, height: int):
    method = self.interactions[GatewayInteractions.VIDEO.value]
    if not method:
      raise Exception("Unsopported interaction: video")
    args = {"payload": payload, "path": path, "width": width, "height": height}
    return await self._interact(method, args)

  async def send_document(self, payload: Any, path: str):
    method = self.interactions[GatewayInteractions.DOCUMENT.value]
    if not method:
      raise Exception("Unsopported interaction: document")
    args = {"payload": payload, "path": path}
    return await self._interact(method, args)

  async def _interact(self, method: str, args: Any) -> bool:
    try:
      result = await self._api_client.exec(method, args)
      return result.is_ok()
    except RequestTimeoutError:
      self._logger.warning(f"gateway: {method} timeout")
      return False


class GatewayCommandResponse:
  """Base class for typed responses returned by command handlers to the gateway."""

  def to_dict(self) -> dict:
    raise NotImplementedError()


@dataclass
class GatewayCommandResponseText(GatewayCommandResponse):
  text: str
  keyboard: Any = None

  def to_dict(self):
    return {"text": self.text, "keyboard": self.keyboard}


@dataclass
class GatewayCommandResponseStatus(GatewayCommandResponse):
  status: str

  def to_dict(self):
    return {"status": self.status}


@dataclass
class GatewayCommandResponseImage(GatewayCommandResponse):
  path: str

  def to_dict(self):
    return {"path": self.path}


@dataclass
class GatewayCommandResponseVideo(GatewayCommandResponse):
  path: str
  width: int
  height: int

  def to_dict(self):
    return {"path": self.path, "width": self.width, "height": self.height}


@dataclass
class GatewayCommandResponseDocument(GatewayCommandResponse):
  path: str

  def to_dict(self):
    return {"path": self.path}


class GatewayCommand:
  """Base class for user command handlers invoked through a gateway."""

  async def exec(self, gateway: Gateway, payload: Any, args: Any):
    pass


class GatewayCommandMethod(ApiMethod):
  """ApiMethod that dispatches gateway commands to the matching GatewayCommand handler."""

  _gateways: dict[str, Gateway]
  _commands: dict[str, GatewayCommand]

  def __init__(self, gateways: dict[str, Gateway], commands: dict[str, GatewayCommand]):
    self._gateways = gateways
    self._commands = commands

  async def exec(self, args):
    if not isinstance(args, dict):
      args = {}

    command_name = args.get("command")
    command_payload = args.get("payload")
    command_args = args.get("args")
    gateway_name = args.get("gateway")

    if not command_name:
      return {"status": "error", "error": "command is required"}

    if not gateway_name:
      return {"status": "error", "error": "gateway is required"}

    command = self._commands.get(command_name)
    if not command:
      return {"status": "error", "error": f"unknown command: {command_name}"}

    gateway = self._gateways[gateway_name]
    if not gateway:
      return {"status": "error", "error": f"unknown gateway: {gateway_name}"}

    asyncio.create_task(command.exec(gateway, command_payload, command_args))

    return {"status": "ok"}
