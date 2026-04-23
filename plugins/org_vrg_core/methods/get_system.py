import asyncio

from plugins.org_vrg_core.plugin import CorePlugin
from sdk.socket.api import ApiMethod


class MethodGetSystem(ApiMethod):
  _plugin: CorePlugin

  def __init__(self, plugin: CorePlugin):
    super().__init__()
    self._plugin = plugin

  async def _get_service_status(self, service_name: str) -> str:
    try:
      proc = await asyncio.create_subprocess_exec(
        "systemctl",
        "is-active",
        f"{service_name}.service",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
      )
      stdout, _ = await proc.communicate()
      return stdout.decode().strip()
    except Exception as e:
      self._plugin.logger.error(f"Error getting service status for {service_name}: {e}")
      return "unknown"

  async def exec(self, args):
    try:
      manifest = self._plugin.runner.videoreg.manifest
      services = manifest.services
      plugins = manifest.plugins

      statuses = await asyncio.gather(*[self._get_service_status(s) for s in services])

      result_services = []
      for service_name, status in zip(services, statuses):
        service_plugins = [
          {"id": p["id"], "name": p.get("name", ""), "enabled": p.get("enabled", True)}
          for p in plugins
          if p.get("service") == service_name
        ]
        result_services.append({"name": service_name, "status": status, "plugins": service_plugins})

      return {"status": "ok", "data": {"services": result_services}}
    except Exception as e:
      self._plugin.logger.error(f"Error in get_system: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
