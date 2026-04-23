import os
from logging import Logger
from math import ceil

from sdk.videoreg import Videoreg


class SmsKeyboardData:
  count_total: int
  page: int
  count_pages: int
  buttons: list


async def get_sms_keyboard(videoreg: Videoreg, logger: Logger, page: int) -> SmsKeyboardData:
  per_page = 6
  offset = per_page * (page - 1)
  sms_dir = str(videoreg.sms_path())

  all_sms = [f for f in os.listdir(sms_dir) if os.path.isfile(os.path.join(sms_dir, f))]
  all_sms.sort(reverse=True)
  all_sms_count = len(all_sms)

  result = SmsKeyboardData()
  result.count_total = all_sms_count
  result.page = page

  if all_sms_count == 0:
    return result

  if offset < 0 or offset >= len(all_sms):
    offset = 0

  count_pages = int(ceil(len(all_sms) / per_page))
  buttons = []

  i = 0
  for sms in all_sms[offset : offset + per_page]:
    sms_filename = sms.replace(".json", "")
    buttons.append(
      [{"text": sms_filename, "callback_data": f"command__sms__get_sms__{sms_filename}"}]
    )
    i += 1

  buttons_row = []

  if page < count_pages:
    next_page = page + 1
    x5_page = min(count_pages, page + 5)
    if x5_page > next_page:
      buttons_row.append(
        {
          "text": "⏪ Much earlier" if page == 1 else "⏪",
          "callback_data": f"command__sms__list_sms__{x5_page}",
        }
      )

    buttons_row.append(
      {"text": "⬅️ Earlier", "callback_data": f"command__sms__list_sms__{next_page}"}
    )
  if page > 1:
    prev_page = page - 1
    buttons_row.append({"text": "Later ➡️", "callback_data": f"command__sms__list_sms__{prev_page}"})
    x5_page = max(page - 5, 1)
    if x5_page < prev_page:
      buttons_row.append(
        {
          "text": "Much later ⏩" if page == count_pages else "⏩",
          "callback_data": f"command__sms__list_sms__{x5_page}",
        }
      )

  buttons.append(buttons_row)

  result.count_pages = count_pages
  result.buttons = buttons

  return result
