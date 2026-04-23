from sdk.socket.api import ApiMethod


class MethodGetCommands(ApiMethod):
  def __init__(self):
    super().__init__()

  async def exec(self, args):
    return {
      "status": "ok",
      "bot_message": "Stat commands",
      "bot_buttons": [
        [{"text": "Get temperature", "callback_data": "button_plugin__stat.get_temp"}],
      ],
    }
