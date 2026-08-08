import logging
import sys

LOG_FORMAT_PREFIX = "%(asctime)s %(levelname)s:"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _get_numeric_log_level(log_level):
  numeric_log_level = getattr(logging, log_level.upper(), None)
  if not isinstance(numeric_log_level, int):
    raise ValueError("Invalid log level: %s" % log_level)
  return numeric_log_level


def create_logger(name, log_level, tag=""):
  """Creates a stdout logger; systemd collects the output into the journal."""
  numeric_log_level = _get_numeric_log_level(log_level)

  logger = logging.getLogger(name)
  logger.setLevel(numeric_log_level)

  stream_handler = logging.StreamHandler(stream=sys.stdout)
  stream_handler.setFormatter(
    logging.Formatter(f"{LOG_FORMAT_PREFIX}{tag} %(message)s", DATE_FORMAT)
  )

  logger.addHandler(stream_handler)

  return logger


class ConditionLog:
  """Logs a persisting failure once instead of on every retry.

  A polling loop that keeps hitting the same error (no modem on the port, no
  network, ...) otherwise fills the journal with identical warnings for as long
  as the condition holds. Here the first occurrence is logged at the requested
  level; while the same message repeats it drops to debug. `resolve()` closes
  the condition, so the next failure is logged in full again and the recovery
  is reported together with the number of suppressed repeats.

  Conditions are told apart by `key`, so one instance can serve several
  independent operations of the same component.
  """

  def __init__(self, logger: logging.Logger):
    self._logger = logger
    self._active: dict[str, tuple[str, int]] = {}

  def warning(self, key: str, message: str):
    self.log(logging.WARNING, key, message)

  def error(self, key: str, message: str):
    self.log(logging.ERROR, key, message)

  def log(self, level: int, key: str, message: str):
    active = self._active.get(key)
    if active and active[0] == message:
      self._active[key] = (message, active[1] + 1)
      self._logger.debug(message)
      return

    self._active[key] = (message, 0)
    self._logger.log(level, message)

  def resolve(self, key: str, message: str = None):
    """Mark the condition as gone. Logs `message` only if it was failing."""
    active = self._active.pop(key, None)
    if active is None or not message:
      return

    _, repeats = active
    if repeats:
      message = f"{message} (after {repeats} suppressed repeat(s))"
    self._logger.info(message)
