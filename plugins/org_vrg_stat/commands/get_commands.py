from sdk.interface import Interface, InterfaceCommand


class CommandGetCommands(InterfaceCommand):
  def __init__(self):
    super().__init__()

  async def exec(self, interface: Interface, payload, args):
    await interface.send_text(
      payload=payload,
      text="Stat commands",
      keyboard=[
        [{"text": "Get temperature", "callback_data": "command__stat__temp"}],
      ],
    )
