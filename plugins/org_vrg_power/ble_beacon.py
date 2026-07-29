import asyncio
import time
from logging import Logger

import plugins.org_vrg_power.const as const

try:
  from bleak import BleakScanner

  BLEAK_AVAILABLE = True
except Exception:  # pragma: no cover - bleak/BlueZ may be absent (e.g. dev host)
  BleakScanner = None
  BLEAK_AVAILABLE = False


class BleBeaconMonitor:
  """Tracks presence of a configured BLE beacon.

  A continuous scanner records the last time the target MAC was seen. The beacon is
  considered "present" if seen within BLE_PRESENCE_WINDOW seconds. Until the target has
  been heard even once in a session (_ever_seen), only the short discovery window
  applies, so a boot/wake that finds no beacon shuts back down quickly; the longer
  grace period only kicks in after a real sighting has been lost. The scanner also
  caches every discovered device so the settings UI can offer a pick-list.
  """

  def __init__(self, plugin, logger: Logger):
    self._plugin = plugin
    self._logger = logger
    self._scanner = None
    self._running = False
    self._last_seen = 0.0
    self._ever_seen = False  # has the target been heard at all in this session?
    self._boot_time = 0.0  # when the current scan session started
    self._seen: dict[str, dict] = {}  # mac -> {"name", "rssi", "last_seen"}
    self._lock = asyncio.Lock()
    self._present = False  # last known presence state, for transition detection
    self._presence_task: asyncio.Task | None = None

  # ---- config helpers ----

  def _enabled(self) -> bool:
    return bool(self._plugin.state.get(const.STATE_KEY_BLE_ENABLED, False))

  def target(self) -> dict | None:
    t = self._plugin.state.get(const.STATE_KEY_BLE_TARGET, None)
    return t if isinstance(t, dict) else None

  def target_mac(self) -> str | None:
    t = self.target()
    mac = t.get("mac") if t else None
    return mac.upper() if isinstance(mac, str) else None

  def is_supported(self) -> bool:
    return BLEAK_AVAILABLE

  def is_active(self) -> bool:
    """Feature drives the shutdown decision only when supported, enabled and targeted."""
    return BLEAK_AVAILABLE and self._enabled() and bool(self.target_mac())

  def grace_minutes(self) -> int:
    raw = self._plugin.state.get(const.STATE_KEY_BLE_GRACE_MINUTES, const.BLE_GRACE_MINUTES_DEFAULT)
    try:
      value = int(raw)
    except (TypeError, ValueError):
      value = const.BLE_GRACE_MINUTES_DEFAULT
    return max(const.BLE_GRACE_MINUTES_MIN, min(const.BLE_GRACE_MINUTES_MAX, value))

  def _grace_seconds(self) -> float:
    return self.grace_minutes() * 60

  # ---- presence ----

  def is_present(self) -> bool:
    """Live presence over the short window — drives the UI indicator and journal."""
    if not self.target_mac():
      return True  # nothing to track — never force a shutdown
    if not self._last_seen:
      return False  # never heard yet in this session
    return (time.time() - self._last_seen) <= const.BLE_PRESENCE_WINDOW

  def is_lost(self) -> bool:
    """True once the beacon has been absent long enough to count as a power cut.

    Before the beacon has ever been heard in this session, only the short discovery
    window applies: a boot/wake that finds no beacon is treated as lost quickly rather
    than waiting out the full grace. After a real sighting, the configurable grace must
    fully elapse since it was last seen — any sighting resets that timer, so a brief
    drop-out during a trip passes without shutting the device down.
    """
    if not self.target_mac():
      return False
    now = time.time()
    if not self._ever_seen:
      return (now - self._boot_time) > const.BLE_PRESENCE_WINDOW
    return (now - self._last_seen) > self._grace_seconds()

  def last_seen_seconds(self) -> int | None:
    if not self._last_seen:
      return None
    return int(time.time() - self._last_seen)

  # ---- detection ----

  def _on_detection(self, device, adv):
    mac = (getattr(device, "address", "") or "").upper()
    if not mac:
      return
    name = (getattr(adv, "local_name", None) or getattr(device, "name", None)) if adv else None
    rssi = getattr(adv, "rssi", None) if adv else None
    now = time.time()
    self._seen[mac] = {"name": name, "rssi": rssi, "last_seen": now}
    if mac == self.target_mac():
      self._last_seen = now
      self._ever_seen = True

  # ---- lifecycle ----

  async def start(self):
    if not BLEAK_AVAILABLE:
      self._logger.warning("bleak not available; BLE beacon monitor disabled")
      return
    async with self._lock:
      if self._running:
        return
      # Fresh session: the beacon has not been heard yet, so presence starts False and
      # is_lost() applies only the short discovery window until the first real sighting.
      self._boot_time = time.time()
      self._last_seen = 0.0
      self._ever_seen = False
      self._present = False
      try:
        self._scanner = BleakScanner(detection_callback=self._on_detection)
        await self._scanner.start()
        self._running = True
        self._presence_task = asyncio.create_task(self._presence_loop())
        self._logger.info(f"BLE beacon monitor started; target={self.target_mac()}")
      except Exception as e:
        self._scanner = None
        self._running = False
        self._logger.error(f"failed to start BLE scanner: {e}", exc_info=True)

  async def stop(self):
    async with self._lock:
      scanner = self._scanner
      task = self._presence_task
      self._scanner = None
      self._presence_task = None
      self._running = False
      if task:
        task.cancel()
      if not scanner:
        return
      try:
        await scanner.stop()
        self._logger.info("BLE beacon monitor stopped")
      except Exception as e:
        self._logger.warning(f"error stopping BLE scanner: {e}")

  async def _presence_loop(self):
    """Watch for present<->absent transitions and report them (journal + log).

    Absence is a timeout on last_seen, so it can only be noticed by polling. The loop
    reports the live (short-window) presence; the longer grace period governs shutdown
    separately via is_lost().
    """
    try:
      while self._running:
        await asyncio.sleep(const.BLE_PRESENCE_TICK)
        present = self.is_present()
        if present == self._present:
          continue
        self._present = present
        try:
          await self._plugin.on_beacon_presence_change(present)
        except Exception as e:
          self._logger.error(f"beacon presence change handler failed: {e}", exc_info=True)
    except asyncio.CancelledError:
      pass

  async def restart(self):
    """Re-apply config: stop, then start again if the feature is now active."""
    await self.stop()
    if self.is_active():
      await self.start()

  # ---- one-shot scan for the UI ----

  async def scan(self, duration: float = 6.0) -> list[dict]:
    """Return devices seen during a short scan as [{mac, name, rssi}], strongest first.

    Reuses the continuous scanner when it is already running (to avoid two scanners on
    one adapter); otherwise spins up a temporary scanner for `duration` seconds.
    """
    if not BLEAK_AVAILABLE:
      raise RuntimeError("bleak_not_available")

    if self._running:
      cutoff = time.time()
      await asyncio.sleep(duration)
      devices = [
        {"mac": mac, "name": v.get("name"), "rssi": v.get("rssi")}
        for mac, v in self._seen.items()
        if v.get("last_seen", 0) >= cutoff
      ]
    else:
      found: dict[str, dict] = {}

      def cb(device, adv):
        mac = (getattr(device, "address", "") or "").upper()
        if not mac:
          return
        name = (getattr(adv, "local_name", None) or getattr(device, "name", None)) if adv else None
        found[mac] = {"mac": mac, "name": name, "rssi": getattr(adv, "rssi", None) if adv else None}

      scanner = BleakScanner(detection_callback=cb)
      await scanner.start()
      try:
        await asyncio.sleep(duration)
      finally:
        await scanner.stop()
      devices = list(found.values())

    devices.sort(key=lambda d: (d.get("rssi") is None, -(d.get("rssi") or 0)))
    return devices
