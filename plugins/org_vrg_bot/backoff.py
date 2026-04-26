class Backoff:
  def next_delay(self) -> float:
    raise Exception("Not implemented")

  def get_http_timeout(self) -> int:
    raise Exception("Not implemented")

  def get_tg_timeout(self) -> int:
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
  jitter = 0.1

  short_timeout = 5
  normal_timeout = 15

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
    timeout = self.short_timeout if self._counter == 0 else self.normal_timeout
    return timeout
  
  def get_tg_timeout(self) -> int:
    timeout = self.short_timeout if self._counter == 0 else self.normal_timeout
    return timeout-2

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

# TODO: Delete if NormalBackoff is ok, and PowerSaveBackoff is not needed
class PowerSaveBackoff(Backoff):
  limit_normal_requests = 4

  normal_delay = 2.0
  powersave_delay = 30.0

  normal_http_timeout = 15
  normal_tg_timeout = 13

  powersave_http_timeout = 5
  powersave_tg_timeout = 0

  _count_scince_last_interaction: int
  _current_delay: float
  _current_http_timeout: int
  _current_tg_timeout: int

  def __init__(self):
    self._current_delay = 0.0
    # start pooling as if no user interaction
    self._count_scince_last_interaction = self.limit_normal_requests
    self._current_http_timeout = self.powersave_http_timeout
    self._current_tg_timeout = self.powersave_tg_timeout

  def next_delay(self) -> float:
    self._count_scince_last_interaction += 1

    if self._count_scince_last_interaction <= self.limit_normal_requests:
      # NORMAL
      self._current_delay = self.normal_delay
      self._current_http_timeout = self.normal_http_timeout
      self._current_tg_timeout = self.normal_tg_timeout
    else:
      # POWERSAVE
      self._current_delay = self.powersave_delay
      self._current_http_timeout = self.powersave_http_timeout
      self._current_tg_timeout = self.powersave_tg_timeout

    return self._current_delay

  def get_http_timeout(self) -> int:
    return self._current_http_timeout

  def get_tg_timeout(self) -> int:
    return self._current_tg_timeout

  def get_current_delay(self):
    return self._current_delay

  def get_current_counter(self):
    return self._count_scince_last_interaction

  def reset(self):
    self._current_delay = 0.0  # in fact, never be zero. Will be set in next_delay()
    self._count_scince_last_interaction = 0
    self._current_http_timeout = self.normal_http_timeout
    self._current_tg_timeout = self.normal_tg_timeout

  def consider_user_interaction(self, has_interaction: bool):
    if has_interaction:
      self.reset()

  def consider_connection_error(self):
    self.reset()

  def consider_timeout(self):
    self.reset()
