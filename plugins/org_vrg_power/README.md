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
