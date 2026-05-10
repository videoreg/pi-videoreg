import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.plugin import PowerPlugin
from sdk.interface import Interface, InterfaceCommand


class CommandGetWakeupCommands(InterfaceCommand):
  _plugin: PowerPlugin

  def __init__(self, plugin: PowerPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, interface: Interface, payload, args):
    wakeup_value = self._plugin.state.get(const.STATE_KEY_WAKEUP, None)
    wakeup_message = wakeup_value if wakeup_value else "disabled"
    await interface.send_text(
      payload=payload,
      text=f"Current setting: {wakeup_message}\n\nThis function is supported only by PiSugar 3",
      keyboard=[
        [{"text": "Afrer 1 minute", "callback_data": "command__power__set_wakeup__1m"}],
        [{"text": "Afrer 2 minutes", "callback_data": "command__power__set_wakeup__2m"}],
        [{"text": "After 10 minutes", "callback_data": "command__power__set_wakeup__10m"}],
        [{"text": "After 30 minutes", "callback_data": "command__power__set_wakeup__30m"}],
        [{"text": "After 1 hour", "callback_data": "command__power__set_wakeup__1h"}],
        [
          {
            "text": "On power restore",
            "callback_data": "command__power__set_wakeup__on-power-restore",
          }
        ],
        [{"text": "Disable", "callback_data": "command__power__set_wakeup__disabled"}],
      ],
    )
