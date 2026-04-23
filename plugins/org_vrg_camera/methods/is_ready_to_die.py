from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.socket.api import ApiMethod


class MethodIsReadyToDie(ApiMethod):
  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    if not self._plugin.is_first_loop_done:
      return {"status": "ok", "ready": False, "why": "waiting first loop"}

    return {"status": "ok", "ready": True}
