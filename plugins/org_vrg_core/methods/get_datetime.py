from plugins.org_vrg_core.methods.datetime_state import read_datetime_state
from plugins.org_vrg_core.plugin import CorePlugin
from sdk.socket.api import ApiMethod


class MethodGetDatetime(ApiMethod):
  _plugin: CorePlugin

  def __init__(self, plugin: CorePlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      return {"status": "ok", "data": await read_datetime_state()}
    except Exception as e:
      self._plugin.logger.error(f"Error in get_datetime: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
