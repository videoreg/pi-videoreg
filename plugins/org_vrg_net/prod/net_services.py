import logging
from asyncio.subprocess import Process

from plugins.org_vrg_net.net_services import NetServicesManager
from sdk.helper import stream_subprocess

TARGET = "vrg-network.target"


class NetServicesManagerImpl(NetServicesManager):
  def __init__(self, logger: logging.Logger):
    self._logger = logger

  async def start(self) -> Process:
    return await stream_subprocess(
      cmd=["sudo", "systemctl", "start", TARGET],
      start_cb=lambda pid, cmd: self._logger.debug(f"CMD (pid={pid}): {cmd}"),
      stdout_cb=lambda pid, s: self._logger.debug(f"STDOUT (pid={pid}): {s}"),
      stderr_cb=lambda pid, s: self._logger.debug(f"STDERR (pid={pid}): {s}"),
    )

  async def stop(self) -> Process:
    return await stream_subprocess(
      cmd=["sudo", "systemctl", "stop", TARGET],
      start_cb=lambda pid, cmd: self._logger.debug(f"CMD (pid={pid}): {cmd}"),
      stdout_cb=lambda pid, s: self._logger.debug(f"STDOUT (pid={pid}): {s}"),
      stderr_cb=lambda pid, s: self._logger.debug(f"STDERR (pid={pid}): {s}"),
    )

  async def status(self) -> bool:
    process = await stream_subprocess(
      cmd=["systemctl", "is-active", TARGET],
      start_cb=lambda pid, cmd: self._logger.debug(f"CMD (pid={pid}): {cmd}"),
      stdout_cb=lambda pid, s: self._logger.debug(f"STDOUT (pid={pid}): {s}"),
      stderr_cb=lambda pid, s: self._logger.debug(f"STDERR (pid={pid}): {s}"),
    )
    return process.returncode == 0
