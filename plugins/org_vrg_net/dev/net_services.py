from asyncio.subprocess import Process

from plugins.org_vrg_net.net_services import NetServicesManager


class NetServicesManagerImpl(NetServicesManager):
  async def start(self) -> Process:
    pass

  async def stop(self) -> Process:
    pass

  async def status(self) -> bool:
    return False
