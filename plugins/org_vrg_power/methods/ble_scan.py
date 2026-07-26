from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.socket.api import ApiMethod


class MethodBleScan(ApiMethod):
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    m = self._plugin.ble_monitor
    if not m or not m.is_supported():
      return {"status": "error", "error": "bleak_not_available"}
    try:
      devices = await m.scan()
    except Exception as e:
      self._plugin.logger.error(f"ble scan failed: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
    return {"status": "ok", "data": {"devices": devices}}
