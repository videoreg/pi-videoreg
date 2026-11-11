from plugins.org_vrg_rearcam import ble_provisioner
from plugins.org_vrg_rearcam.ble_provisioner import ProvisionError
from plugins.org_vrg_rearcam.plugin import RearcamPlugin
from sdk.socket.api import ApiMethod


class MethodProvision(ApiMethod):
  """Provision a rear camera over BLE: args {"mac": "AA:BB:..", "name": optional}.

  The WiFi credentials of the network the hub itself is on are taken from
  net.wifi_credentials, so the camera joins the same network (router or the
  hub's own AP). May take up to ~40 s (BLE handshake + WiFi connect).
  """

  _plugin: RearcamPlugin

  def __init__(self, plugin: RearcamPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    if not ble_provisioner.is_supported():
      return {"status": "error", "error": "bleak_not_available"}
    if not isinstance(args, dict) or not isinstance(args.get("mac"), str):
      return {"status": "error", "error": "mac_required"}
    name = args.get("name") if isinstance(args.get("name"), str) else ""
    try:
      device = await self._plugin.provision(args["mac"], name)
      return {"status": "ok", "data": {"device": device}}
    except ProvisionError as e:
      self._plugin.logger.warning(f"provisioning failed: {e}")
      return {"status": "error", "error": str(e)}
    except Exception as e:
      self._plugin.logger.error(f"Error in provision: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
