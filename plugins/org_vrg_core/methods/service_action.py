import asyncio

from plugins.org_vrg_core.plugin import CorePlugin
from sdk.socket.api import ApiMethod

ALLOWED_ACTIONS = {"start", "stop", "restart"}


class MethodServiceAction(ApiMethod):
  _plugin: CorePlugin

  def __init__(self, plugin: CorePlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      service_name = args.get("service")
      action = args.get("action")

      if not service_name or not action:
        return {"status": "error", "error": "Missing fields: service, action"}

      if action not in ALLOWED_ACTIONS:
        return {"status": "error", "error": f"Invalid action: {action}"}

      proc = await asyncio.create_subprocess_exec(
        "systemctl",
        action,
        f"{service_name}.service",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
      )
      stdout, stderr = await proc.communicate()

      if proc.returncode != 0:
        error_msg = stderr.decode().strip() or stdout.decode().strip()
        return {"status": "error", "error": error_msg}

      return {"status": "ok", "data": {}}
    except Exception as e:
      self._plugin.logger.error(f"Error in service_action: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
