import asyncio
import os
from datetime import datetime

import plugins.org_vrg_camera.osd as osd
from plugins.org_vrg_gps.modem import Modem
from plugins.org_vrg_gps.tracker import GpsTracker
from sdk.journal import JournalRecord
from sdk.media_manager import MediaFileType
from sdk.power import ChargingStatus
from sdk.service import Plugin

gps_token = osd.Token(key="gps", text=None, weight=osd.WEIGHT_GPS)

lbs_token = osd.Token(key="lbs", text=None, weight=osd.WEIGHT_LBS)


class GpsPlugin(Plugin):
  modem: Modem = None
  _gps_monitor_started = False
  _gps_location = None
  _lbs_location = None
  _is_charging = "--"
  _bat_level = "--"
  _cpu_temp = "--"
  _gps_tracker: GpsTracker = None

  def __init__(self, id, name, runner):
    super().__init__(id, name, runner)

  async def start(self):
    await super().start()
    asyncio.create_task(self._start_lifecycle_loop())
    asyncio.create_task(self._check_files_loop())

  def init_modem(self, modem: Modem):
    self.modem = modem

  async def stop(self):
    await super().stop()
    if self._gps_tracker:
      track_file_name = os.path.basename(self._gps_tracker._file_path)
      kept = self._gps_tracker.close()
      self._gps_tracker = None
      if not kept:
        self.runner.media_manager.remove_file(MediaFileType.GPS, track_file_name)

    # self._revert_annotation()

  async def _start_lifecycle_loop(self):
    while self.runner.is_running():
      charging_status = await self.runner.power_supply.get_charging_status_slow_but_safe()

      if charging_status == ChargingStatus.NOT_CHARGING:
        if self._gps_tracker:
          track_file_name = os.path.basename(self._gps_tracker._file_path)
          kept = self._gps_tracker.close()
          self._gps_tracker = None
          if not kept:
            self.runner.media_manager.remove_file(MediaFileType.GPS, track_file_name)
      else:
        if not self.modem.is_enabled():
          is_enabled = await self.modem.enable()
          if not is_enabled:
            await asyncio.sleep(5)
            continue

        if not self._gps_monitor_started:
          asyncio.create_task(self._start_gps_monitor())
          self._gps_monitor_started = True

        if not self._gps_tracker:
          track_file_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.gpx")
          self._gps_tracker = GpsTracker(str(self.runner.videoreg.gps_path(track_file_name)))
          self._gps_tracker.start()
          self.runner.media_manager.append_file(MediaFileType.GPS, track_file_name)
          asyncio.create_task(
            self.journal_client.write(
              JournalRecord(type="track_created", data={"filename": track_file_name})
            )
          )

      await asyncio.sleep(5)

  async def _start_gps_monitor(self):
    self.logger.info("will start gps monitor")

    try:
      gps_enabled = False

      # enable gps
      i = 0
      while not gps_enabled and self.runner.is_running():
        i += 1

        # Sometimes modem could change it's id (probably due to bad usb cable connection)
        if i % 10 == 0:  # ~ every minute
          modem_enabled = await self.modem.enable()
          if not modem_enabled:
            self.logger.warning("gps enable loop: modem disappeared")
            self._gps_monitor_started = False
            break  # exit gps monitor loop. GPS should be restarted in lifecycle loop

        gps_enabled = await self.modem.enable_gps()

        if not gps_enabled:
          self.logger.warning("gps monitor: gps not enabled")
          await asyncio.sleep(6)
          continue

        await self.modem.enable_lbs()

        self.logger.info("gps monitor enabled")

      # track gps
      enabled_modem_id = self.modem.modem_id  # save id at the moment GPS was enabled
      i = 0
      while self.runner.is_running():
        i += 1

        # Sometimes modem could change it's id (probably due to bad usb cable connection)
        if i % 10 == 0:  # ~ every minute
          modem_enabled = await self.modem.enable()
          if not modem_enabled or self.modem.modem_id != enabled_modem_id:
            self.logger.warning("gps track loop: modem disappeared or id changed")
            self._gps_monitor_started = False
            break  # exit gps monitor loop. GPS should be restarted in lifecycle loop

        self._gps_location = await self.modem.get_location_gps()
        self._lbs_location = await self.modem.get_location_lbs()

        if (
          self._gps_location
          and self._gps_location["latitude"] != "--"
          and self._gps_location["longitude"] != "--"
          and self._gps_tracker
        ):
          self._gps_tracker.track(
            float(self._gps_location["latitude"]),
            float(self._gps_location["longitude"]),
            self._gps_location.get("speed"),
          )

        await self._update_osd()

        # If GPS time lags system time by more than 5 minutes — GPS is frozen, restart it
        gps_dt_str = self._gps_location.get("datetime") if self._gps_location else None
        if gps_dt_str:
          try:
            gps_dt = datetime.fromisoformat(gps_dt_str)
            if (datetime.now().astimezone() - gps_dt).total_seconds() > 300:
              self.logger.warning(f"gps time is stale: {gps_dt}, restarting gps monitor")
              await self.modem.disable_gps()
              await asyncio.sleep(15)
              break  # finally block will set _gps_monitor_started = False
          except Exception as e:
            self.logger.warning(f"gps stale time check error: {e}")

        # self.logger.debug(f"gps: {self._gps_location}")
        # self.logger.debug(f"lbs: {self._lbs_location}")

        await asyncio.sleep(6)

    except Exception as e:
      self.logger.warning(f"gps monitor error: {e}")

    finally:
      self._gps_monitor_started = False

  async def _update_osd(self):
    global gps_token, lbs_token

    if self._gps_location:
      speed = self._gps_location.get("speed")
      speed_str = f" S:{speed}" if speed is not None else ""
      lat = self._gps_location["latitude"]
      lng = self._gps_location["longitude"]
      gps_token.text = f"GPS:{lat},{lng}{speed_str}"
    else:
      gps_token.text = None

    if self._lbs_location:
      lat = self._lbs_location["latitude"]
      lng = self._lbs_location["longitude"]
      lbs_token.text = f"LBS:{lat},{lng}"
    else:
      lbs_token.text = None

    await self._connection.send_data("osd", [gps_token.to_dict(), lbs_token.to_dict()])

  async def _check_files_loop(self):
    await asyncio.sleep(15)
    while self.runner.is_running():
      removed = self.runner.media_manager.remove_old_files(MediaFileType.GPS, max_files=50)
      if removed > 0:
        self.logger.debug(f"removed gps files {removed}")

      await asyncio.sleep(60 * 5)
