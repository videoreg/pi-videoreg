from datetime import datetime

from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.media_manager import MediaFileType
from sdk.service import ApiMethod

DATE_FORMAT = "%Y-%m-%d_%H-%M-%S"


class MethodListMedia(ApiMethod):
  """Combined paginated list of videos and photos, sorted by date descending"""

  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      if not isinstance(args, dict):
        args = {}

      all_items = bool(args.get("all", False))
      page = int(args.get("page", 1))
      per_page = int(args.get("per_page", 20))
      fave = bool(args.get("fave", False))

      if page < 1:
        page = 1
      if per_page < 1:
        per_page = 20

      media_manager = self._plugin.runner.media_manager

      video_items = []
      video_names = set()

      if fave:
        h264_type = MediaFileType.H264_FAVE
        jpeg_type = MediaFileType.JPEG_FAVE
      else:
        h264_type = MediaFileType.H264
        jpeg_type = MediaFileType.JPEG

      # Read video files (.h264)
      try:
        mp4_files = set() if fave else set(media_manager.get_files(MediaFileType.MP4))
        for filename in media_manager.get_files(h264_type):
          if not filename.endswith(".h264"):
            continue
          name = filename[: -len(".h264")]
          dt = self._parse_datetime(name)
          if dt is None:
            continue
          mp4_exists = (name + ".mp4") in mp4_files
          video_names.add(name)
          video_items.append(
            {
              "type": "video",
              "name": name,
              "datetime": dt.isoformat(),
              "ready": mp4_exists,
              "_dt": dt,
            }
          )
      except Exception as e:
        self._plugin.logger.error(f"list_media: error reading h264_dir: {e}", exc_info=True)

      # Read jpg files: collect all names and separate photo items (not thumbnails)
      jpeg_names = set()
      photo_items = []
      try:
        for filename in media_manager.get_files(jpeg_type):
          if filename.endswith(".jpg"):
            name = filename[: -len(".jpg")]
          elif filename.endswith(".jpeg"):
            name = filename[: -len(".jpeg")]
          else:
            continue
          dt = self._parse_datetime(name)
          if dt is None:
            continue
          jpeg_names.add(name)
          if name in video_names:
            # This is a video thumbnail, skip as a standalone photo
            continue
          photo_items.append(
            {
              "type": "photo",
              "name": name,
              "datetime": dt.isoformat(),
              "ready": True,
              "_dt": dt,
            }
          )
      except Exception as e:
        self._plugin.logger.error(f"list_media: error reading jpeg_dir: {e}", exc_info=True)

      # Attach preview to video items
      for item in video_items:
        item["preview"] = item["name"] if item["name"] in jpeg_names else None

      # Merge and sort by date descending (before pagination)
      items = video_items + photo_items
      items.sort(key=lambda x: x["_dt"], reverse=True)

      # Remove internal field before returning
      for item in items:
        del item["_dt"]

      total_count = len(items)

      if all_items:
        return {
          "status": "ok",
          "data": {
            "total_count": total_count,
            "items": items,
          },
        }

      total_pages = max(1, (total_count + per_page - 1) // per_page)

      if page > total_pages:
        page = total_pages

      start = (page - 1) * per_page
      end = start + per_page
      page_items = items[start:end]

      return {
        "status": "ok",
        "data": {
          "page": page,
          "total_pages": total_pages,
          "total_count": total_count,
          "per_page": per_page,
          "items": page_items,
        },
      }

    except Exception as e:
      self._plugin.logger.error(f"Error in list_media: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}

  def _parse_datetime(self, name: str):
    try:
      return datetime.strptime(name, DATE_FORMAT)
    except ValueError:
      return None
