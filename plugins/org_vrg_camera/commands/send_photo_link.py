import plugins.org_vrg_http.functions as functions
from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.interface import Interface, InterfaceCommand


class CommandSendPhotoLink(InterfaceCommand):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, interface: Interface, payload, args):
    file_name = str(args)

    if not file_name:
      self._plugin.logger.warning(
        f"Command CommandSendPhotoLink: missing file name in args args={args}"
      )
      return

    file_path = self._plugin.runner.videoreg.jpeg_path(f"{file_name}.jpg")

    if not file_path.exists():
      self._plugin.logger.warning(
        f"Command CommandSendPhotoLink: file not exists file_name={file_name}"
      )
      return

    link = await functions.get_link(dir="photo", file_name=file_name)

    await interface.send_text(payload, link)
