import asyncio
import re
from logging import Logger

from sdk.power.base import PowerSupply
from sdk.power.generic import GenericPowerSupply
from sdk.videoreg import Videoreg


async def _i2cdetect(bus: int = 1) -> set[int]:
  try:
    process = await asyncio.create_subprocess_exec(
      "i2cdetect", "-y", "-q", str(bus),
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await process.communicate()
    addresses = set()
    for line in stdout.decode().splitlines():
      for token in line.split():
        if re.fullmatch(r"[0-9a-fA-F]{2}", token):
          addresses.add(int(token, 16))
    return addresses
  except Exception:
    return set()


async def detect_power_supply(videoreg: Videoreg, logger: Logger) -> PowerSupply:
  try:
    addresses = await _i2cdetect(bus=1)
    if 0x57 in addresses:
      from sdk.power.pisugar import PiSugar
      logger.info("power_supply: pisugar detected")
      return PiSugar(videoreg, logger)
    logger.info(f"power_supply: generic (i2c addresses found: {[hex(a) for a in sorted(addresses)]})")
  except Exception as e:
    logger.warning(f"power_supply: detection failed ({e}), falling back to generic")
  return GenericPowerSupply()
