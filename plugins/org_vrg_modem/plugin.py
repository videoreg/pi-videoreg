import asyncio
import json
import os
import time
from datetime import datetime

import plugins.org_vrg_camera.osd as osd
from plugins.org_vrg_modem.modem import Modem
from plugins.org_vrg_modem.sms_manager import SmsManager
from plugins.org_vrg_modem.tracker import GpsTracker
from sdk.command_cancel import apply_command_cancellations
from sdk.journal import JournalRecord
from sdk.media_manager import MediaFileType
from sdk.power import ChargingStatus
from sdk.service import Plugin

gps_token = osd.Token(key="gps", text=None, weight=osd.WEIGHT_GPS)

lbs_token = osd.Token(key="lbs", text=None, weight=osd.WEIGHT_LBS)

# Interval between location polls (GPS + LBS) in the monitor loop, seconds.
LOCATION_POLL_INTERVAL = 10

# Interval between modem-info polls (model, operator, signal, access tech) that
# keep the dashboard tile's cache warm, seconds.
MODEM_INFO_POLL_INTERVAL = 15


class ModemPlugin(Plugin):
  modem: Modem = None
  sms_manager: SmsManager = None
  _gps_monitor_started = False
  _gps_location = None
  _lbs_location = None
  _modem_info = None
  _is_charging = "--"
  _bat_level = "--"
  _cpu_temp = "--"
  _gps_tracker: GpsTracker = None
  _start_check_sms_time = -1.0
  _received_sms = False
  _command_plugin_map: dict[str, str]
  _command_cancel_map: dict[str, set[str]]
  _allowed_phones: list[str]

  def __init__(self, id, name, runner):
    super().__init__(id, name, runner)
    self._command_plugin_map = {}
    self._command_cancel_map = {}
    self._allowed_phones = []

  async def start(self):
    await super().start()
    self._sweep_empty_gps_tracks()
    asyncio.create_task(self._start_lifecycle_loop())
    asyncio.create_task(self._check_files_loop())
    asyncio.create_task(self._start_check_sms_loop())
    asyncio.create_task(self._start_modem_info_loop())

  def init_modem(self, modem: Modem):
    self.modem = modem

  def init_sms_manager(self, sms_manager: SmsManager):
    self.sms_manager = sms_manager

  def init_command_plugin_map(self, command_plugin_map: dict[str, str]):
    self._command_plugin_map = command_plugin_map

  def init_command_cancel_map(self, command_cancel_map: dict[str, set[str]]):
    self._command_cancel_map = command_cancel_map

  def init_allowed_phones(self, phones: list[str]):
    self._allowed_phones = phones

  def get_waiting_first_sms_time(self) -> int:
    """
    :return: "-1" if sms already readed or function not suppoted at all
    :rtype: int
    """
    if self._received_sms:
      return -1

    if self._start_check_sms_time < 0:
      return -1

    return int(time.time() - self._start_check_sms_time)

  @property
  def gps_location(self) -> dict | None:
    """Last GPS location cached by the background monitor (or None)."""
    return self._gps_location

  @property
  def lbs_location(self) -> dict | None:
    """Last LBS location cached by the background monitor (or None)."""
    return self._lbs_location

  @property
  def modem_info(self) -> dict | None:
    """Last modem info cached by the background poller (None until first poll)."""
    return self._modem_info

  async def stop(self):
    self._close_gps_tracker()
    await super().stop()

    # self._revert_annotation()

  def _close_gps_tracker(self):
    """Close the active track, dropping the file if no point ever made it in.

    Nothing is journaled here: a track is only announced once it holds a point (see
    _register_gps_track), so an empty one has never been advertised. That matters
    because stop() runs while the service is going down — the bus and the journal
    server live in vrg-core, which systemd may have stopped already, so a record
    written at this point is likely to be lost.
    """
    if not self._gps_tracker:
      return

    track_file_name = os.path.basename(self._gps_tracker.file_path)
    kept = self._gps_tracker.close()
    self._gps_tracker = None

    if not kept:
      self.logger.info(f"gps track {track_file_name} has no points: dropped")
      self.runner.media_manager.remove_file(MediaFileType.GPS, track_file_name)

  async def _register_gps_track(self, track_file_name: str):
    """Announce a track once it actually holds a point.

    Announcing at creation would advertise files that are about to be discarded: a
    parking wake-up opens a track, never gets a fix and deletes it seconds later, yet
    the Trips page would still show a download button for it (the device wakes up every
    few minutes, so a single parking collected over a hundred of them).
    """
    self.runner.media_manager.append_file(MediaFileType.GPS, track_file_name)
    if self.journal_client:
      await self.journal_client.write(
        JournalRecord(type="track_created", data={"filename": track_file_name})
      )

  def _sweep_empty_gps_tracks(self):
    """Delete point-less tracks left behind by a session that died without stopping.

    A power cut can kill the service before stop() runs, leaving the .gpx of a fix-less
    wake-up on disk forever. Such a file was never announced, so removing it at start
    (when no tracker is open yet) is invisible to everything else.
    """
    try:
      for track_file in self.runner.videoreg.gps_path().glob("*.gpx"):
        try:
          if "<trkpt" in track_file.read_text(encoding="utf-8", errors="replace"):
            continue
          track_file.unlink()
          self.logger.info(f"gps track {track_file.name} left empty by a previous session: dropped")
        except OSError as e:
          self.logger.warning(f"could not sweep gps track {track_file.name}: {e}")
    except Exception as e:
      self.logger.error(f"gps track sweep failed: {e}", exc_info=True)

  async def _start_lifecycle_loop(self):
    while self.runner.is_running():
      charging_status = await self.runner.power_supply.get_charging_status_slow_but_safe()

      if charging_status == ChargingStatus.NOT_CHARGING:
        self._close_gps_tracker()
      else:
        if not self.modem.is_enabled():
          is_enabled = await self.modem.enable()
          if not is_enabled:
            await asyncio.sleep(5)
            continue

        if not self._gps_monitor_started:
          asyncio.create_task(self._start_gps_monitor())
          self._gps_monitor_started = True

        # External power is present on a parking wake-up too, so the beacon decides
        # whether this is a trip — same gate the camera applies before recording.
        if not self._gps_tracker and not await self._beacon_blocks_recording():
          track_file_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.gpx")
          self._gps_tracker = GpsTracker(str(self.runner.videoreg.gps_path(track_file_name)))
          self._gps_tracker.start()

      await asyncio.sleep(5)

  async def _beacon_blocks_recording(self) -> bool:
    """Ask the power plugin (another service) whether the BLE beacon currently blocks
    recording. On a parking wake-up external power is present but the in-car beacon is
    absent, so the power plugin treats power as absent and shuts the device down —
    tracking that minute produces nothing but a fix-less .gpx. Fails safe to False
    (track as usual) so a transient bus/api error never costs a real trip its track."""
    try:
      response = await self.api_client.exec("power.get_beacon_state", None)
      if response.is_ok():
        data = response.get_data() or {}
        return bool(data.get("recording_blocked"))
      self.logger.warning(f"power.get_beacon_state error: {response.get_error()}")
    except Exception as e:
      self.logger.debug(f"power.get_beacon_state unavailable: {type(e).__name__}: {e}")
    return False

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
        if i % 6 == 0:  # ~ every minute (6 * 10s)
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
          tracker = self._gps_tracker
          was_empty = not tracker.has_points
          tracker.track(
            float(self._gps_location["latitude"]),
            float(self._gps_location["longitude"]),
            self._gps_location.get("speed"),
          )
          if was_empty and tracker.has_points:
            await self._register_gps_track(os.path.basename(tracker.file_path))

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

        await asyncio.sleep(LOCATION_POLL_INTERVAL)

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

  async def _start_modem_info_loop(self):
    """Keep modem info (model, operator, signal, access tech) warm in a cache.

    Reading it over AT is slow — the port is shared with GPS/SMS and serialised
    by the transport lock — and can lag badly under weak signal. The modem
    dashboard tile reads this cache via ``modem.modem_info`` instead of doing a
    synchronous AT read per request, so a slow read no longer makes the tile
    fall back to a false "disabled" state. Runs regardless of charging state
    (like the SMS loop, which also uses the AT port).
    """
    await asyncio.sleep(1)
    while self.runner.is_running():
      try:
        self._modem_info = await self.sms_manager.get_modem_info()
      except Exception as e:
        self.logger.warning(f"modem info poll error: {e}")
      await asyncio.sleep(MODEM_INFO_POLL_INTERVAL)

  async def _check_files_loop(self):
    await asyncio.sleep(15)
    while self.runner.is_running():
      removed = self.runner.media_manager.remove_old_files(MediaFileType.GPS, max_files=50)
      if removed > 0:
        self.logger.debug(f"removed gps files {removed}")

      await asyncio.sleep(60 * 5)

  # --- SMS -----------------------------------------------------------------

  async def _start_check_sms_loop(self):
    self._start_check_sms_time = time.time()

    await asyncio.sleep(1)

    while self.runner.is_running():
      try:
        sms_list = await self.sms_manager.read_and_delete_sms()
        commands_to_exec: list[tuple[str, str, str]] = []

        while len(sms_list):
          sms = sms_list.pop()

          self.logger.debug(f"{sms.to_dict()}")

          sms_datetime = datetime.fromisoformat(sms.timestamp)
          sms_datetime_str_for_file = sms_datetime.strftime("%Y-%m-%d_%H-%M-%S")
          sms_datetime_str_for_bot = sms_datetime.strftime("%Y-%m-%d %H:%M:%S")

          sms_file_name = f"{sms_datetime_str_for_file}_{sms.number}.json".replace("+", "")
          sms_file_path = self.runner.videoreg.sms_path(sms_file_name)

          with open(sms_file_path, "w") as f:
            json.dump(sms.to_dict(), f, indent=2)
          self.runner.media_manager.invalidate(MediaFileType.SMS)

          if sms.text.startswith("/") and len(sms.text) > 1:
            if sms.number not in self._allowed_phones:
              self.logger.warning(f"command from not allowed number: {sms.number}")
            else:
              inputs = sms.text.split(" ", 1)
              command_name = inputs[0][1:]
              command_args = inputs[1] if len(inputs) > 1 else None

              self.logger.info(f"detected command: name={command_name}, args={command_args}")

              commands_to_exec.append((sms.number, command_name, command_args))
          else:
            bot_response = await self.api_client.exec(
              "bot.send_text",
              {
                "payload": None,
                "text": f"SMS\n\n{sms_datetime_str_for_bot}\n\nFrom: {sms.number}\n\n{sms.text}\n",
              },
            )
            if not bot_response.is_ok():
              self.logger.warning(f"bot.send_text error: {bot_response.get_error()}")

        # Drop a /shutdown that a /no cancels within this same batch (e.g. both queued
        # while the device was offline and read together on reconnect).
        commands_to_exec = apply_command_cancellations(
          commands_to_exec, self._command_cancel_map, lambda command: command[1]
        )

        for sms_number, command_name, command_args in commands_to_exec:
          asyncio.create_task(self._handle_command(sms_number, command_name, command_args))

        self._received_sms = True

      except Exception as e:
        self.logger.error(f"error: {e}")

      await asyncio.sleep(10)

  async def _handle_command(self, sms_number: str, name: str, args: str):
    plugin_name = self._command_plugin_map.get(name)
    if not plugin_name:
      self.logger.warning(f"Unknown command: {name}")
      return
    try:
      await self.api_client.exec(
        f"{plugin_name}.command",
        {
          "command": name,
          "gateway": "sms",
          "payload": {"phone": sms_number},
          "args": args,
        },
      )
    except Exception as e:
      self.logger.error(f"_handle_command error: {e}")
