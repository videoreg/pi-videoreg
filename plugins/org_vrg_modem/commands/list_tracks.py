from plugins.org_vrg_modem.plugin import ModemPlugin
from plugins.org_vrg_modem.tracks_keyboard import get_tracks_keyboard
from sdk.gateway import Gateway, GatewayCommand


class CommandListTracks(GatewayCommand):
  _plugin: ModemPlugin

  def __init__(self, plugin: ModemPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, gateway: Gateway, payload, args):
    page = 1
    try:
      page = int(args)
    except:
      pass

    per_page = gateway.list_page_size or 6
    keyboard_data = await get_tracks_keyboard(
      videoreg=self._plugin.runner.videoreg, logger=self._plugin.logger, page=page, per_page=per_page
    )

    if keyboard_data.all_files_count == 0:
      await gateway.send_text(payload=payload, text="There are no gps tracks")
      return

    bot_message = f"Page {keyboard_data.page} of {keyboard_data.count_pages}"

    if keyboard_data.first_file_datetime_str:
      bot_message += f" ({keyboard_data.first_file_datetime_str})"

    await gateway.send_text(payload=payload, text=bot_message, keyboard=keyboard_data.buttons)
