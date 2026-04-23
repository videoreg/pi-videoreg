from plugins.org_vrg_core.plugin import CorePlugin
from sdk.socket.api import ApiMethod


class MethodGetJournalFiles(ApiMethod):
  _plugin: CorePlugin

  def __init__(self, plugin: CorePlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      journal_dir = self._plugin.runner.videoreg.private_path(
        f"data/plugins/{self._plugin.id}/journal"
      )
      if not journal_dir.exists():
        return {"status": "ok", "data": {"files": []}}

      files = sorted(journal_dir.glob("*.txt"))
      recent = files[-2:] if len(files) >= 2 else files

      return {"status": "ok", "data": {"files": [str(f) for f in reversed(recent)]}}
    except Exception as e:
      self._plugin.logger.error(f"Error in get_journal_files: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
