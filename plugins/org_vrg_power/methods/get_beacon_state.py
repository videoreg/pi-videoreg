from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.socket.api import ApiMethod


class MethodGetBeaconState(ApiMethod):
  """Beacon-derived recording gate for other services (the camera in particular).

  Returns whether the BLE beacon is currently blocking video recording — the feature
  is active and the beacon has not been confirmed present this session (or was lost
  past grace). The camera consults this each lifecycle loop so it does not treat
  external power as a reason to record on a parking wake-up when only the in-car
  beacon is missing; a wakeup photo is still taken and the power plugin shuts the
  device down shortly after.
  """

  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    return {
      "status": "ok",
      "data": {"recording_blocked": self._plugin.beacon_blocks_recording()},
    }
