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
      plugins_by_id = {p["id"]: p for p in manifest.plugins}

      service_names = [s.get("name") for s in services]
      statuses = await asyncio.gather(*[self._get_service_status(s) for s in service_names])

      result_services = []
      for service_entry, status in zip(services, statuses):
        service_plugins = []
        for plugin_id in service_entry.get("plugins", []) or []:
          p = plugins_by_id.get(plugin_id)
          if p is None:
            continue
          service_plugins.append(
            {"id": p["id"], "name": p.get("name", ""), "enabled": p.get("enabled", True)}
          )
        result_services.append(
          {"name": service_entry.get("name"), "status": status, "plugins": service_plugins}
        )

      return {"status": "ok", "data": {"services": result_services}}
    except Exception as e:
      self._plugin.logger.error(f"Error in get_system: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
