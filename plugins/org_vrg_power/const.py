STATE_KEY_WAKEUP = "wakeup"
STATE_KEY_LAST_SHUTDOWN_CONFIG = "last_shutdown_config"
STATE_KEY_CHARGING_PROTECTION = "charging_protection"
STATE_KEY_BLE_ENABLED = "ble_enabled"
STATE_KEY_BLE_TARGET = "ble_target"  # {"mac": "AA:BB:...", "name": "..."} or None
STATE_KEY_BLE_GRACE_MINUTES = "ble_grace_minutes"  # grace before a lost beacon shuts down
SHUTDOWN_DELAY_SEC = 5

# BLE beacon external-power detection.
# A beacon is considered "present" if it was last seen within this many seconds.
# This short window drives the live UI indicator and the beacon_found / beacon_lost
# journal events. It also bounds boot discovery: until the beacon has been seen even
# once in a session, it is treated as lost after this many seconds — so a wake that
# finds no beacon shuts back down quickly instead of waiting out the full grace. The
# beacon must therefore make itself heard within this window (a few BLE adverts).
BLE_PRESENCE_WINDOW = 15

# How often the monitor re-evaluates presence to detect present<->absent transitions
# (for the journal events). Seconds.
BLE_PRESENCE_TICK = 3

# Beacon-loss grace period. A momentary drop-out (weak signal, a passing obstruction)
# should not power the device off: once the beacon signal is lost the device keeps
# running in normal mode for this many minutes, and only shuts down if the beacon is
# still gone when the grace elapses. If the beacon reappears the timer resets. The
# value is user-configurable on the Beacon settings tab and clamped to [MIN, MAX].
BLE_GRACE_MINUTES_DEFAULT = 10
BLE_GRACE_MINUTES_MIN = 1
BLE_GRACE_MINUTES_MAX = 120

# Marker file the plugin drops in its own data dir immediately before a shutdown
# that must cut PiSugar power even though external power is still present (the BLE
# beacon vanished, so only the RTC alarm brings the device back). The PiSugar
# poweroff scripts read it and, when fresh, arm the cut instead of rebooting.
FORCE_POWERCUT_MARKER = "force-powercut"
