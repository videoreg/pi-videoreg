import asyncio
import os
import signal
import subprocess
from asyncio.subprocess import Process
from collections import deque
from logging import Logger
from typing import Any

from plugins.org_vrg_camera.camera_controls import CameraControls, VideoMode, VideoParams
from sdk.helper import stream_subprocess
from sdk.videoreg import Videoreg


class CameraControlsImpl(CameraControls):
  _logger: Logger
  _videoreg: Videoreg
  _queue: deque
  _video_process: Process = None

  def __init__(self, logger: Logger, videoreg: Videoreg):
    self._queue: deque = deque()
    self._is_processing: bool = False
    self._lock: asyncio.Lock = asyncio.Lock()
    # self._last_video_params: VideoParams = VideoParams()
    self._logger = logger
    self._videoreg = videoreg

  def is_recording(self) -> bool:
    return self._video_process

  def is_recording_completed(self):
    return self._video_process and self._video_process.returncode is not None

  async def start_video(self, mode: VideoMode, params: VideoParams = None):
    future = asyncio.Future()
    if params is None:
      params = VideoParams()
    await self._add_to_queue("start_video", (mode, params), future)
    return await future

  async def stop_video(self):
    future = asyncio.Future()
    await self._add_to_queue("stop_video", (), future)
    await future

  async def take_photo(
    self, path: str, is_screenshot: bool, is_night: bool, hflip: bool = False, vflip: bool = False
  ):
    future = asyncio.Future()
    await self._add_to_queue("take_photo", (path, is_screenshot, is_night, hflip, vflip), future)
    await future

  async def take_video(self, filename: str, params: VideoParams = None):
    future = asyncio.Future()
    await self._add_to_queue("take_video", (filename, params), future)
    await future

  async def shutdown(self):
    if self._video_process:
      await self.stop_video()

  async def _add_to_queue(self, action_name: str, args: tuple[Any, ...], future: asyncio.Future):
    async with self._lock:
      self._queue.append((action_name, args, future))

    if not self._is_processing:
      self._is_processing = True
      asyncio.create_task(self._process_queue())

  async def _process_queue(self):
    try:
      while True:
        async with self._lock:
          if not self._queue:
            self._is_processing = False
            break
          action_name, args, future = self._queue.popleft()

        try:
          if action_name == "start_video":
            result = await self._start_video(*args)
          elif action_name == "stop_video":
            result = await self._stop_video(*args)
          elif action_name == "take_photo":
            result = await self._take_photo(*args)
          elif action_name == "take_video":
            result = await self._take_video(*args)
          else:
            raise ValueError(f"Unknown action: {action_name}")

          future.set_result(result)
        except Exception as e:
          future.set_exception(e)

    except asyncio.CancelledError:
      self._queue.clear()
      pass

  async def _start_video(self, mode: VideoMode, params: VideoParams):
    if self._video_process:
      return
    # self._last_video_params = params

    script_path = self._videoreg.app_path("task/camera/start_video.sh")
    h264_dir = self._videoreg.h264_path()
    photo_dir = self._videoreg.jpeg_path()

    cmd = [
      "bash",
      str(script_path),
      "--h264-dir",
      str(h264_dir),
      "--screenshots-dir",
      str(photo_dir),
      "--mode",
      str(mode.value),
      "--post-process-file",
      str(self._videoreg.app_path("task/camera/rpicam-post.json")),
      "--camera-mode",
      params.camera_mode_str,
      "--width",
      str(params.width),
      "--height",
      str(params.height),
      "--fps",
      str(params.fps),
      "--bitrate",
      str(params.bitrate),
    ]
    if params.hflip:
      cmd.append("--hflip")
    if params.vflip:
      cmd.append("--vflip")
    if mode == VideoMode.TO_STREAM:
      if params.hls_dir:
        cmd.extend(["--hls-dir", params.hls_dir])
    elif params.screenshot:
      cmd.extend(["--screenshot", str(photo_dir) + "/%V.jpg"])

    process: Process = await asyncio.create_subprocess_exec(
      *cmd,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
    )

    asyncio.create_task(_read_stream(process.stdout, lambda s: self._logger.debug(f"STDOUT: {s}")))
    asyncio.create_task(_read_stream(process.stderr, lambda s: self._logger.debug(f"STDERR: {s}")))

    self._logger.info(f"Video process started {process.pid}")

    self._video_process = process

  async def _stop_video(self):
    if not self._video_process:
      return

    if self._video_process.returncode is not None:
      self._video_process = None
      return

    try:
      # os.killpg(os.getpgid(process.pid), signal.SIGTERM)
      os.kill(self._video_process.pid, signal.SIGTERM)
      await asyncio.wait_for(self._video_process.wait(), timeout=5)
      self._logger.info("Video process stopped")

    except TimeoutError:
      self._logger.warning("Video process kill SIGTERM timeout. Try SIGKILL")
      # os.killpg(os.getpgid(process.pid), signal.SIGKILL)
      os.kill(self._video_process.pid, signal.SIGKILL)
      await asyncio.wait_for(self._video_process.wait(), timeout=5)

    except:
      self._logger.error("Video process kill error")

    finally:
      self._video_process = None

  async def _take_photo(
    self, path: str, is_screenshot: bool, is_night: bool, hflip: bool = False, vflip: bool = False
  ):
    if self._video_process:
      return

    if is_screenshot:
      await self._take_photo_screenshot(path)
    else:
      await self._take_photo_raw(path, is_night, hflip, vflip)

  async def _take_photo_screenshot(self, path: str):
    await stream_subprocess(
      cmd=["bash", str(self._videoreg.app_path("task/camera/take_screenshot.sh")), f"-s {path}"],
      start_cb=lambda pid, cmd: self._logger.debug(f"CMD (pid={pid}): {cmd}"),
      stdout_cb=lambda pid, s: self._logger.debug(f"STDOUT (pid={pid}): {s}"),
      stderr_cb=lambda pid, s: self._logger.debug(f"STDERR (pid={pid}): {s}"),
    )

  async def _take_photo_raw(
    self, path: str, is_night: bool, hflip: bool = False, vflip: bool = False
  ):
    try:
      cmd = [
        "bash",
        str(self._videoreg.app_path("task/camera/take_photo.sh")),
        "--screenshot",
        path,
        "--night",
        "1" if is_night else "0",
        "--post-process-file",
        str(self._videoreg.app_path("task/camera/rpicam-post.json")),
      ]
      if hflip:
        cmd.append("--hflip")
      if vflip:
        cmd.append("--vflip")
      photo_coroutine = stream_subprocess(
        cmd=cmd,
        start_cb=lambda pid, cmd: self._logger.info(f"CMD (pid={pid}): {cmd}"),
        stdout_cb=lambda pid, s: self._logger.info(f"STDOUT (pid={pid}): {s}"),
        stderr_cb=lambda pid, s: self._logger.info(f"STDERR (pid={pid}): {s}"),
      )

      await asyncio.wait_for(photo_coroutine, timeout=60 if is_night else 10)

    except TimeoutError:
      self._logger.warning("take photo timeout error")
      pass

  async def _take_video(self, filename: str, params: VideoParams = None):
    if self._video_process:
      return

    script_path = self._videoreg.app_path("task/camera/start_video.sh")
    h264_dir = self._videoreg.h264_path()
    photo_dir = self._videoreg.jpeg_path()

    h264_path = self._videoreg.h264_path(f"{filename}.h264")
    screenshot_path = self._videoreg.jpeg_path(f"{filename}.jpg")

    cmd = [
      "bash",
      str(script_path),
      "--path",
      str(h264_path),
      "--h264-dir",
      str(h264_dir),  # no need
      "--screenshots-dir",
      str(photo_dir),  # no need
      "--mode",
      VideoMode.TO_FILE.value,
      "--post-process-file",
      str(self._videoreg.app_path("task/camera/rpicam-post.json")),
      "--camera-mode",
      params.camera_mode_str,
      "--width",
      str(params.width),
      "--height",
      str(params.height),
      "--fps",
      str(params.fps),
      "--bitrate",
      str(params.bitrate),
      "--duration",
      str(params.duration),
    ]
    if params.hflip:
      cmd.append("--hflip")
    if params.vflip:
      cmd.append("--vflip")
    if params.screenshot:
      cmd.extend(["--screenshot", str(screenshot_path)])

    video_coroutine = stream_subprocess(
      cmd=cmd,
      start_cb=lambda pid, cmd: self._logger.info(f"CMD (pid={pid}): {cmd}"),
      stdout_cb=lambda pid, s: self._logger.info(f"STDOUT (pid={pid}): {s}"),
      stderr_cb=lambda pid, s: self._logger.info(f"STDERR (pid={pid}): {s}"),
    )

    await asyncio.wait_for(video_coroutine, timeout=(params.duration + 20))


async def _read_stream(stream, callback):
  async for line in stream:
    if isinstance(line, bytes):
      line = line.decode("utf-8", errors="replace")
    callback(line.rstrip("\n\r"))
