from enum import Enum


class ChargingStatus(str, Enum):
  CHARGING = "charging"
  NOT_CHARGING = "not_charging"
  UNKNOWN = "unknown"

  def to_int(self):
    if self == ChargingStatus.CHARGING:
      return 1
    elif self == ChargingStatus.NOT_CHARGING:
      return -1
    else:
      return 0


class PowerSupply:
  """Abstract Pi power source. Implementations: PiSugar, GenericPowerSupply."""
  name: str = "unknown"
  title: str = "Unknown"
  battery_telemetry: bool = False

  async def get_battery_percent(self) -> int | None:
    raise NotImplementedError

  async def get_charging_status(self) -> ChargingStatus:
    raise NotImplementedError

  async def get_charging_status_slow_but_safe(self) -> ChargingStatus:
    """Default implementation: just delegates to get_charging_status().
    PiSugar overrides this with a double-check to compensate for hardware lies."""
    return await self.get_charging_status()
