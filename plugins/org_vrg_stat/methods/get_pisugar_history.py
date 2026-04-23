import os

from plugins.org_vrg_stat.dirs import Dirs
from sdk.socket.api import ApiMethod


class MethodGetPisugarHistory(ApiMethod):
  def __init__(self, dirs: Dirs):
    super().__init__()
    self._dirs = dirs

  async def exec(self, args):
    dir_path = str(self._dirs.pisugar)
    if not os.path.exists(dir_path):
      return {"status": "ok", "data": {"files": []}}
    files = sorted(
      os.path.join(dir_path, f)
      for f in os.listdir(dir_path)
      if os.path.isfile(os.path.join(dir_path, f))
    )
    return {"status": "ok", "data": {"files": files}}
