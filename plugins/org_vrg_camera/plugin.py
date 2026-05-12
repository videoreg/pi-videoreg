import asyncio
import os
import shutil
from datetime import datetime
from enum import Enum

import plugins.org_vrg_camera.const as const
import plugins.org_vrg_camera.osd as osd
from plugins.org_vrg_camera.camera_controls import CameraControls, VideoMode, VideoParams
from plugins.org_vrg_camera.h264_watcher import H264FolderWatcher
from plugins.org_vrg_camera.jpeg_watcher import JpegFolderWatcher
from plugins.org_vrg_camera.thermal_throttle import ThermalAction, ThermalThrottle
from plugins.org_vrg_stat.functions import get_cpu_temp
from sdk.journal import JournalRecord
from sdk.media_manager import MediaFileType
from sdk.power import ChargingStatus
from sdk.service import Plugin


class VideoState(Enum):
  STOP = "stop"
  START = "record"
  PAUSE = "pause"
  STREAM = "stream"

  def print(self):
    icons = {"record": "🟢 ", "pause": "🟡 ", "stop": "🔴 ", "stream": "🔵 "}
    return f"Camera state: {icons.get(self.value, '')}{self.value}"


_VIDEO_STATE_EVENTS = {
  VideoState.START: "video_start",
  VideoState.STOP: "video_stop",
  VideoState.PAUSE: "video_pause",
  VideoState.STREAM: "stream_start",
}


class CameraPlugin(Plugin):
  HLS_DIR = "/run/videoreg/hls"

  _video_state: VideoState
  _camera_controls: CameraControls
  _osd: osd.OSD
  is_first_loop_done = False
  _jpeg_watcher: "JpegFolderWatcher"
  _suspended = False
  _stream_timer_task: asyncio.Task = None

  def __init__(self, id, name, runner):
    super().__init__(id, name, runner)
    self._video_state = VideoState.STOP
    self._osd = osd.OSD(self.runner.videoreg)
    self._converting_names: set = set()
    self._h264_watcher: H264FolderWatcher = None
    self._jpeg_watcher: JpegFolderWatcher = None
    self._stream_timer_task = None
    self._thermal_throttle = ThermalThrottle()
    self.HLS_DIR = runner.videoreg.plugin_private_path(id, "hls")

  @property
  def video_state(self) -> VideoState:
    return self._video_state

  @property
  def thermal_status(self) -> str:
    return self._thermal_throttle.status.value

  @video_state.setter
  def video_state(self, value: VideoState):
    if self._video_state == value:
      return
    self._video_state = value
    if self.journal_client:
      asyncio.create_task(
        self.journal_client.write(JournalRecord(type=_VIDEO_STATE_EVENTS[value], data=None))
      )

  def init_camera_controls(self, camera_controls: CameraControls):
    self._camera_controls = camera_controls

  async def start(self):
    await super().start()
    os.makedirs(self.HLS_DIR, exist_ok=True)
    self._osd.reset()
    asyncio.create_task(self._lifecycle_loop())
    asyncio.create_task(self._check_files_loop())
    h264_dir = self.runner.videoreg.h264_path()
    self._h264_watcher = H264FolderWatcher(
      h264_dir, self.journal_client, self.runner.media_manager, self.logger
    )
    self._h264_watcher.start()
    jpeg_dir = self.runner.videoreg.jpeg_path()
    self._jpeg_watcher = JpegFolderWatcher(
      jpeg_dir, self.journal_client, self.runner.media_manager, self.logger
    )
    self._jpeg_watcher.start()

  async def stop(self):
    await super().stop()
    await self.stop_video()
    self._osd.reset()
    if self._h264_watcher:
      await self._h264_watcher.stop()
    if self._jpeg_watcher:
      await self._jpeg_watcher.stop()

  async def _lifecycle_loop(self):
    try:
      while self.runner.is_running():
        if self._camera_controls.is_recording_completed():
          await self.stop_video()

        charging_status = await self.runner.power_supply.get_charging_status_slow_but_safe()
        bat_level = await self.runner.power_supply.get_battery_percent()
        cpu_temp = get_cpu_temp()

        self._osd.update(
          [
            osd.Token(key="chrg", text=f"C:{charging_status.to_int()}", weight=osd.WEIGHT_CHRG),
            osd.Token(key="bat", text=f"B:{bat_level if bat_level is not None else '--'}", weight=osd.WEIGHT_BAT),
            osd.Token(key="cpu", text=f"T:{cpu_temp}C", weight=osd.WEIGHT_CPU),
          ]
        )

        if charging_status == ChargingStatus.NOT_CHARGING:
          self._thermal_throttle.reset_status()
          if self.video_state in (VideoState.START, VideoState.STREAM):
            self.logger.info("Detect charging is off: will stop video")
            await self.stop_video()
          elif self.video_state == VideoState.STOP:
            # One wakeup photo on first loop — device just powered on without charging
            if not self.is_first_loop_done:
              self.logger.info("Take wakeup photo")
              try:
                await asyncio.wait_for(
                  self.take_photo(is_screenshot=False, is_night=False), timeout=15
                )
              except TimeoutError:
                self.logger.warning("wakeup photo timeout")

              self._is_wakeup_photo_taken = True
        else:
          user_width = self.state.get(const.KEY_VIDEO_WIDTH, const.DEFAULT_VIDEO_WIDTH)
          action = self._thermal_throttle.update(
            cpu_temp,
            user_width,
            is_recording=self.video_state == VideoState.START,
            is_active=self.video_state in (VideoState.START, VideoState.STREAM),
            is_stopped=self.video_state == VideoState.STOP,
          )
          if action == ThermalAction.DOWNSCALE:
            self.logger.warning(
              f"CPU temp {cpu_temp}C > {const.TEMP_DOWNSCALE_ON}C: downscaling video to 720p/{const.THROTTLE_VIDEO_FPS}fps"
            )
            asyncio.create_task(self.journal_client.write(
              JournalRecord(type="thermal_throttle_on", data={"temp": cpu_temp})
            ))
            await self.restart_video()
          elif action == ThermalAction.RESTORE:
            self.logger.info(
              f"CPU temp {cpu_temp}C < {const.TEMP_DOWNSCALE_OFF}C: restoring full video resolution"
            )
            asyncio.create_task(self.journal_client.write(
              JournalRecord(type="thermal_throttle_off", data={"temp": cpu_temp})
            ))
            await self.restart_video()
          elif action == ThermalAction.STOP:
            self.logger.warning("CPU temp is too high: will stop video")
            asyncio.create_task(self.journal_client.write(
              JournalRecord(type="thermal_overheated", data={"temp": cpu_temp})
            ))
            await self.stop_video()
          elif action == ThermalAction.START:
            self.logger.info("Detect charging is ON and CPU temp is OK: will start video")
            try:
              await asyncio.wait_for(self.start_video(), timeout=15)
            except TimeoutError:
              self.logger.warning("start video timeout")
            except Exception as e:
              self.logger.error(f"start video error: {type(e).__name__}: {e}")
          elif action == ThermalAction.TAKE_PHOTO_AND_WAIT:
            self.logger.warning(
              f"Detect charging is ON but CPU temp is too high {cpu_temp}. Will take photo"
            )
            await self.take_photo(is_screenshot=False, is_night=False)
            await asyncio.sleep(15)  # extra sleep to cooldown

        if not self.is_first_loop_done:
          self.logger.info("first loop done")

        self.is_first_loop_done = True

        await asyncio.sleep(5)

    except asyncio.CancelledError:
      await self._camera_controls.shutdown()

  def _build_video_params(self) -> VideoParams:
    user_width = self.state.get(const.KEY_VIDEO_WIDTH, const.DEFAULT_VIDEO_WIDTH)
    user_height = self.state.get(const.KEY_VIDEO_HEIGHT, const.DEFAULT_VIDEO_HEIGHT)
    user_mode = self.state.get(const.KEY_CAMERA_MODE_STR, const.DEFAULT_CAMERA_MODE_STR)
    user_fps = self.state.get(const.KEY_VIDEO_FPS, const.DEFAULT_VIDEO_FPS)

    if self._thermal_throttle.throttled and user_width > const.DEFAULT_STREAM_VIDEO_WIDTH:
      camera_mode_str = const.DEFAULT_STREAM_CAMERA_MODE_STR
      width = const.DEFAULT_STREAM_VIDEO_WIDTH
      height = const.DEFAULT_STREAM_VIDEO_HEIGHT
      fps = min(user_fps, const.THROTTLE_VIDEO_FPS)
    else:
      camera_mode_str = user_mode
      width = user_width
      height = user_height
      fps = user_fps

    return VideoParams(
      fps=fps,
      bitrate=self.state.get(const.KEY_VIDEO_BITRATE, const.DEFAULT_VIDEO_BITRATE),
      camera_mode_str=camera_mode_str,
      width=width,
      height=height,
      hflip=self.state.get(const.KEY_HFLIP, const.DEFAULT_HFLIP),
      vflip=self.state.get(const.KEY_VFLIP, const.DEFAULT_VFLIP),
      screenshot=self.state.get(const.KEY_SCREENSHOT, const.DEFAULT_SCREENSHOT),
      hls_dir=self.HLS_DIR,
    )

  def _build_stream_video_params(self) -> VideoParams:
    return VideoParams(
      fps=self.state.get(const.KEY_VIDEO_FPS, const.DEFAULT_VIDEO_FPS),
      bitrate=self.state.get(const.KEY_VIDEO_BITRATE, const.DEFAULT_VIDEO_BITRATE),
      camera_mode_str=self.state.get(const.KEY_STREAM_CAMERA_MODE_STR, const.DEFAULT_STREAM_CAMERA_MODE_STR),
      width=self.state.get(const.KEY_STREAM_VIDEO_WIDTH, const.DEFAULT_STREAM_VIDEO_WIDTH),
      height=self.state.get(const.KEY_STREAM_VIDEO_HEIGHT, const.DEFAULT_STREAM_VIDEO_HEIGHT),
      hflip=self.state.get(const.KEY_HFLIP, const.DEFAULT_HFLIP),
      vflip=self.state.get(const.KEY_VFLIP, const.DEFAULT_VFLIP),
      screenshot=False,
      hls_dir=self.HLS_DIR,
    )

  async def start_video(self):
    if self.video_state == VideoState.START and self._camera_controls.is_recording():
      return
    self.video_state = VideoState.START
    try:
      await self._camera_controls.start_video(VideoMode.TO_FILE, self._build_video_params())
    except Exception:
      self.video_state = VideoState.STOP
      raise

  async def restart_video(self):
    if self.video_state != VideoState.START:
      return
    await self.stop_video()
    await self.start_video()

  async def stream_start(self):
    if self.video_state == VideoState.STREAM:
      self._reset_stream_timer()
      return
    if self._camera_controls.is_recording():
      await self._camera_controls.stop_video()
    self._clear_hls_dir()
    await self._camera_controls.start_video(VideoMode.TO_STREAM, self._build_stream_video_params())
    self.video_state = VideoState.STREAM
    self._reset_stream_timer()

  def _clear_hls_dir(self):
    try:
      for name in os.listdir(self.HLS_DIR):
        if name.endswith(('.m3u8', '.ts')):
          try:
            os.unlink(os.path.join(self.HLS_DIR, name))
          except OSError:
            pass
    except OSError:
      pass

  async def stream_stop(self):
    if self.video_state != VideoState.STREAM:
      return
    self._cancel_stream_timer()
    if self._camera_controls.is_recording():
      await self._camera_controls.stop_video()
    self.video_state = VideoState.STOP
    await self.start_video()

  def _cancel_stream_timer(self):
    task = self._stream_timer_task
    self._stream_timer_task = None
    if task and not task.done() and task is not asyncio.current_task():
      task.cancel()

  def _reset_stream_timer(self):
    self._cancel_stream_timer()
    self._stream_timer_task = asyncio.create_task(self._stream_auto_stop())

  async def _stream_auto_stop(self):
    try:
      await asyncio.sleep(60)
      self.logger.info("Stream auto-stopped after 60s timeout")
      await self.stream_stop()
    except asyncio.CancelledError:
      pass

  def stream_status(self) -> dict:
    streaming = self.video_state == VideoState.STREAM
    return {
      "streaming": streaming,
      "hls_url": "/hls/stream.m3u8" if streaming else None,
    }

  async def stop_video(self, pause: bool = False):
    if self.video_state == VideoState.STREAM:
      self._cancel_stream_timer()
    self.video_state = VideoState.PAUSE if pause else VideoState.STOP
    if self._camera_controls.is_recording():
      await self._camera_controls.stop_video()

  async def suspend_video(self):
    was_started = self.video_state == VideoState.START
    await self.stop_video(pause=True)
    self._suspended = was_started

  async def continue_video(self):
    if self._suspended:
      await self.start_video()
      self._suspended = False

  async def take_photo(self, is_screenshot: bool, is_night: bool) -> str:
    date = datetime.today().strftime("%Y-%m-%d_%H-%M-%S")
    try:
      path = str(self.runner.videoreg.jpeg_path(f"{date}.jpg"))
    except PermissionError as e:
      self.logger.error(f"take_photo permission error: {str(e)}")
      return None
    hflip = self.state.get(const.KEY_HFLIP, const.DEFAULT_HFLIP)
    vflip = self.state.get(const.KEY_VFLIP, const.DEFAULT_VFLIP)
    await self._camera_controls.take_photo(path, is_screenshot, is_night, hflip, vflip)
    # self.runner.media_manager.invalidate(MediaFileType.JPEG)
    return path

  async def take_video(self, duration: int) -> str:
    filename = datetime.today().strftime("%Y-%m-%d_%H-%M-%S")
    try:
      path = str(self.runner.videoreg.h264_path(f"{filename}.h264"))
    except PermissionError as e:
      self.logger.error(f"take_video permission error: {str(e)}")
      return None
    params = VideoParams(
      fps=self.state.get(const.KEY_VIDEO_FPS, const.DEFAULT_VIDEO_FPS),
      bitrate=self.state.get(const.KEY_VIDEO_BITRATE, const.DEFAULT_VIDEO_BITRATE),
      camera_mode_str=self.state.get(const.KEY_CAMERA_MODE_STR, const.DEFAULT_CAMERA_MODE_STR),
      width=self.state.get(const.KEY_VIDEO_WIDTH, const.DEFAULT_VIDEO_WIDTH),
      height=self.state.get(const.KEY_VIDEO_HEIGHT, const.DEFAULT_VIDEO_HEIGHT),
      hflip=self.state.get(const.KEY_HFLIP, const.DEFAULT_HFLIP),
      vflip=self.state.get(const.KEY_VFLIP, const.DEFAULT_VFLIP),
      screenshot=self.state.get(const.KEY_SCREENSHOT, const.DEFAULT_SCREENSHOT),
      duration=duration,
    )
    await self._camera_controls.take_video(filename, params)
    # self.runner.media_manager.invalidate(MediaFileType.JPEG)
    return path

  def copy_to_fave(self, name: str, file_type: MediaFileType):
    """Copies a file to the fave folder and notifies MediaManager.
    For H264_FAVE also copies the jpeg thumbnail (if present).
    Returns True if the main file was copied, False if not found."""
    vr = self.runner.videoreg
    if file_type == MediaFileType.H264_FAVE:
      src = vr.h264_path(f"{name}.h264")
      dst = vr.h264_fave_path(f"{name}.h264")
    else:
      src = vr.jpeg_path(f"{name}.jpg")
      dst = vr.jpeg_fave_path(f"{name}.jpg")

    if not src.is_file():
      return False
    if not dst.is_file():
      shutil.copy2(str(src), str(dst))
      self.runner.media_manager.append_file(file_type, dst.name)

    if file_type == MediaFileType.H264_FAVE:
      jpeg_src = vr.jpeg_path(f"{name}.jpg")
      jpeg_dst = vr.jpeg_fave_path(f"{name}.jpg")
      if jpeg_src.is_file() and not jpeg_dst.is_file():
        shutil.copy2(str(jpeg_src), str(jpeg_dst))
        self.runner.media_manager.append_file(MediaFileType.JPEG_FAVE, jpeg_dst.name)

    return True

  def delete_from_fave(self, name: str, file_type: MediaFileType):
    """Removes a file from the fave folder and notifies MediaManager.
    For H264_FAVE also removes the jpeg thumbnail (if present)."""
    vr = self.runner.videoreg
    if file_type == MediaFileType.H264_FAVE:
      path = vr.h264_fave_path(f"{name}.h264")
    else:
      path = vr.jpeg_fave_path(f"{name}.jpg")

    if path.is_file():
      path.unlink()
      self.runner.media_manager.remove_file(file_type, path.name)

    if file_type == MediaFileType.H264_FAVE:
      jpeg_path = vr.jpeg_fave_path(f"{name}.jpg")
      if jpeg_path.is_file():
        jpeg_path.unlink()
        self.runner.media_manager.remove_file(MediaFileType.JPEG_FAVE, jpeg_path.name)

  async def handle_osd_update(self, raw_data):
    try:
      tokens_to_update: list[osd.Token] = [osd.Token(**t) for t in raw_data]
      self._osd.update(tokens_to_update)
    except Exception as e:
      self.logger.warning(f"osd update error {type(e).__name__}: {e}")

  async def _check_files_loop(self):
    await asyncio.sleep(15)
    while self.runner.is_running():
      removed = self.runner.media_manager.remove_old_files(
        MediaFileType.H264, max_files=400, companion_types=[MediaFileType.MP4]
      )
      if removed > 0:
        self.logger.debug(f"removed h264 files {removed}")

      removed = self.runner.media_manager.remove_old_files(MediaFileType.JPEG, max_files=400)
      if removed > 0:
        self.logger.debug(f"removed jpeg files {removed}")

      await asyncio.sleep(60 * 5)
