from logging import Logger

from plugins.org_vrg_net.modem_controls import ModemControls
from sdk.socket.api import ApiClient, ApiMethod


class MethodGetModemInfo(ApiMethod):
  _logger: Logger
  _modem_controls: ModemControls
  _api_client: ApiClient

  def __init__(self, logger: Logger, modem_controls: ModemControls, api_client: ApiClient):
    super().__init__()
    self._logger = logger
    self._modem_controls = modem_controls
    self._api_client = api_client

  async def exec(self, args):
    """Gets modem information.

    Primary source is ModemManager (mmcli). For modems ModemManager does not
    manage (e.g. the A7670 over RNDIS), mmcli reports nothing, so we fall back
    to reading the info directly over AT from the vrg-modem service, which owns
    the modem's serial port.
    """

    try:
      result = await self._modem_controls.get_modem_info()

      if result.get("connected"):
        return {"status": "ok", "data": result}

      # mmcli found no modem — try the AT-based fallback in the modem service.
      fallback = await self._get_modem_info_over_at()
      return {"status": "ok", "data": fallback or result}

    except Exception as e:
      self._logger.error(f"Error getting modem info: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}

  async def _get_modem_info_over_at(self) -> dict | None:
    try:
      response = await self._api_client.exec("modem.modem_info", {})
      if response.is_ok():
        return response.get_data()
      self._logger.warning(f"modem.modem_info error: {response.get_error()}")
    except Exception as e:
      self._logger.warning(f"modem.modem_info call failed: {e}")
    return None
