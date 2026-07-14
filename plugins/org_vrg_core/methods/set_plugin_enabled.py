from plugins.org_vrg_core.plugin import CorePlugin
from sdk.merged_manifest import set_plugin_enabled
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

      # The enabled flag is stored in the merged manifest under `.videoreg/`, never in
      # the repo's videoreg.manifest.yaml, so the working tree stays clean.
      found = set_plugin_enabled(self._plugin.runner.videoreg, plugin_id, bool(enabled))
      if not found:
        return {"status": "error", "error": f"Plugin not found: {plugin_id}"}

      return {"status": "ok", "data": {}}
    except Exception as e:
      self._plugin.logger.error(f"Error in set_plugin_enabled: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
