from plugins.org_vrg_modem.plugin import ModemPlugin
from sdk.socket.api import ApiMethod


class MethodIsReadyToDie(ApiMethod):
  _plugin: ModemPlugin
  _wait_first_sms_limit = 10

  def __init__(self, plugin: ModemPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):

    assumptions = []

    waiting_first_sms_time = self._plugin.get_waiting_first_sms_time()

    if waiting_first_sms_time > 0 and waiting_first_sms_time <= self._wait_first_sms_limit:
      return {
        "status": "ok",
        "ready": False,
        "why": f"waiting SMS: {waiting_first_sms_time}s (limit {self._wait_first_sms_limit}s)",
      }
    elif waiting_first_sms_time > self._wait_first_sms_limit:
      assumptions.append(
        f"waiting SMS over limit: {waiting_first_sms_time}s (limit {self._wait_first_sms_limit}s)"
      )

    return {"status": "ok", "ready": True, "assumptions": assumptions}
