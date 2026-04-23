from plugins.org_vrg_sms.plugin import SmsPlugin
from sdk.socket.api import ApiMethod


class MethodSendText(ApiMethod):
  _plugin: SmsPlugin

  def __init__(self, plugin: SmsPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    if not isinstance(args, dict):
      return {"status": "error", "error": "Arguments should be json"}

    payload = args.get("payload", {})
    phone = payload.get("phone") if isinstance(payload, dict) else None
    text = args.get("text")

    if not phone:
      return {"status": "error", "error": "Missing phone in payload"}

    if not text:
      return {"status": "error", "error": "Missing text"}

    await self._plugin.sms_manager.send_sms(phone, text)

    return {"status": "ok"}
