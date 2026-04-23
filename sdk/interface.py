import asyncio
from dataclasses import dataclass
from enum import Enum
from logging import Logger
from typing import Any

from sdk.socket.api import ApiClient, ApiMethod
from sdk.socket.requests import RequestTimeoutError


class InterfaceInteractions(Enum):
  TEXT = "text"
  STATUS = "status"
  IMAGE = "image"
  VIDEO = "video"
  DOCUMENT = "document"


class Interface:
  """Sends user-facing responses (text, image, video, etc.) to an interface plugin via the API."""

  interactions: dict[InterfaceInteractions, str]
  _api_client: ApiClient
  _logger: Logger

  @staticmethod
  def parse_interfaces(
    interfaces_manifest: list[dict], logger: Logger, api_client: ApiClient
  ) -> dict[str, "Interface"]:
    result: dict[str, Interface] = {}

    for interface_manifest in interfaces_manifest:
      name = interface_manifest.get("name")
      interactions = interface_manifest.get("interactions")

      if not name or not interactions:
        continue

      result[name] = Interface(interactions, api_client, logger)

    return result

  def __init__(
    self, interactions: dict[InterfaceInteractions, str], api_client: ApiClient, logger: Logger
  ):
    self.interactions = interactions
    self._api_client = api_client
    self._logger = logger

  def support(self, interaction: InterfaceInteractions) -> bool:
    return interaction in self.interactions

  async def send_text(self, payload: Any, text: str, keyboard: Any = None) -> bool:
    method = self.interactions[InterfaceInteractions.TEXT.value]
    if not method:
      raise Exception("Unsopported interaction: text")
    args = {"payload": payload, "text": text, "keyboard": keyboard}
    return await self._interact(method, args)

  async def send_status(self, payload: Any, status: str):
    method = self.interactions[InterfaceInteractions.STATUS.value]
    if not method:
      raise Exception("Unsopported interaction: status")
    args = {"payload": payload, "status": status}
    return await self._interact(method, args)

  async def send_image(self, payload: Any, path: str):
    method = self.interactions[InterfaceInteractions.IMAGE.value]
    if not method:
      raise Exception("Unsopported interaction: image")
    args = {"payload": payload, "path": path}
    return await self._interact(method, args)

  async def send_video(self, payload: Any, path: str, width: int, height: int):
    method = self.interactions[InterfaceInteractions.VIDEO.value]
    if not method:
      raise Exception("Unsopported interaction: video")
    args = {"payload": payload, "path": path, "width": width, "height": height}
    return await self._interact(method, args)

  async def send_document(self, payload: Any, path: str):
    method = self.interactions[InterfaceInteractions.DOCUMENT.value]
    if not method:
      raise Exception("Unsopported interaction: document")
    args = {"payload": payload, "path": path}
    return await self._interact(method, args)

  async def _interact(self, method: str, args: Any) -> bool:
    try:
      result = await self._api_client.exec(method, args)
      return result.is_ok()
    except RequestTimeoutError:
      self._logger.warning(f"interface: {method} timeout")
      return False


class InterfaceCommandResponse:
  """Base class for typed responses returned by command handlers to the interface."""

  def to_dict(self) -> dict:
    raise NotImplementedError()


@dataclass
class InterfaceCommandResponseText(InterfaceCommandResponse):
  text: str
  keyboard: Any = None

  def to_dict(self):
    return {"text": self.text, "keyboard": self.keyboard}


@dataclass
class InterfaceCommandResponseStatus(InterfaceCommandResponse):
  status: str

  def to_dict(self):
    return {"status": self.status}


@dataclass
class InterfaceCommandResponseImage(InterfaceCommandResponse):
  path: str

  def to_dict(self):
    return {"path": self.path}


@dataclass
class InterfaceCommandResponseVideo(InterfaceCommandResponse):
  path: str
  width: int
  height: int

  def to_dict(self):
    return {"path": self.path, "width": self.width, "height": self.height}


@dataclass
class InterfaceCommandResponseDocument(InterfaceCommandResponse):
  path: str

  def to_dict(self):
    return {"path": self.path}


class InterfaceCommand:
  """Base class for user command handlers invoked through an interface."""

  async def exec(self, interface: Interface, payload: Any, args: Any):
    pass


class InterfaceCommandMethod(ApiMethod):
  """ApiMethod that dispatches interface commands to the matching InterfaceCommand handler."""

  _interfaces: dict[str, Interface]
  _commands: dict[str, InterfaceCommand]

  def __init__(self, interfaces: dict[str, Interface], commands: dict[str, InterfaceCommand]):
    self._interfaces = interfaces
    self._commands = commands

  async def exec(self, args):
    if not isinstance(args, dict):
      args = {}

    command_name = args.get("command")
    command_payload = args.get("payload")
    command_args = args.get("args")
    interface_name = args.get("interface")

    if not command_name:
      return {"status": "error", "error": "command is required"}

    if not interface_name:
      return {"status": "error", "error": "interface is required"}

    command = self._commands.get(command_name)
    if not command:
      return {"status": "error", "error": f"unknown command: {command_name}"}

    interface = self._interfaces[interface_name]
    if not interface:
      return {"status": "error", "error": f"unknown interface: {interface_name}"}

    asyncio.create_task(command.exec(interface, command_payload, command_args))

    return {"status": "ok"}
