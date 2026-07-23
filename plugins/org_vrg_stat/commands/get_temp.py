import plugins.org_vrg_stat.functions as functions
from sdk.gateway import Gateway, GatewayCommand


class CommandGetTemp(GatewayCommand):
  def __init__(self):
    super().__init__()

  async def exec(self, gateway: Gateway, payload, args):
    await gateway.send_text(payload=payload, text=functions.get_cpu_temp())
