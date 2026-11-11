"""HTTP client for the rear-camera REST API (see the rear-camera-protocol spec)."""

import aiohttp

import plugins.org_vrg_rearcam.const as const


class CameraClient:
  """Talks to one rear camera over plain HTTP on the local network."""

  def __init__(self, ip: str, timeout: float = const.HTTP_TIMEOUT_SECONDS):
    self._base = f"http://{ip}"
    self._timeout = aiohttp.ClientTimeout(total=timeout)

  async def get_health(self) -> dict:
    async with aiohttp.ClientSession(timeout=self._timeout) as session:
      async with session.get(f"{self._base}/health") as resp:
        resp.raise_for_status()
        return await resp.json()

  async def get_status(self) -> dict:
    async with aiohttp.ClientSession(timeout=self._timeout) as session:
      async with session.get(f"{self._base}/status") as resp:
        resp.raise_for_status()
        return await resp.json()

  async def get_photo(self) -> bytes:
    timeout = aiohttp.ClientTimeout(total=const.PHOTO_TIMEOUT_SECONDS)
    async with aiohttp.ClientSession(timeout=timeout) as session:
      async with session.get(f"{self._base}/photo") as resp:
        resp.raise_for_status()
        return await resp.read()

  async def get_config(self) -> dict:
    """Camera frame config: {"frame": {width,height,fps}, "frames": [...]}."""
    async with aiohttp.ClientSession(timeout=self._timeout) as session:
      async with session.get(f"{self._base}/config") as resp:
        resp.raise_for_status()
        return await resp.json()

  async def set_config(self, width: int, height: int) -> dict:
    """Switch the frame size; returns the applied frame {width,height,fps}."""
    async with aiohttp.ClientSession(timeout=self._timeout) as session:
      async with session.post(
        f"{self._base}/config", json={"frame": {"width": width, "height": height}}
      ) as resp:
        if resp.status == 400:
          body = await resp.json(content_type=None)
          raise CameraConfigError(body.get("error") or "unsupported_frame")
        resp.raise_for_status()
        return await resp.json()


class CameraConfigError(Exception):
  """The camera rejected the requested frame (see the protocol error codes)."""
