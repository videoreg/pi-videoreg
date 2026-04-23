from plugins.org_vrg_gps.plugin import GpsPlugin
from plugins.org_vrg_gps.tracks_keyboard import get_tracks_keyboard
from sdk.interface import Interface, InterfaceCommand


class CommandListTracks(InterfaceCommand):
  _plugin: GpsPlugin

  def __init__(self, plugin: GpsPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, interface: Interface, payload, args):
    page = 1
    try:
      page = int(args)
    except:
      pass

    keyboard_data = await get_tracks_keyboard(
      videoreg=self._plugin.runner.videoreg, logger=self._plugin.logger, page=page
    )

    if keyboard_data.all_files_count == 0:
      await interface.send_text(payload=payload, text="There are no gps tracks")
      return

    bot_message = f"Page {keyboard_data.page} of {keyboard_data.count_pages}"

    if keyboard_data.first_file_datetime_str:
      bot_message += f" ({keyboard_data.first_file_datetime_str})"

    await interface.send_text(payload=payload, text=bot_message, keyboard=keyboard_data.buttons)
