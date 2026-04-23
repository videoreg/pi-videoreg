from plugins.org_vrg_net.modem_controls import ModemControls


class ModemControlsImpl(ModemControls):
  async def get_modem_info(self) -> dict:
    return {"connected": False}
