import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sdk.socket.client import EasyConnection


@dataclass
class JournalRecord:
  """A single business-event record written to the journal."""

  type: str
  data: Any

  @staticmethod
  def parse(raw: dict) -> "JournalRecord":
    if not isinstance(raw, dict) or "type" not in raw:
      raise ValueError(f"Invalid journal record format: {raw!r}")
    return JournalRecord(type=raw["type"], data=raw.get("data"))

  def to_dict(self) -> dict:
    return {"type": self.type, "data": self.data}


class JournalClient:
  """Sends JournalRecord instances to the journal channel over the event bus."""

  def __init__(self, plugin_id: str, easy_connection: EasyConnection):
    self._plugin_id = plugin_id
    self._easy_connection = easy_connection

  async def write(self, record: JournalRecord) -> bool:
    payload = record.to_dict()
    payload["from"] = self._plugin_id
    return await self._easy_connection.send_data("journal", payload, wait=5)


class JournalServer:
  """Receives journal records from the bus and appends them to daily log files."""

  def __init__(self, plugin_id: str, videoreg):
    self._plugin_id = plugin_id
    self._videoreg = videoreg

  def write(self, from_plugin_id: str, record: JournalRecord):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    iso_str = now.isoformat()

    journal_dir = self._videoreg.private_path(f"data/plugins/{self._plugin_id}/journal")
    journal_dir.mkdir(parents=True, exist_ok=True)

    journal_file = journal_dir / f"{date_str}.txt"
    data_str = json.dumps(record.data, ensure_ascii=False)
    line = f"{iso_str},{from_plugin_id},{record.type},{data_str}\n"

    with open(journal_file, "a", encoding="utf-8") as f:
      f.write(line)
