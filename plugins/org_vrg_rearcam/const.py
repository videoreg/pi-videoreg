# Rear camera (rearcam) plugin constants.
# The wire protocol is specified in the rear-camera-protocol repository.

STATE_KEY_DEVICES = "devices"  # device_id -> {number, name, ble_mac, ip, paired_at, last_seen, firmware}

# Hub-side registration server: cameras POST {hub}/api/register after (re)connecting.
REGISTER_PORT = 8531
REGISTER_PATH = "/api/register"

# BLE provisioning GATT service (128-bit UUIDs, see the protocol spec).
BLE_SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
BLE_CHR_PUBKEY_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"  # read+write, 32-byte X25519 public keys
BLE_CHR_CREDS_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a9"  # write, encrypted credentials frame
BLE_CHR_RESULT_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26aa"  # notify, encrypted result frame

BLE_NAME_PREFIX = "ESP32-"
BLE_SCAN_SECONDS = 8.0
BLE_PROVISION_TIMEOUT = 60.0  # device-side WiFi connect may take up to ~30 s

HEALTH_POLL_SECONDS = 30
HTTP_TIMEOUT_SECONDS = 10
# A 1080p frame at JPEG quality 95 is ~1.2 MB; over a weak WiFi link the
# transfer from the camera can take ~15-20 s.
PHOTO_TIMEOUT_SECONDS = 45

FIRST_CAMERA_NUMBER = 2  # camera #1 is the built-in main camera

# Bot menu order for the dynamic /photo_N entries: just below /photo (100),
# above /video (90).
MENU_COMMAND_WEIGH = 95
