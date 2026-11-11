from plugins.org_vrg_rearcam.plugin import RearcamPlugin
from sdk.socket.api import ApiMethod


def parse_camera_number(args) -> int | None:
  """Camera number from method args; tolerates query-string digits."""
  number = args.get("number") if isinstance(args, dict) else None
  if isinstance(number, str) and number.isdigit():
    number = int(number)
  if not isinstance(number, int) or number < 2:
    return None
  return number
