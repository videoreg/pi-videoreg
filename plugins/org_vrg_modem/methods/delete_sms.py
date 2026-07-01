import os

from plugins.org_vrg_modem.plugin import ModemPlugin
from sdk.media_manager import MediaFileType
from sdk.socket.api import ApiMethod


class MethodDeleteSms(ApiMethod):
  """Deletes an incoming SMS message by filename (moved from the http handler)."""

  _plugin: ModemPlugin

  def __init__(self, plugin: ModemPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    filename = args.get("filename", "") if isinstance(args, dict) else ""

    if not filename or "/" in filename or "\\" in filename or ".." in filename:
      return {"status": "error", "error": "Invalid filename"}

    try:
      file_path = self._plugin.runner.videoreg.sms_path(f"{filename}.json")
      if not file_path.exists():
        return {"status": "error", "error": "Not found"}

      os.remove(file_path)
      self._plugin.runner.media_manager.invalidate(MediaFileType.SMS)
      return {"status": "ok", "data": {}}

    except Exception as e:
      self._plugin.logger.error(f"Error in delete_sms: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
