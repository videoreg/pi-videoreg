from sdk.gateway import Gateway, GatewayCommand


class CommandGetCommands(GatewayCommand):
  def __init__(self):
    super().__init__()

  async def exec(self, gateway: Gateway, payload, args):
    await gateway.send_text(
      payload=payload,
      text="Stat commands",
      keyboard=[
        [{"text": "Get temperature", "callback_data": "command__stat__temp"}],
      ],
    )
