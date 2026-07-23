from plugins.org_vrg_core.methods.datetime_state import has_timedatectl, read_datetime_state
from plugins.org_vrg_core.plugin import CorePlugin
from sdk.helper import return_subprocess
from sdk.socket.api import ApiMethod


class MethodSetNtp(ApiMethod):
  """Enable or disable automatic time synchronization (NTP).

  Accepts ``{"enabled": bool}``.
  """

  _plugin: CorePlugin

  def __init__(self, plugin: CorePlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      if not isinstance(args, dict) or "enabled" not in args:
        return {"status": "error", "error": "Missing field: enabled"}

      if not has_timedatectl():
        return {"status": "error", "error": "timedatectl is not available on this system"}

      enabled = "true" if args.get("enabled") else "false"
      result = await return_subprocess(["sudo", "timedatectl", "set-ntp", enabled])
      if result.returncode != 0:
        return {"status": "error", "error": (result.stderr.strip() or result.stdout.strip())}

      return {"status": "ok", "data": await read_datetime_state()}
    except Exception as e:
      self._plugin.logger.error(f"Error in set_ntp: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
