import os

from plugins.org_vrg_stat.dirs import Dirs
from plugins.org_vrg_stat.stat_files import list_stat_files, parse_stat_file
from sdk.socket.api import ApiMethod


class MethodGetPisugarHistory(ApiMethod):
  def __init__(self, dirs: Dirs):
    super().__init__()
    self._dirs = dirs

  async def exec(self, args):
    requested_date = args.get("date") if isinstance(args, dict) else None
    files = list_stat_files(str(self._dirs.pisugar))
    if not files:
      return {"status": "ok", "data": {"data": [], "date": None, "available_dates": []}}

    available_dates = sorted(os.path.splitext(os.path.basename(f))[0] for f in files)

    if requested_date:
      file_by_date = {os.path.splitext(os.path.basename(f))[0]: f for f in files}
      selected_file = file_by_date.get(requested_date, files[-1])
    else:
      selected_file = files[-1]

    data, date = parse_stat_file(selected_file)
    return {
      "status": "ok",
      "data": {"data": data, "date": date, "available_dates": available_dates},
    }
