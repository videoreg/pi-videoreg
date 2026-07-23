import plugins.org_vrg_stat.functions as functions
from sdk.socket.api import ApiMethod


class MethodGetCurrentTemp(ApiMethod):
  async def exec(self, args):
    try:
      return {"status": "ok", "data": {"cpu_temp": functions.get_cpu_temp()}}
    except Exception:
      return {"status": "ok", "data": {"cpu_temp": None}}
