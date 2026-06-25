import json
import logging

from plugins.org_vrg_botvk.main import MenuButton

# VK limits: bottom keyboards allow up to 10 rows; group buttons to stay within it.
MENU_BUTTONS_PER_ROW = 3

# VK inline keyboard limits (error 911 if exceeded).
INLINE_MAX_ROWS = 6
INLINE_MAX_BUTTONS = 10
INLINE_MAX_BUTTONS_PER_ROW = 5

logger = logging.getLogger("botvk")


def _callback_button(label: str, callback_data: str) -> dict:
  return {
    "action": {
      "type": "callback",
      "label": str(label),
      "payload": json.dumps({"cb": callback_data}),
    },
    "color": "secondary",
  }


def inline_callback_keyboard(rows) -> "str | None":
  """Convert a generic keyboard (Telegram-shaped rows of {text, callback_data})
  into a VK inline keyboard JSON string. Returns None for an empty keyboard."""
  if not rows:
    return None

  vk_rows = []
  for row in rows:
    vk_row = []
    for button in row:
      label = button.get("text", "")
      callback_data = button.get("callback_data")
      if callback_data:
        vk_row.append(_callback_button(label, callback_data))
      else:
        # Plain button: tapping sends the label as a message.
        vk_row.append({"action": {"type": "text", "label": str(label)}, "color": "secondary"})
    if vk_row:
      vk_rows.append(vk_row)

  if not vk_rows:
    return None

  # Diagnostic only: VK rejects an over-limit inline keyboard with error 911.
  # Do not truncate here — dropping rows would make paged items unreachable.
  total_buttons = sum(len(r) for r in vk_rows)
  widest_row = max(len(r) for r in vk_rows)
  if (
    len(vk_rows) > INLINE_MAX_ROWS
    or total_buttons > INLINE_MAX_BUTTONS
    or widest_row > INLINE_MAX_BUTTONS_PER_ROW
  ):
    logger.warning(
      f"inline keyboard exceeds VK limits: rows={len(vk_rows)} buttons={total_buttons} "
      f"widest_row={widest_row} (max rows={INLINE_MAX_ROWS} buttons={INLINE_MAX_BUTTONS} "
      f"per_row={INLINE_MAX_BUTTONS_PER_ROW}); VK will likely reject with error 911"
    )

  return json.dumps({"inline": True, "buttons": vk_rows})


def menu_keyboard(menu_buttons: list[MenuButton]) -> "str | None":
  """Build a persistent bottom keyboard from the command menu buttons."""
  if not menu_buttons:
    return None

  vk_rows = []
  for i in range(0, len(menu_buttons), MENU_BUTTONS_PER_ROW):
    chunk = menu_buttons[i : i + MENU_BUTTONS_PER_ROW]
    vk_rows.append([_callback_button(b.label, b.callback_data) for b in chunk])

  return json.dumps({"inline": False, "one_time": False, "buttons": vk_rows})
