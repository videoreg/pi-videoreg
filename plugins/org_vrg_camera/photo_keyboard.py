import os
from datetime import datetime
from logging import Logger
from math import ceil

from sdk.videoreg import Videoreg


class PhotoKeyboardData:
  all_files_count: int
  page: int
  count_pages: int
  first_file_datetime_str: str
  buttons: list


async def get_photos_keyboard(videoreg: Videoreg, logger: Logger, page: int) -> PhotoKeyboardData:
  per_page = 6
  offset = per_page * (page - 1)
  photo_dir = str(videoreg.jpeg_path())

  all_files = [f for f in os.listdir(photo_dir) if os.path.isfile(os.path.join(photo_dir, f))]
  all_files.sort(reverse=True)
  all_files_count = len(all_files)

  result = PhotoKeyboardData()
  result.all_files_count = all_files_count
  result.page = page

  if all_files_count == 0:
    return result

  if offset < 0 or offset >= all_files_count:
    offset = 0

  count_pages = int(ceil(all_files_count / per_page))
  buttons = []
  first_file_datetime = None

  i = 0
  for file in all_files[offset : offset + per_page]:
    file_name = file.replace(".jpg", "")
    file_datetime = datetime.strptime(file_name, "%Y-%m-%d_%H-%M-%S")
    buttons.append(
      [
        {
          "text": file_datetime.strftime("%H:%M:%S"),
          "callback_data": f"command__camera__send_photo__{file_name}",
        },
        {"text": "🔗", "callback_data": f"command__camera__send_photo_link__{file_name}"},
      ]
    )
    if not first_file_datetime:
      first_file_datetime = file_datetime
    i += 1

  buttons_row = []

  if page < count_pages:
    next_page = page + 1
    x5_page = min(count_pages, page + 5)
    if x5_page > next_page:
      buttons_row.append(
        {
          "text": "⏪ Much earlier" if page == 1 else "⏪",
          "callback_data": f"command_edit__camera__list_photos__{x5_page}",
        }
      )

    buttons_row.append(
      {"text": "⬅️ Earlier", "callback_data": f"command_edit__camera__list_photos__{next_page}"}
    )
  if page > 1:
    prev_page = page - 1
    buttons_row.append(
      {"text": "Later ➡️", "callback_data": f"command_edit__camera__list_photos__{prev_page}"}
    )
    x5_page = max(page - 5, 1)
    if x5_page < prev_page:
      buttons_row.append(
        {
          "text": "Much later ⏩" if page == count_pages else "⏩",
          "callback_data": f"command_edit__camera__list_photos__{x5_page}",
        }
      )

  buttons.append(buttons_row)

  first_file_datetime_str = ""
  if first_file_datetime:
    first_file_datetime_str = first_file_datetime.strftime("%Y-%m-%d")

  result.count_pages = count_pages
  result.first_file_datetime_str = first_file_datetime_str
  result.buttons = buttons

  return result
