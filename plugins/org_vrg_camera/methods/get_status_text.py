from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.socket.api import ApiMethod

_STATE_EMOJI = {"record": "🟢", "pause": "🟡", "stop": "🔴"}


class MethodGetStatusText(ApiMethod):
  """Returns a short human-readable camera status for the `/status` bot summary."""

  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      video_state = self._plugin.video_state.value
      emoji = _STATE_EMOJI.get(video_state, "")

      thermal_status = self._plugin.thermal_status
      thermal_label = self._plugin.runner.i18n.t(f"camera.thermal_status_{thermal_status}")

      text = f"Camera: {emoji} {video_state}\nThermal: {thermal_label}"

      return {"status": "ok", "data": {"text": text}}
    except Exception as e:
      self._plugin.logger.error(f"Error in get_status_text: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
