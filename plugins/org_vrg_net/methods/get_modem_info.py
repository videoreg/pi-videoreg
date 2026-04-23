from logging import Logger

from plugins.org_vrg_net.modem_controls import ModemControls
from sdk.socket.api import ApiMethod


class MethodGetModemInfo(ApiMethod):
  _logger: Logger
  _modem_controls: ModemControls

  def __init__(self, logger: Logger, modem_controls: ModemControls):
    super().__init__()
    self._logger = logger
    self._modem_controls = modem_controls

  async def exec(self, args):
    """Gets modem information via mmcli"""

    try:
      result = await self._modem_controls.get_modem_info()

      return {"status": "ok", "data": result}

    except Exception as e:
      self._logger.error(f"Error getting modem info: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
