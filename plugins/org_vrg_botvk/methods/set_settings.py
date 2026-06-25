from plugins.org_vrg_botvk.plugin import BotvkPlugin
from sdk.socket.api import ApiMethod


class MethodSetSettings(ApiMethod):
  _plugin: BotvkPlugin

  def __init__(self, plugin: BotvkPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    if not isinstance(args, dict):
      return {"status": "error", "error": "Arguments should be json"}

    patch = {}

    vk_bot_token = args.get("vk_bot_token")
    if vk_bot_token is not None:
      patch["vk_bot_token"] = str(vk_bot_token).strip()

    vk_group_id = args.get("vk_group_id")
    if vk_group_id is not None:
      patch["vk_group_id"] = str(vk_group_id).strip()

    if not patch:
      return {"status": "error", "error": "No fields to update"}

    self._plugin.state.save(patch)

    return {"status": "ok"}
