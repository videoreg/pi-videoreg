import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from threading import Event

import inotify_simple

_READ_TIMEOUT_MS = 500


class FolderWatcher(ABC):
  """Watches a directory for new files using inotify."""

  def __init__(self, watch_dir: Path, logger: logging.Logger):
    self._watch_dir = watch_dir
    self._logger = logger
    self._task: asyncio.Task = None
    self._stop_event = Event()

  def start(self):
    self._stop_event.clear()
    self._task = asyncio.create_task(self._watch_loop())

  async def stop(self):
    self._stop_event.set()
    if self._task:
      self._task.cancel()
      try:
        await self._task
      except asyncio.CancelledError:
        pass

  @abstractmethod
  async def on_file_created(self, filename: str):
    pass

  def _read_events(self, inotify: inotify_simple.INotify) -> list:
    """Blocking read with timeout, called in executor thread."""
    while not self._stop_event.is_set():
      events = inotify.read(timeout=_READ_TIMEOUT_MS)
      if events:
        return events
    return []

  async def _watch_loop(self):
    inotify = inotify_simple.INotify()
    try:
      inotify.add_watch(str(self._watch_dir), inotify_simple.flags.CREATE)
      self._logger.info(f"{self.__class__.__name__}: watching {self._watch_dir}")

      loop = asyncio.get_event_loop()
      while not self._stop_event.is_set():
        events = await loop.run_in_executor(None, self._read_events, inotify)
        for event in events:
          filename = event.name
          if not filename:
            continue
          self._logger.debug(f"{self.__class__.__name__}: new file {filename}")
          asyncio.create_task(self.on_file_created(filename))
    except asyncio.CancelledError:
      raise
    except Exception as e:
      self._logger.error(f"{self.__class__.__name__} error: {type(e).__name__}: {e}")
    finally:
      inotify.close()
