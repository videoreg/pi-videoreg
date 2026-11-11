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
    async with aiohttp.ClientSession(timeout=self._timeout) as session:
      async with session.get(f"{self._base}/photo") as resp:
        resp.raise_for_status()
        return await resp.read()
