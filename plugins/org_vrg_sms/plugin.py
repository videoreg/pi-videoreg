import asyncio
import json
import time
from datetime import datetime

from plugins.org_vrg_sms.sms_manager import SmsManager
from sdk.media_manager import MediaFileType
from sdk.service import Plugin


class SmsPlugin(Plugin):
  sms_manager: SmsManager = None
  _start_check_sms_time = -1.0
  _received_sms = False
  _command_plugin_map: dict[str, str]
  _allowed_phones: list[str]

  def __init__(self, id, name, runner):
    super().__init__(id, name, runner)
    self._command_plugin_map = {}
    self._allowed_phones = []

  def init_sms_manager(self, sms_manager: SmsManager):
    self.sms_manager = sms_manager

  async def start(self):
    await super().start()
    asyncio.create_task(self._start_check_sms_loop())

  def init_command_plugin_map(self, command_plugin_map: dict[str, str]):
    self._command_plugin_map = command_plugin_map

  def init_allowed_phones(self, phones: list[str]):
    self._allowed_phones = phones

  def get_waiting_first_sms_time(self) -> int:
    """
    :return: "-1" if sms already readed or function not suppoted at all
    :rtype: int
    """
    if self._received_sms:
      return -1

    if self._start_check_sms_time < 0:
      return -1

    return int(time.time() - self._start_check_sms_time)

  async def _start_check_sms_loop(self):
    self._start_check_sms_time = time.time()

    await asyncio.sleep(1)

    while self.runner.is_running():
      try:
        sms_list = await self.sms_manager.read_and_delete_sms()
        commands_to_exec: list[tuple[str, str, str]] = []

        while len(sms_list):
          sms = sms_list.pop()

          self.logger.debug(f"{sms.to_dict()}")

          sms_datetime = datetime.fromisoformat(sms.timestamp)
          sms_datetime_str_for_file = sms_datetime.strftime("%Y-%m-%d_%H-%M-%S")
          sms_datetime_str_for_bot = sms_datetime.strftime("%Y-%m-%d %H:%M:%S")

          sms_file_name = f"{sms_datetime_str_for_file}_{sms.number}.json".replace("+", "")
          sms_file_path = self.runner.videoreg.sms_path(sms_file_name)

          with open(sms_file_path, "w") as f:
            json.dump(sms.to_dict(), f, indent=2)
          self.runner.media_manager.invalidate(MediaFileType.SMS)

          if sms.text.startswith("/") and len(sms.text) > 1:
            if sms.number not in self._allowed_phones:
              self.logger.warning(f"command from not allowed number: {sms.number}")
            else:
              inputs = sms.text.split(" ", 1)
              command_name = inputs[0][1:]
              command_args = inputs[1] if len(inputs) > 1 else None

              self.logger.info(f"detected command: name={command_name}, args={command_args}")

              commands_to_exec.append((sms.number, command_name, command_args))
          else:
            bot_response = await self.api_client.exec(
              "bot.send_text",
              {
                "payload": None,
                "text": f"SMS\n\n{sms_datetime_str_for_bot}\n\nFrom: {sms.number}\n\n{sms.text}\n",
              },
            )
            if not bot_response.is_ok():
              self.logger.warning(f"bot.send_text error: {bot_response.get_error()}")

        for sms_number, command_name, command_args in commands_to_exec:
          asyncio.create_task(self._handle_command(sms_number, command_name, command_args))

        self._received_sms = True

      except Exception as e:
        self.logger.error(f"error: {e}")

      await asyncio.sleep(10)

  async def _handle_command(self, sms_number: str, name: str, args: str):
    plugin_name = self._command_plugin_map.get(name)
    if not plugin_name:
      self.logger.warning(f"Unknown command: {name}")
      return
    try:
      await self.api_client.exec(
        f"{plugin_name}.command",
        {
          "command": name,
          "interface": "sms",
          "payload": {"phone": sms_number},
          "args": args,
        },
      )
    except Exception as e:
      self.logger.error(f"_handle_command error: {e}")
