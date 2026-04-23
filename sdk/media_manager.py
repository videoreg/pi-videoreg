import os
from enum import Enum
from pathlib import Path

from sdk.videoreg import Videoreg


class MediaFileType(Enum):
  H264 = "h264"
  MP4 = "mp4"
  JPEG = "jpeg"
  SMS = "sms"
  GPS = "gps"
  H264_FAVE = "h264_fave"
  JPEG_FAVE = "jpeg_fave"


class MediaManager:
  """
  Manages media files of the system: provides access to file lists by type,
  maintains an in-memory cache, and handles deletion operations.

  Each file type (MediaFileType) is stored in a separate directory whose path
  is resolved via the Videoreg object. The file list is loaded from disk on
  first access and then kept in the cache — external code must notify MediaManager
  of any changes via append_file / remove_file / invalidate.
  """

  def __init__(self, videoreg: Videoreg):
    self._videoreg = videoreg
    self._cache: dict[MediaFileType, list[str]] = {}

  def get_dir(self, file_type: MediaFileType) -> Path:
    """Returns the directory path for the given file type."""
    mapping = {
      MediaFileType.H264: self._videoreg.h264_path,
      MediaFileType.MP4: self._videoreg.mp4_path,
      MediaFileType.JPEG: self._videoreg.jpeg_path,
      MediaFileType.SMS: self._videoreg.sms_path,
      MediaFileType.GPS: self._videoreg.gps_path,
      MediaFileType.H264_FAVE: self._videoreg.h264_fave_path,
      MediaFileType.JPEG_FAVE: self._videoreg.jpeg_fave_path,
    }
    return mapping[file_type]()

  def get_files(self, file_type: MediaFileType) -> list[str]:
    """
    Returns a list of filenames (without path) for the given file type.

    On the first call, reads the directory from disk and stores the result in cache.
    Subsequent calls return the cached list. Returns an empty list if the directory
    is unavailable.
    """
    if file_type in self._cache:
      return self._cache[file_type]

    dir_path = self.get_dir(file_type)
    try:
      files = [f for f in os.listdir(str(dir_path)) if os.path.isfile(str(dir_path / f))]
    except Exception:
      files = []

    self._cache[file_type] = files
    return files

  def invalidate(self, file_type: MediaFileType):
    """Clears the cache for the given file type. The next call to get_files will re-read from disk."""
    self._cache.pop(file_type, None)

  def append_file(self, file_type: MediaFileType, filename: str):
    """
    Adds a filename to the cache if the cache is already loaded and the file is not yet present.

    Called when a new file appears (e.g. from FolderWatcher) to avoid invalidating the entire cache.
    """
    cached = self._cache.get(file_type)
    if cached is not None and filename not in cached:
      cached.append(filename)

  def remove_file(self, file_type: MediaFileType, filename: str):
    """Removes a filename from the cache. Does not delete the file from disk."""
    cached = self._cache.get(file_type)
    if cached is not None and filename in cached:
      cached.remove(filename)

  def remove_files(self, file_type: MediaFileType, filenames: list[str]):
    """Removes multiple filenames from the cache. Does not delete files from disk."""
    cached = self._cache.get(file_type)
    if cached is not None:
      to_remove = set(filenames)
      self._cache[file_type] = [f for f in cached if f not in to_remove]

  def remove_old_files(
    self,
    file_type: MediaFileType,
    max_files: int,
    companion_types: list["MediaFileType"] | None = None,
  ) -> int:
    """
    Removes old files of the primary type, keeping at most max_files.

    Files are sorted by name; excess files (oldest in alphabetical order) are removed first.

    :param file_type: primary file type used for sorting and applying the limit.
    :param max_files: maximum number of primary-type files to keep.
    :param companion_types: additional file types to remove alongside the primary files.
                            Matching is done by filename stem (name without extension).
                            The limit and sort order are not applied to companion types.
    :return: number of removed primary-type files.
    """
    files = sorted(self.get_files(file_type))
    dir_path = str(self.get_dir(file_type))
    to_remove = len(files) - max_files
    removed_names = []
    if to_remove > 0:
      for i in range(to_remove):
        filename = files[i]
        try:
          os.remove(os.path.join(dir_path, filename))
          removed_names.append(filename)
        except Exception:
          pass
      if removed_names:
        self.remove_files(file_type, removed_names)
        if companion_types:
          stem_set = {Path(f).stem for f in removed_names}
          for companion_type in companion_types:
            companion_dir = str(self.get_dir(companion_type))
            companion_names = [
              f for f in self.get_files(companion_type) if Path(f).stem in stem_set
            ]
            for companion_name in companion_names:
              try:
                os.remove(os.path.join(companion_dir, companion_name))
              except Exception:
                pass
            if companion_names:
              self.remove_files(companion_type, companion_names)
    return len(removed_names)
