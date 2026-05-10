import asyncio
import os
import time
from datetime import datetime
from logging import Logger
import psutil

from plugins.org_vrg_stat.dirs import Dirs
from plugins.org_vrg_stat.tracker import Tracker
from sdk.power import PowerSupply
from sdk.power.pisugar import PiSugar


class TrackerImpl(Tracker):
  _stop_event: asyncio.Event
  _logger: Logger
  _power_supply: PowerSupply
  _dirs: Dirs

  def __init__(self, logger: Logger, power_supply: PowerSupply, dirs: Dirs):
    self._stop_event = asyncio.Event()
    self._logger = logger
    self._power_supply = power_supply
    self._dirs = dirs

    self.prev_traffic_timestamp_kbps = 0
    self.prev_traffic_counters_kbps: dict = None

    self.prev_traffic_timestamp_hourly = 0
    self.prev_traffic_counters_hourly: dict = None

  async def start_loop(self):
    await asyncio.sleep(4)

    i = 0

    while not self._stop_event.is_set():
      await self._log_pisugar()
      self._log_traffic()
      self._log_temp()

      if i % 120 == 0:
        self._clean_old_data(str(self._dirs.cpu))
        self._clean_old_data(str(self._dirs.pisugar))
        self._clean_old_data(str(self._dirs.traffic_kbps))
        self._clean_old_data(str(self._dirs.traffic_hourly))
        self._clean_old_data(str(self._dirs.temp))

      i += 1

      await asyncio.sleep(30)

  def stop_loop(self):
    self._stop_event.set()

  def _clean_old_data(self, dir):
    all_files = [f for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]
    all_files.sort(reverse=True)
    if len(all_files) > 5:
      oldest = all_files[-1]
      os.remove(os.path.join(dir, oldest))

  async def _log_pisugar(self):
    battery_percent = await self._power_supply.get_battery_percent()
    charging_status = await self._power_supply.get_charging_status()
    temp = await self._power_supply.get_temp() if isinstance(self._power_supply, PiSugar) else None
    self._logger.debug(
      f"power: battery_percent={battery_percent} charging_status={charging_status} temp={temp}"
    )
    file_name = datetime.today().strftime("%Y-%m-%d.txt")
    file_path = f"{self._dirs.pisugar}/{file_name}"
    timestamp = time.time()
    timedate = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

    with open(file_path, "a+") as f:
      f.write(f"{int(timestamp)},{timedate},{battery_percent},{charging_status},{temp}\n")

  def _log_traffic(self):
    file_name = datetime.today().strftime("%Y-%m-%d.txt")
    file_path_kbps = f"{self._dirs.traffic_kbps}/{file_name}"
    file_path_hourly = f"{self._dirs.traffic_hourly}/{file_name}"
    timestamp = time.time()

    stat = psutil.net_io_counters(pernic=True)

    if self.prev_traffic_counters_kbps is None or self.prev_traffic_timestamp_kbps == 0:
      self.prev_traffic_counters_kbps = stat
      self.prev_traffic_timestamp_kbps = timestamp
    else:
      line_kbps = f"{int(timestamp)}"

      for interface, counters in stat.items():
        sent_kbps = 0
        recv_kbps = 0

        if interface in self.prev_traffic_counters_kbps:
          prev = self.prev_traffic_counters_kbps[interface]
          diff_sent_kb = int(counters.bytes_sent - prev.bytes_sent) / 1024
          diff_recv_kb = int(counters.bytes_recv - prev.bytes_recv) / 1024

          seconds_diff = timestamp - self.prev_traffic_timestamp_kbps
          sent_kbps = round(diff_sent_kb / seconds_diff, 1)
          recv_kbps = round(diff_recv_kb / seconds_diff, 1)

        line_kbps += f",{interface}:{sent_kbps}:{recv_kbps}"

      self.prev_traffic_counters_kbps = stat
      self.prev_traffic_timestamp_kbps = timestamp

      with open(file_path_kbps, "a+") as f:
        f.write(f"{line_kbps}\n")

    # HOURLY

    if self.prev_traffic_counters_hourly is None or self.prev_traffic_timestamp_hourly == 0:
      self.prev_traffic_counters_hourly = stat
      self.prev_traffic_timestamp_hourly = timestamp
    elif timestamp - self.prev_traffic_timestamp_hourly > 3600:
      line_hourly = f"{int(timestamp)}"

      for interface, counters in stat.items():
        diff_sent_mb = 0
        diff_recv_mb = 0

        if interface in self.prev_traffic_counters_hourly:
          prev = self.prev_traffic_counters_hourly[interface]
          diff_sent_mb = round(int(counters.bytes_sent - prev.bytes_sent) / (1024 * 1024), 1)
          diff_recv_mb = round(int(counters.bytes_recv - prev.bytes_recv) / (1024 * 1024), 1)

        line_hourly += f",{interface}:{diff_sent_mb}:{diff_recv_mb}"

      self.prev_traffic_counters_hourly = stat
      self.prev_traffic_timestamp_hourly = timestamp

      with open(file_path_hourly, "a+") as f:
        f.write(f"{line_hourly}\n")

  def _log_temp(self):
    with open("/sys/class/thermal/thermal_zone0/temp") as f:
      temp = round(float(f.read()) / 1000.0, 1)
      file_name = datetime.today().strftime("%Y-%m-%d.txt")
      file_path = f"{self._dirs.temp}/{file_name}"
      timestamp = time.time()
      timedate = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

      with open(file_path, "a+") as f:
        f.write(f"{int(timestamp)},{timedate},{temp}\n")
