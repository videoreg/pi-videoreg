import logging
from pathlib import Path

from sdk.folder_watcher import FolderWatcher
from sdk.journal import JournalRecord
from sdk.media_manager import MediaFileType, MediaManager


class JpegFolderWatcher(FolderWatcher):
  """Watches jpeg directory for new files, updates MediaManager cache and writes journal events."""

  def __init__(
    self, watch_dir: Path, journal_client, media_manager: MediaManager, logger: logging.Logger
  ):
    super().__init__(watch_dir, logger)
    self._journal_client = journal_client
    self._media_manager = media_manager

  async def on_file_created(self, filename: str):
    self._media_manager.append_file(MediaFileType.JPEG, filename)
    await self._journal_client.write(JournalRecord(type="jpeg", data={"filename": filename}))
