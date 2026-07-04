import time


class BotHealth:
  """Tracks whether a gateway bot is successfully exchanging data with its server.

  A successful poll response — even an empty one — proves the bot reaches the
  remote server (Telegram getUpdates, VK Long Poll, ...). The dispatcher marks
  each poll as ok/error; the plugin's `get_status` api-method reads this state to
  expose a health indicator to the UI, independent of user interaction.
  """

  # No successful poll within this window => considered unhealthy.
  STALE_SEC = 60

  polling: bool
  last_ok_at: "float | None"
  last_error_at: "float | None"
  last_error: "str | None"

  def __init__(self):
    self.polling = False
    self.last_ok_at = None
    self.last_error_at = None
    self.last_error = None

  def mark_polling(self, value: bool) -> None:
    self.polling = value

  def mark_ok(self) -> None:
    self.last_ok_at = time.time()
    self.last_error = None
    self.last_error_at = None

  def mark_error(self, message: str) -> None:
    self.last_error_at = time.time()
    self.last_error = message

  def is_healthy(self) -> bool:
    if not self.polling or self.last_ok_at is None:
      return False
    return (time.time() - self.last_ok_at) < self.STALE_SEC
