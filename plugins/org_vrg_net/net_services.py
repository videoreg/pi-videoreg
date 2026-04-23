from asyncio.subprocess import Process


class NetServicesManager:
  async def start(self) -> Process:
    raise NotImplementedError()

  async def stop(self) -> Process:
    raise NotImplementedError()

  async def status(self) -> bool:
    raise NotImplementedError()
