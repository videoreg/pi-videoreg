import yaml

from plugins.org_vrg_core.plugin import CorePlugin
from sdk.socket.api import ApiMethod


class MethodSetPluginEnabled(ApiMethod):
  _plugin: CorePlugin

  def __init__(self, plugin: CorePlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      plugin_id = args.get("id")
      enabled = args.get("enabled")

      if not plugin_id or enabled is None:
        return {"status": "error", "error": "Missing fields: id, enabled"}

      manifest_path = self._plugin.runner.videoreg.app_path("videoreg.manifest.yaml")
      with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

      found = False
      for plugin in manifest.get("plugins", []):
        if plugin.get("id") == plugin_id:
          plugin["enabled"] = bool(enabled)
          found = True
          break

      if not found:
        return {"status": "error", "error": f"Plugin not found: {plugin_id}"}

      with open(manifest_path, "w") as f:
        yaml.dump(manifest, f, allow_unicode=True, default_flow_style=False)

      return {"status": "ok", "data": {}}
    except Exception as e:
      self._plugin.logger.error(f"Error in set_plugin_enabled: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
