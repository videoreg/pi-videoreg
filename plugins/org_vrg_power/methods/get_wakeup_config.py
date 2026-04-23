import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.socket.api import ApiMethod


class MethodGetWakeupConfig(ApiMethod):
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin):
    super().__init__()
    self._plugin = plugin

  WAKEUP_OPTIONS = [
    {"value": "1m", "label": "After 1 minute"},
    {"value": "2m", "label": "After 2 minutes"},
    {"value": "10m", "label": "After 10 minutes"},
    {"value": "30m", "label": "After 30 minutes"},
    {"value": "1h", "label": "After 1 hour"},
    {"value": "on-power-restore", "label": "On power restore"},
    {"value": "disabled", "label": "Disabled"},
  ]

  async def exec(self, args):
    wakeup_value = self._plugin.state.get(const.STATE_KEY_WAKEUP, None)
    return {
      "status": "ok",
      "data": {
        "current": wakeup_value,
        "options": self.WAKEUP_OPTIONS,
      },
    }
