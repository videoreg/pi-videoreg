import logging
import sys
from logging.handlers import RotatingFileHandler

LOG_FORMAT_PREFIX = "%(asctime)s %(levelname)s:"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _get_numeric_log_level(log_level):
  numeric_log_level = getattr(logging, log_level.upper(), None)
  if not isinstance(numeric_log_level, int):
    raise ValueError("Invalid log level: %s" % log_level)
  return numeric_log_level


def create_rotating_file_handler(log_file, tag="") -> RotatingFileHandler:
  rotating_file_handler = RotatingFileHandler(
    log_file, mode="a+", maxBytes=5 * 1024 * 1024, backupCount=1, encoding=None, delay=0
  )
  rotating_file_handler.setFormatter(
    logging.Formatter(f"{LOG_FORMAT_PREFIX}{tag} %(message)s", DATE_FORMAT)
  )
  return rotating_file_handler


def create_logger(name, log_level, rotating_file_handler: RotatingFileHandler, tag=""):
  numeric_log_level = _get_numeric_log_level(log_level)

  logger = logging.getLogger(name)
  logger.setLevel(numeric_log_level)

  stream_handler = logging.StreamHandler(stream=sys.stdout)
  stream_handler.setFormatter(
    logging.Formatter(f"{LOG_FORMAT_PREFIX}{tag} %(message)s", DATE_FORMAT)
  )

  logger.addHandler(stream_handler)
  logger.addHandler(rotating_file_handler)

  return logger
