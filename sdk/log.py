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
