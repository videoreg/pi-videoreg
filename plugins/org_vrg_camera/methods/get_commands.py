from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.socket.api import ApiMethod


class MethodGetCommands(ApiMethod):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    camera_state = self._plugin.video_state.value
    if camera_state == "record":
      emoji = "🟢 "
    elif camera_state == "pause":
      emoji = "🟡 "
    elif camera_state == "stop":
      emoji = "🔴 "
    else:
      emoji = ""

    return {
      "status": "ok",
      "bot_message": f"Camera state: {emoji}{camera_state}",
      "bot_buttons": [
        [
          {"text": "Start", "callback_data": "button_plugin__camera.video_start"},
          {"text": "Pause", "callback_data": "button_plugin__camera.video_pause"},
          # {"text": "Stop", "callback_data": "button_plugin__camera.video_stop"},
        ],
        [{"text": "Take photo", "callback_data": "button_plugin__camera.photo"}],
        [
          {"text": "Take photo (night mode)", "callback_data": "button_plugin__camera.photo__night"}
        ],
        # [{"text": "Take photo (screenshot)", "callback_data": "button_plugin__camera.photo__screenshot"}],
        [{"text": "List videos", "callback_data": "button_plugin__camera.list_videos"}],
        [{"text": "List photos", "callback_data": "button_plugin__camera.list_photos"}],
        # [{"text": "Settings ", "callback_data": "button_plugin__camera.get_settings_commands"}],
        # [{"text": "Video size ", "callback_data": "button_plugin__camera.get_video_sizes"}],
        # [{"text": "Photo size ", "callback_data": "button_plugin__camera.get_photo_sizes"}],
      ],
    }
