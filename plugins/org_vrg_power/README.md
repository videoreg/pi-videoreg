# Power management plugin (org_vrg_power)

Manages Raspberry Pi power via PiSugar 3 UPS (Li-Po battery, RTC, software shutdown, wakeup alarm).

Communication with PiSugar is done through the `PiSugar` class from `sdk/pisugar.py`.

## Wakeup modes

The mode defines how the Pi will wake up after shutdown. Set via the `set_wakeup` method, stored in the plugin state. Default: `on-power-restore`.

| Value | Behavior |
|---|---|
| `1m` / `2m` / `10m` / `30m` / `1h` | Wake up after N minutes/hours (PiSugar RTC alarm) |
| `on-power-restore` | Wake up only when external power is restored |
| `disabled` | Do not wake up automatically |

## Shutdown logic on power loss

File: `shutdown.py` — classes `ShutdownLogic` and `PisugarShutdownController`.

When external power is disconnected (`is_charging == -1`), `ShutdownLogic.should_shutdown()` polls the `bot`, `camera`, `sms` plugins via `{plugin}.is_ready_to_die`. Shutdown happens only if all plugins are ready. Retry is allowed no sooner than 30 seconds later.

`PisugarShutdownController.shutdown()` applies the wakeup config to PiSugar before shutdown:
- RTC alarm — for timed modes (`1m`…`1h`)
- wakeup on power restore — always enabled

## How power is actually cut

The plugin only asks the OS to go down; it never arms the PiSugar power cut itself.
Cutting power is owned by three shell components, ordered so that every decision is
made while the system can still read the bus, retry and log:

| Component | When | Role |
|-----------|------|------|
| `vrg-poweroff.service` → `task/service/vrg-poweroff.sh` | `ExecStop`, after all other services have stopped | Reads charging status and the wakeup alarm, decides power cut vs reboot, arms the cut and verifies it, publishes the decision to `/run/vrg/pisugar-poweroff` |
| `/lib/systemd/system-shutdown/shutdown-pisugar.sh` (from `tools/install/`) | Last shutdown phase | Fallback. Consumes the published decision; one control read of `REG_POWER` to catch power that appeared during the shutdown, then either `reboot -f` or the arming writes |
| `vrg-pisugar-cancel-powercut.service` | Early boot | Cancels a cut that was armed but never carried out, publishes `/run/vrg/pisugar-power-byte`, restores charging-enabled and wakeup-on-power-restore if they were cleared |

On external power with a wakeup alarm still ahead, the poweroff is turned into a
reboot so the device stays online. That check is made as late as possible because
external power can appear while the services are still stopping.
