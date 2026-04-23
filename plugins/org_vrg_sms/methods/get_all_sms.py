import json

from plugins.org_vrg_sms.plugin import SmsPlugin
from sdk.media_manager import MediaFileType
from sdk.socket.api import ApiMethod


class MethodGetAllSms(ApiMethod):
  """Returns a list of all incoming SMS messages"""

  _plugin: SmsPlugin

  def __init__(self, plugin: SmsPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    media_manager = self._plugin.runner.media_manager
    sms_dir = media_manager.get_dir(MediaFileType.SMS)
    messages = []

    try:
      files = sorted(
        [f for f in media_manager.get_files(MediaFileType.SMS) if f.endswith(".json")], reverse=True
      )

      for filename in files:
        file_path = sms_dir / filename
        try:
          with open(file_path) as f:
            data = json.load(f)
          messages.append(
            {
              "filename": filename.replace(".json", ""),
              "number": data.get("number", ""),
              "text": data.get("text", ""),
              "timestamp": data.get("timestamp", ""),
            }
          )
        except Exception:
          pass

      return {"status": "ok", "data": {"messages": messages}}
    except Exception as e:
      self._plugin.logger.error(f"Error in get_all_sms: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
