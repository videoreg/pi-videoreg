from plugins.org_vrg_camera.photo_keyboard import get_photos_keyboard
from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.interface import InterfaceCommand


class CommandListPhotos(InterfaceCommand):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, interface, payload, args):
    page = 1
    try:
      page = int(args)
    except:
      pass

    keyboard_data = await get_photos_keyboard(
      videoreg=self._plugin.runner.videoreg, logger=self._plugin.logger, page=page
    )

    if keyboard_data.all_files_count == 0:
      await interface.send_text(payload=payload, text="There are no photos")
      return

    text = f"Page {keyboard_data.page} of {keyboard_data.count_pages}"

    if keyboard_data.first_file_datetime_str:
      text += f" ({keyboard_data.first_file_datetime_str})"

    if isinstance(payload, dict) and payload.get("message_id"):
      await interface.edit_message(payload=payload, text=text, keyboard=keyboard_data.buttons)
    else:
      await interface.send_text(payload=payload, text=text, keyboard=keyboard_data.buttons)
