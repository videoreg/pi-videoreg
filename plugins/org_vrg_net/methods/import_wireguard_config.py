from plugins.org_vrg_net.plugin import NetPlugin
from plugins.org_vrg_net.wg_config import parse_config
from sdk.socket.api import ApiMethod


class MethodImportWireguardConfig(ApiMethod):
  """Parses a pasted wg-quick config (e.g. from a VPN server panel) into form settings.

  Saves nothing: the client fills the form with the result and the user saves it.
  Args: {"content": str}
  Data: {"settings": {...}, "public_key": str | None, "ignored": [<unsupported lines>]}
  """

  _plugin: NetPlugin

  def __init__(self, plugin: NetPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    content = args.get("content", "") if isinstance(args, dict) else ""
    if not content.strip():
      return {"status": "error", "error": "Configuration content is required"}

    try:
      settings, ignored = parse_config(content)
      private_key = settings["private_key"]
      public_key = None
      if private_key:
        public_key = await self._plugin.wg_monitor.get_public_key(private_key)

      return {
        "status": "ok",
        "data": {"settings": settings, "public_key": public_key, "ignored": ignored},
      }
    except Exception as e:
      self._plugin.logger.error(f"Error in import_wireguard_config: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}
