from plugins.org_vrg_rearcam import ble_provisioner
from plugins.org_vrg_rearcam.plugin import RearcamPlugin
from sdk.socket.api import ApiMethod


class MethodScanBle(ApiMethod):
  """One-shot BLE scan for unprovisioned rear cameras (~8 s)."""

  _plugin: RearcamPlugin

  def __init__(self, plugin: RearcamPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    if not ble_provisioner.is_supported():
      return {"status": "error", "error": "bleak_not_available"}
    try:
      devices = await self._plugin.scan_ble()
      return {"status": "ok", "data": {"devices": devices}}
    except Exception as e:
      self._plugin.logger.error(f"Error in scan_ble: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
