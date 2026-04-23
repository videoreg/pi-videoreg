import os
from datetime import datetime
from logging import Logger
from math import ceil

from sdk.videoreg import Videoreg


class VideoKeyboardData:
  all_video_count: int
  page: int
  count_pages: int
  first_video_datetime_str: str
  buttons: list


async def get_video_keyboard(videoreg: Videoreg, logger: Logger, page: int) -> VideoKeyboardData:
  per_page = 6
  offset = per_page * (page - 1)
  h264_dir = str(videoreg.h264_path())

  all_video = [f for f in os.listdir(h264_dir) if os.path.isfile(os.path.join(h264_dir, f))]
  all_video.sort(reverse=True)
  all_video_count = len(all_video)

  result = VideoKeyboardData()
  result.all_video_count = all_video_count
  result.page = page

  if all_video_count == 0:
    return result

  if offset < 0 or offset >= all_video_count:
    offset = 0

  count_pages = int(ceil(all_video_count / per_page))
  buttons = []
  first_video_datetime = None

  i = 0
  for video in all_video[offset : offset + per_page]:
    try:
      video_filename = video.replace(".h264", "")
      video_datetime = datetime.strptime(video_filename, "%Y-%m-%d_%H-%M-%S")
      buttons.append(
        [
          {
            "text": video_datetime.strftime("%H:%M:%S"),
            "callback_data": f"command__camera__send_video__{video_filename}",
          },
          {"text": "🔗", "callback_data": f"command__camera__send_video_link__{video_filename}"},
        ]
      )
      if not first_video_datetime:
        first_video_datetime = video_datetime
    except ValueError:
      pass
    finally:
      i += 1

  buttons_row = []

  if page < count_pages:
    next_page = page + 1
    x5_page = min(count_pages, page + 5)
    if x5_page > next_page:
      buttons_row.append(
        {
          "text": "⏪ Much earlier" if page == 1 else "⏪",
          "callback_data": f"command__camera__list_videos__{x5_page}",
        }
      )

    buttons_row.append(
      {"text": "⬅️ Earlier", "callback_data": f"command__camera__list_videos__{next_page}"}
    )
  if page > 1:
    prev_page = page - 1
    buttons_row.append(
      {"text": "Later ➡️", "callback_data": f"command__camera__list_videos__{prev_page}"}
    )
    x5_page = max(page - 5, 1)
    if x5_page < prev_page:
      buttons_row.append(
        {
          "text": "Much later ⏩" if page == count_pages else "⏩",
          "callback_data": f"command__camera__list_videos__{x5_page}",
        }
      )

  buttons.append(buttons_row)

  first_video_datetime_str = ""
  if first_video_datetime:
    first_video_datetime_str = first_video_datetime.strftime("%Y-%m-%d")

  result.count_pages = count_pages
  result.first_video_datetime_str = first_video_datetime_str
  result.buttons = buttons

  return result
