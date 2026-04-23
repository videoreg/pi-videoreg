from dataclasses import dataclass
from enum import Enum


class VideoMode(Enum):
  TO_FILE = "file"
  TO_STREAM = "stream"
  BOTH = "both"


@dataclass
class VideoParams:
  fps: int = 15
  bitrate: int = 4000000
  camera_mode_str: str = "1920:1080"
  width: int = 1920
  height: int = 1080
  hflip: bool = False
  vflip: bool = False
  screenshot: bool = (True,)
  path: str = None
  duration: int = 0


class CameraControls:
  async def start_video(self, mode: VideoMode, params: VideoParams = None):
    raise NotImplementedError()

  async def stop_video(self):
    raise NotImplementedError()

  async def take_photo(
    self, path: str, is_screenshot: bool, is_night: bool, hflip: bool = False, vflip: bool = False
  ):
    raise NotImplementedError()

  async def take_video(self, params: VideoParams = None):
    raise NotImplementedError()

  def is_recording(self) -> bool:
    raise NotImplementedError()

  def is_recording_completed(self) -> bool:
    raise NotImplementedError()

  async def shutdown(self):
    raise NotImplementedError()
