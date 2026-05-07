from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.interface import Interface, InterfaceCommand


class CommandGetCommands(InterfaceCommand):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, interface: Interface, payload, args):
    camera_state = self._plugin.video_state.value
    if camera_state == "record":
      emoji = "🟢 "
    elif camera_state == "pause":
      emoji = "🟡 "
    elif camera_state == "stop":
      emoji = "🔴 "
    else:
      emoji = ""

    await interface.send_text(
      payload=payload,
      text=f"Camera state: {emoji}{camera_state}",
      keyboard=[
        [
          {"text": "Start", "callback_data": "command__camera__start"},
          {"text": "Pause", "callback_data": "command__camera__pause"},
        ],
        [{"text": "Take photo", "callback_data": "command__camera__photo"}],
        [{"text": "Take photo (night mode)", "callback_data": "command__camera__photo__night"}],
        [{"text": "List videos", "callback_data": "command__camera__list_videos"}],
        [{"text": "List photos", "callback_data": "command__camera__list_photos"}],
        [{"text": "Start stream", "callback_data": "command__camera__stream"}],
      ],
    )
