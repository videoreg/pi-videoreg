import plugins.org_vrg_stat.functions as functions
from sdk.interface import Interface, InterfaceCommand


class CommandGetTemp(InterfaceCommand):
  def __init__(self):
    super().__init__()

  async def exec(self, interface: Interface, payload, args):
    await interface.send_text(payload=payload, text=functions.get_cpu_temp())
