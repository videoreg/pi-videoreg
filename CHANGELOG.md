# Changelog

Notable changes per released version. Versions before 0.1.2 are not documented here —
see the git history for them.

## 0.1.3 — 2026-08-28

### Power and shutdown

- The wake-up alarm is disarmed below 15% battery, leaving only wake-on-power-restore.
  Every alarm wake costs a full boot for a few dozen seconds of work, so at `wakeup=2m`
  on battery the device cycles about twenty times an hour and flattens itself in roughly
  seven hours. The threshold is skipped while external power is present, where the alarm
  is the only way back.
- The shutdown hook can no longer withdraw a reboot decision. It used to re-read the
  PiSugar power register once and act on that single sample; a disagreeing sample made it
  arm a power cut that could not fire, so Linux halted with the rails still live and
  nothing power-cycled the board. Charging status is now sampled three times and the
  samples may only add power, never retract it.
- An unreadable I2C answer is no longer treated as a zero byte.

## 0.1.2 — 2026-08-09

### BLE beacon

- Optional external-power detection via a BLE beacon: the car beacon is treated as
  the "engine is on" signal in addition to the PiSugar power state.
- Camera recording is gated on beacon presence — no recording while the beacon is away.
- Beacon-loss grace period before acting on a disappearance; the grace is skipped until
  the beacon has been seen at least once.
- Beacon events (found / lost, feature enabled / disabled) are written to the journal.
- `vrg-install`: onboard Bluetooth is unblocked and powered on at boot via a
  `bluetooth.service` drop-in, so the setup survives the pi-gen build chroot.

### Power and shutdown

- PiSugar poweroff refactoring: the power cut is armed just before the last shutdown
  phase and its window is shrunk to the teardown minimum.
- `vrg-poweroff` `ExecStop` and `cancel-powercut` run as root, so shutdown-mode
  detection works and the log no longer reports a cancel that did not happen.
- Shutdown is cancelable: the new `/no` command cancels a `/shutdown` from the same batch.
- On a beacon-loss shutdown the PiSugar power cut is forced even when external power is
  present; wake-on-power-restore stays always on.

### Trips and journal

- Trips and parkings are derived from the effective power + beacon state.
- The shutdown reason (forced / power loss / beacon lost) is journaled and shown on the
  Trips page.
- Trips block events are merged into a single chronological log; beacon events are hidden
  in the collapsed section together with photos.
- Parking wake-ups are detected even without a `beacon_lost` event.

### GPS

- GPS tracks that never received a point are dropped instead of being kept as empty files.
- A track is announced only once it holds at least one point.

### SMS and bot

- `/status` works over SMS; the summary includes bot health.
- Long outgoing SMS are segmented into concatenated parts.
- SMS status reporting fixes (PDU handling, bot/botvk `get_status_text`).

### Network

- `modemmanager` is declared explicitly by `vrg-install` — base Raspberry Pi OS images no
  longer ship it. A missing `mmcli` now degrades to the AT fallback instead of erroring.
- The modem interface is probed among `wwan0` / `usb0` / `ppp0` instead of assuming
  `wwan0`, which fixes the empty Modem line and the IP fallback in RNDIS/ECM mode.
- The modem IP is excluded from HTTPS certificate SANs.
- The date & time settings page warns that changing the clock disrupts HTTPS.

### Logging

- Services and plugins log to stdout only; systemd collects them into the journal.
- Routine lines moved to debug level.
- A persisting modem failure is logged once instead of on every retry.

### Web UI

- "Rebuild components" also rebuilds the merged manifest, so menu / component / dashboard
  changes apply without a service restart. The automatic page reload is replaced with a
  hint to reload with a cache reset.
