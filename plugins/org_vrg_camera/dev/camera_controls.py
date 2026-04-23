from plugins.org_vrg_camera.camera_controls import CameraControls, VideoMode, VideoParams


class CameraControlsImpl(CameraControls):
  async def start_video(self, mode: VideoMode, params: VideoParams = None):
    pass

  async def stop_video(self):
    pass

  async def take_photo(
    self, path: str, is_screenshot: bool, is_night: bool, hflip: bool = False, vflip: bool = False
  ):
    pass

  async def take_video(self, params=None):
    pass

  def is_recording(self) -> bool:
    return True

  def is_recording_completed(self) -> bool:
    return False

  async def shutdown(self):
    pass
