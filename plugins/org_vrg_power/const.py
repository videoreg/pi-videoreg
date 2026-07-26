STATE_KEY_WAKEUP = "wakeup"
STATE_KEY_LAST_SHUTDOWN_CONFIG = "last_shutdown_config"
STATE_KEY_CHARGING_PROTECTION = "charging_protection"
STATE_KEY_BLE_ENABLED = "ble_enabled"
STATE_KEY_BLE_TARGET = "ble_target"  # {"mac": "AA:BB:...", "name": "..."} or None
SHUTDOWN_DELAY_SEC = 5

# BLE beacon external-power detection.
# A beacon is considered "present" if it was last seen within this many seconds.
# The same window doubles as the boot grace: the monitor seeds last_seen at start,
# so the beacon reads as present for the first BLE_PRESENCE_WINDOW seconds while the
# scanner discovers it.
BLE_PRESENCE_WINDOW = 15

# Marker file the plugin drops in its own data dir immediately before a shutdown
# that must cut PiSugar power even though external power is still present (the BLE
# beacon vanished, so only the RTC alarm brings the device back). The PiSugar
# poweroff scripts read it and, when fresh, arm the cut instead of rebooting.
FORCE_POWERCUT_MARKER = "force-powercut"
