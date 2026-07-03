from plugins.org_vrg_core.plugin import CorePlugin
from sdk.socket.api import ApiMethod


class MethodMarkDatetimeConfigured(ApiMethod):
  """Mark the one-time, system-wide first-run clock setup as completed.

  Persisted in the core plugin state so the onboarding step is shown only once
  for the whole system, regardless of which user logs in.
  """

  _plugin: CorePlugin

  def __init__(self, plugin: CorePlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      self._plugin.state.save({"datetime_configured": True})
      return {"status": "ok", "data": {"configured": True}}
    except Exception as e:
      self._plugin.logger.error(f"Error in mark_datetime_configured: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
