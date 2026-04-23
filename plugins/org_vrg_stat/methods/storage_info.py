import plugins.org_vrg_stat.functions as functions
from sdk.socket.api import ApiMethod


class MethodStorageInfo(ApiMethod):
  def __init__(self):
    super().__init__()

  async def exec(self, args):
    try:
      partitions = await functions.get_disk_partitions()
      return {"status": "ok", "data": {"partitions": partitions}}
    except Exception as e:
      return {"status": "error", "error": str(e)}
