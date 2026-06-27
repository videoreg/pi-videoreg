from plugins.org_vrg_camera.photo_keyboard import get_photos_keyboard
from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.gateway import GatewayCommand


class CommandListPhotos(GatewayCommand):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, gateway, payload, args):
    page = 1
    try:
      page = int(args)
    except:
      pass

    per_page = gateway.list_page_size or 6
    keyboard_data = await get_photos_keyboard(
      videoreg=self._plugin.runner.videoreg, logger=self._plugin.logger, page=page, per_page=per_page
    )

    if keyboard_data.all_files_count == 0:
      await gateway.send_text(payload=payload, text="There are no photos")
      return

    text = f"Page {keyboard_data.page} of {keyboard_data.count_pages}"

    if keyboard_data.first_file_datetime_str:
      text += f" ({keyboard_data.first_file_datetime_str})"

    if isinstance(payload, dict) and payload.get("message_id"):
      await gateway.edit_message(payload=payload, text=text, keyboard=keyboard_data.buttons)
    else:
      await gateway.send_text(payload=payload, text=text, keyboard=keyboard_data.buttons)
