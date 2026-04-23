from pathlib import Path

from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.helper import stream_subprocess


async def convert_h264_to_mp4(plugin: CameraPlugin, h264_file_path: Path, mp4_file_path: Path):
  await stream_subprocess(
    cmd=["ffmpeg", "-i", h264_file_path, "-c:v", "copy", mp4_file_path],
    start_cb=lambda pid, cmd: plugin.logger.debug(f"CMD (pid={pid}): {cmd}"),
    stdout_cb=lambda pid, s: plugin.logger.debug(f"STDOUT (pid={pid}): {s}"),
    stderr_cb=lambda pid, s: plugin.logger.debug(f"STDERR (pid={pid}): {s}"),
  )
  plugin.logger.debug(f"mp4 convert finished: {h264_file_path}")
