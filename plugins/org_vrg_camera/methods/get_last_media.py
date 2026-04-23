from datetime import datetime

from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.media_manager import MediaFileType
from sdk.service import ApiMethod

DATE_FORMAT = "%Y-%m-%d_%H-%M-%S"


class MethodGetLastMedia(ApiMethod):
  """Most recent media item (video or photo), sorted by date descending"""

  _plugin: CameraPlugin

  def __init__(self, plugin: CameraPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      media_manager = self._plugin.runner.media_manager

      video_items = []
      video_names = set()

      try:
        mp4_files = set(media_manager.get_files(MediaFileType.MP4))
        for filename in media_manager.get_files(MediaFileType.H264):
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
        self._plugin.logger.error(f"get_last_media: error reading h264_dir: {e}", exc_info=True)

      jpeg_names = set()
      photo_items = []
      try:
        for filename in media_manager.get_files(MediaFileType.JPEG):
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
        self._plugin.logger.error(f"get_last_media: error reading jpeg_dir: {e}", exc_info=True)

      for item in video_items:
        item["preview"] = item["name"] if item["name"] in jpeg_names else None

      items = video_items + photo_items
      items.sort(key=lambda x: x["_dt"], reverse=True)

      last_item = None
      if items:
        last_item = items[0]
        del last_item["_dt"]

      return {
        "status": "ok",
        "data": {
          "item": last_item,
        },
      }

    except Exception as e:
      self._plugin.logger.error(f"Error in get_last_media: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}

  def _parse_datetime(self, name: str):
    try:
      return datetime.strptime(name, DATE_FORMAT)
    except ValueError:
      return None
