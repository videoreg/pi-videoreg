class Backoff:
  def next_delay(self) -> float:
    raise Exception("Not implemented")

  def get_http_timeout(self) -> int:
    raise Exception("Not implemented")

  def get_wait_timeout(self) -> int:
    raise Exception("Not implemented")

  def get_current_delay(self) -> float:
    raise Exception("Not implemented")

  def get_current_counter(self) -> int:
    return 0

  def reset(self):
    pass

  def consider_user_interaction(self, has_interaction: bool):
    pass

  def consider_connection_error(self):
    pass

  def consider_timeout(self):
    pass


class NormalBackoff(Backoff):
  min_delay = 2.0
  max_delay = 15.0
  factor = 1.3

  short_timeout = 5
  normal_timeout = 30

  def __init__(self):
    self._current_delay = 0.0
    self._next_delay = self.min_delay
    self._counter = 0

  def next_delay(self) -> float:
    self._current_delay = self._next_delay
    self._next_delay = self._calculate_next_delay(self._next_delay)
    self._counter += 1
    return self._current_delay

  def get_http_timeout(self) -> int:
    return self.short_timeout if self._counter == 0 else self.normal_timeout

  def get_wait_timeout(self) -> int:
    # VK Long Poll `wait` parameter (server-side hold time, seconds)
    return (self.short_timeout if self._counter == 0 else self.normal_timeout) - 5

  def _calculate_next_delay(self, value: float) -> float:
    return min(value * self.factor, self.max_delay)

  def get_current_delay(self) -> float:
    return self._current_delay

  def get_current_counter(self):
    return self._counter

  def consider_user_interaction(self, has_interaction):
    if has_interaction:
      self.reset()

  def consider_connection_error(self):
    self.reset()

  def consider_timeout(self):
    self.reset()

  def reset(self):
    self._current_delay = 0.0
    self._counter = 0
    self._next_delay = self.min_delay
