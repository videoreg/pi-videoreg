import asyncio

from plugins.org_vrg_net.methods.get_connections import MethodGetConnections
from plugins.org_vrg_net.methods.get_modem_info import MethodGetModemInfo
from sdk.socket.api import ApiMethod


class MethodGetModemDashboard(ApiMethod):
  """Self-contained payload for the modem dashboard tile.

  The tile needs the modem info (model, operator, access tech, connected) plus
  the WWAN IP, which lives in the NetworkManager connection rather than in the
  modem info. Both are gathered here so a dashboard block maps to a single
  method (see the http.dashboard manifest convention).
  """

  _modem_info: MethodGetModemInfo
  _connections: MethodGetConnections

  def __init__(self, modem_info: MethodGetModemInfo, connections: MethodGetConnections):
    super().__init__()
    self._modem_info = modem_info
    self._connections = connections

  async def exec(self, args):
    info_res, conn_res = await asyncio.gather(
      self._modem_info.exec({}),
      self._connections.exec({}),
      return_exceptions=True,
    )

    data: dict = {}
    if isinstance(info_res, dict) and info_res.get("status") == "ok":
      data = dict(info_res.get("data") or {})

    ip = None
    if isinstance(conn_res, dict) and conn_res.get("status") == "ok":
      modem_conn = (conn_res.get("data") or {}).get("modem") or {}
      ip = modem_conn.get("ip")
    data["ip"] = ip

    return {"status": "ok", "data": data}
