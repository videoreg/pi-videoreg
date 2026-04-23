import time
from collections.abc import Generator
from contextlib import contextmanager


class KeepAlive:
  """Tracks named reasons that should delay system shutdown, each with an expiry timestamp."""

  _alive: dict[str, int]

  def __init__(self):
    self._alive = {}

  def have_to_wait(self, reason, sec):
    self._alive[reason] = time.time() + sec

  def no_more_need_to_wait(self, reason):
    if reason in self._alive:
      del self._alive[reason]

  @contextmanager
  def wait_until_done(self, reason: str, timeout: int) -> Generator[None, None, None]:
    self.have_to_wait(reason, timeout)
    try:
      yield
    finally:
      self.no_more_need_to_wait(reason)

  def get_alive_reasons(self) -> dict[str, int]:
    if not self._alive:
      return self._alive

    cur_time = time.time()

    actual_alive: dict[str, int] = {}

    for reason, target_time in self._alive.items():
      if target_time > cur_time:
        actual_alive[reason] = target_time

    self._alive = actual_alive

    return actual_alive
