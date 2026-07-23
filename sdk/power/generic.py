from sdk.power.base import ChargingStatus, PowerSupply


class GenericPowerSupply(PowerSupply):
  """Plain USB / wall power, no telemetry. Assume on-AC; battery unknown."""
  name = "generic"
  title = "Generic USB"
  battery_telemetry = False

  async def get_battery_percent(self) -> int | None:
    return None

  async def get_charging_status(self) -> ChargingStatus:
    return ChargingStatus.CHARGING
