from dataclasses import dataclass


@dataclass
class SMS:
  number: str
  text: str
  timestamp: str

  def __init__(self, number, text, timestamp):
    self.number = number
    self.text = text
    self.timestamp = timestamp

  def to_dict(self):
    return {"number": self.number, "text": self.text, "timestamp": self.timestamp}
