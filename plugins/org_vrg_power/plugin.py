import asyncio
import subprocess
import time
from datetime import UTC, datetime, timedelta

import plugins.org_vrg_power.const as const
from plugins.org_vrg_power.ble_beacon import BleBeaconMonitor
from plugins.org_vrg_power.power_controls import PowerControls
from plugins.org_vrg_power.shutdown import ShutdownController, ShutdownLogic
from sdk.helper import stream_subprocess
from sdk.journal import JournalRecord
from sdk.keep_alive import KeepAlive
from sdk.power import ChargingStatus
from sdk.power.pisugar import PiSugar
from sdk.service import Plugin


class PowerPlugin(Plugin):
  _time_start: int
  _last_charging_status = None
  _shutdown_logic: ShutdownLogic
  _shutdown_controller: ShutdownController
  _power_controls: PowerControls
  keep_alive: KeepAlive
  ble_monitor: BleBeaconMonitor = None

  def __init__(self, id, name, runner):
    super().__init__(id, name, runner)
    self._time_start = time.time()
    self.keep_alive = KeepAlive()

  def get_uptime(self):
    return int(time.time() - self._time_start)

  async def start(self):
    await super().start()
    # Drop any stale beacon marker from a previous session so it can never force a
    # power cut on an unrelated shutdown (freshness is also checked by the scripts).
    self._clear_force_powercut_marker()
    alarm_time = await self._is_alarm_wakeup_pending()
    if alarm_time:
      self.logger.info(f"alarm wakeup pending: {alarm_time.isoformat()}")
      self.keep_alive.have_to_wait("initial_power", 60)
    ps = self.runner.power_supply
    if isinstance(ps, PiSugar):
      asyncio.create_task(ps.set_alarm_wakeup_enabled(False))
      asyncio.create_task(ps.set_wakeup_on_power_restore(True))
      asyncio.create_task(self._apply_charging_protection())
    if self.ble_monitor and self.ble_monitor.is_active():
      # Give the scanner ~1 presence window to discover the beacon before the
      # shutdown loop is allowed to treat its absence as a power cut. This is the
      # boot grace enforced through the is_ready_to_die engine (keep_alive reason).
      self.keep_alive.have_to_wait("ble_initial", const.BLE_PRESENCE_WINDOW)
      asyncio.create_task(self.ble_monitor.start())
    elif self.ble_monitor and self.state.get(const.STATE_KEY_BLE_TARGET, None):
      # Booted with a beacon configured but the feature inactive (disabled or
      # unsupported). No beacon_found/lost events are emitted while inactive, so
      # this marker is the only signal the Trips page has to end a beacon-absent
      # parking once the feature was turned off.
      await self.journal_beacon_active(False)
    asyncio.create_task(self._start_check_charging_loop())

  async def stop(self):
    if self.ble_monitor:
      await self.ble_monitor.stop()
    await super().stop()

  def init_ble_monitor(self, ble_monitor: BleBeaconMonitor):
    self.ble_monitor = ble_monitor

  def effective_charging_status(self, charging_status: ChargingStatus) -> ChargingStatus:
    """Fold BLE beacon presence into the charging status.

    Power is present only if PiSugar reports charging AND (the beacon feature is
    inactive OR the beacon has not been gone past its grace period). A beacon lost
    for longer than the grace therefore looks exactly like a NOT_CHARGING reading and
    flows through the existing shutdown logic unchanged. A brief drop-out is tolerated
    (is_lost stays False until the grace elapses), so the device keeps running.
    """
    if (
      charging_status == ChargingStatus.CHARGING
      and self.ble_monitor
      and self.ble_monitor.is_active()
      and self.ble_monitor.is_lost()
    ):
      return ChargingStatus.NOT_CHARGING
    return charging_status

  async def on_beacon_presence_change(self, present: bool):
    """React to a live beacon present<->absent transition: log and journal it.

    This fires on the short presence window (~15s), independent of the longer grace
    that governs shutdown, so the journal records the moment the signal actually
    dropped or came back — useful on the Trips page.
    """
    self.logger.info(f"BLE beacon {'appeared' if present else 'disappeared'}")
    if self.journal_client:
      event_type = "beacon_found" if present else "beacon_lost"
      await self.journal_client.write(JournalRecord(type=event_type, data=None))

  async def journal_beacon_active(self, active: bool):
    """Journal a beacon-gating on/off transition (feature enabled/disabled).

    The Trips page uses this to know when beacon presence governs trip/parking
    detection: with the feature off, no beacon_found/lost events are emitted, so
    this is the only marker that lets it end a beacon-absent parking.
    """
    if self.journal_client:
      event_type = "beacon_enabled" if active else "beacon_disabled"
      await self.journal_client.write(JournalRecord(type=event_type, data=None))

  async def _apply_charging_protection(self):
    ps = self.runner.power_supply
    if not isinstance(ps, PiSugar):
      return
    enabled = bool(self.state.get(const.STATE_KEY_CHARGING_PROTECTION, True))
    try:
      ok = await ps.set_charging_protection(enabled)
      if ok:
        self.logger.info(f"charging protection applied: {enabled}")
      else:
        self.logger.warning(f"PiSugar rejected charging protection={enabled}")
    except Exception as e:
      self.logger.error(f"failed to apply charging protection: {e}", exc_info=True)

  async def delayed_shutdown(self, reason: str, force_powercut: bool = False):
    self.logger.info(f"shutdown (reason={reason})")
    # Record why we are powering off before the teardown begins. Awaited (not
    # fire-and-forget) so the record reaches the journal — which lives in this same
    # vrg-core service — before ps.shutdown() triggers systemd stop.
    if self.journal_client:
      try:
        await self.journal_client.write(JournalRecord(type="shutdown", data={"reason": reason}))
      except Exception as e:
        self.logger.warning(f"failed to journal shutdown reason: {e}")
    ps = self.runner.power_supply
    if isinstance(ps, PiSugar):
      if force_powercut:
        self._write_force_powercut_marker()
      await ps.shutdown()
    else:
      subprocess.run(["sudo", "shutdown", "now"])

  def _force_powercut_marker_path(self):
    return self.runner.videoreg.plugin_private_path(self.id, const.FORCE_POWERCUT_MARKER)

  def _write_force_powercut_marker(self):
    # Tell the PiSugar poweroff scripts (task/service/vrg-poweroff.sh and the
    # shutdown hook) to cut power even though PiSugar still reports external power:
    # the beacon is gone and only the RTC alarm should bring the device back.
    # Without this they turn a charging+alarm poweroff into a reboot. The scripts
    # honour the marker only when fresh, so a leftover cannot force a cut later.
    try:
      path = self._force_powercut_marker_path()
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_text(f"{int(time.time())}\n")
      self.logger.info(f"force-powercut marker written: {path}")
    except Exception as e:
      self.logger.error(f"failed to write force-powercut marker: {e}", exc_info=True)

  def _clear_force_powercut_marker(self):
    try:
      self._force_powercut_marker_path().unlink(missing_ok=True)
    except Exception as e:
      self.logger.warning(f"failed to clear force-powercut marker: {e}")

  async def delayed_reboot(self):
    self.logger.info("reboot")
    subprocess.run(["sudo", "shutdown", "-r", "now"])

  def init_shutdown(
    self, shutdown_logic: ShutdownLogic, shutdown_controller: ShutdownController
  ):
    self._shutdown_logic = shutdown_logic
    self._shutdown_controller = shutdown_controller

  def init_power_controls(self, power_controls: PowerControls):
    self._power_controls = power_controls

  async def _is_alarm_wakeup_pending(self) -> datetime | None:
    ps = self.runner.power_supply
    if not isinstance(ps, PiSugar):
      return None
    try:
      if not await ps.get_alarm_wakeup_enabled():
        return None
      alarm_time_str = await ps.get_alarm_wakeup_time()
      if not alarm_time_str:
        return None
      alarm_time = datetime.fromisoformat(alarm_time_str)
      now = datetime.now(alarm_time.tzinfo or UTC)
      woke_up_by_alarm = alarm_time <= now or (alarm_time - now) <= timedelta(minutes=5)
      return alarm_time if woke_up_by_alarm else None
    except Exception:
      return None

  async def _start_check_charging_loop(self):
    _initial_captured = False
    while self.runner.is_running():
      raw_charging_status = await self.runner.power_supply.get_charging_status_slow_but_safe()
      charging_status = self.effective_charging_status(raw_charging_status)

      if not _initial_captured:
        _initial_captured = True
        if charging_status == ChargingStatus.CHARGING:
          self.keep_alive.have_to_wait("initial_power", 60)

      # be careful: don't use continue here
      if charging_status != self._last_charging_status:
        if charging_status == ChargingStatus.NOT_CHARGING:
          self.logger.info("Charging is off: will stop vrg-charging.target")
          await self._power_controls.stop_charging_target()
        elif charging_status == ChargingStatus.CHARGING:
          self.logger.info("Charging is on: will start vrg-charging.target")
          await self._power_controls.start_charging_target()

      await asyncio.sleep(5)

      # shutdown after delay to prevent immediately shutdown

      if self._shutdown_logic and self._shutdown_controller:
        if charging_status != ChargingStatus.UNKNOWN:
          should_shutdown = await self._shutdown_logic.should_shutdown(charging_status)
          if should_shutdown:
            # Beacon lost while PiSugar still reports external power: the shutdown must
            # actually cut power (force_powercut) rather than reboot, and rely on the
            # RTC alarm to wake. Wake-on-power-restore stays enabled (as on develop) so
            # that if external power really does drop and return during the sleep, the
            # device wakes early instead of waiting out the alarm.
            external_power_present = (
              raw_charging_status == ChargingStatus.CHARGING
              and charging_status == ChargingStatus.NOT_CHARGING
            )
            shutdown_config = await self._shutdown_controller.shutdown("stop_charging")
            if not shutdown_config:
              self._last_charging_status = charging_status
              continue

            self.state.save({const.STATE_KEY_LAST_SHUTDOWN_CONFIG: shutdown_config.to_json()})

            # external_power_present here means the beacon vanished while PiSugar still
            # sees power (force-powercut); otherwise external power was actually lost.
            reason = (
              const.SHUTDOWN_REASON_BEACON_LOST
              if external_power_present
              else const.SHUTDOWN_REASON_POWER_LOSS
            )
            asyncio.create_task(
              self.delayed_shutdown(reason, force_powercut=external_power_present)
            )
            break

      self._last_charging_status = charging_status
