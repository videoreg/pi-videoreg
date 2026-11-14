# org_vrg_rearcam — rear-view WiFi cameras

Pairs additional cameras (e.g. a rear-view camera) with the device and serves them to
the rest of the system. The wire protocol is specified in the `rear-camera-protocol`
project (sibling checkout `../rear-camera-protocol`, README.md); the reference camera
firmware lives in `esp32-rear-camera` (`../esp32-rear-camera`).

Runs inside the `vrg-camera` service.

## How it works

1. **Provisioning (BLE)**. An unconfigured camera advertises itself as `ESP32-XXXXXX`.
   The settings UI scans for it (`rearcam.scan_ble`), then `rearcam.provision` performs
   the encrypted handshake (ephemeral X25519, AES-256-GCM frames) and hands the camera
   the WiFi credentials of the network the hub itself is on — obtained from
   `net.wifi_credentials` — plus the hub URL `http://<hub-ip>:8531` and a per-camera
   access token (`secrets.token_hex(32)`, regenerated on every provisioning, i.e.
   token rotation).
2. **Registration (heartbeat)**. After connecting, the camera POSTs
   `{device_id, ip, fw}` to `{hub}/api/register` with the
   `Authorization: Bearer <token>` header. This plugin runs that tiny HTTP
   server (`register_server.py`, port 8531); heartbeats with a missing or
   mismatched token — including from unknown cameras — are rejected with 401
   (no auto-registration; the camera is expected to re-provision over BLE).
   The same server exposes `GET /api/time` (`{epoch, utc_offset_s}`), also
   token-protected — the camera syncs its clock from it on every WiFi
   (re)connect and every 6 h afterwards.
3. **Runtime**. A background poller checks each camera's `GET /health` every 30 s and
   maintains the online flag; heartbeats refresh `ip`/`firmware`/`last_seen`.
   All hub→camera calls send the camera's token in the `Authorization` header
   (`CameraClient`).
4. **Use**. `/photo N` (N ≥ 2) fetches a JPEG via `rearcam.get_photo`; the Web UI lists
   cameras and their state. Additionally each paired camera gets its own bot menu
   command `/photo_N` (see "Gateway commands" below).

## State

`plugin.state["devices"]`: `device_id` (STA MAC, 12 lowercase hex chars) →
`{number, name, ble_mac, ip, paired_at, last_seen, firmware, access_token, frame?}`
(`frame` — the frame size chosen via `set_config`; `access_token` — the bearer
token issued at provisioning, rotated on re-provisioning; never exposed via the
plugin's API methods). Numbers start at 2 —
camera #1 is the built-in main camera. The online flag is runtime-only (not persisted).

## API methods

| Method | Args | Returns |
|--------|------|---------|
| `rearcam.list_devices` | — | `{devices: [...]}` |
| `rearcam.scan_ble` | — | `{devices: [{mac, name, rssi}]}` (~8 s) |
| `rearcam.provision` | `{mac, name?}` | `{device: {...}}` (up to ~40 s) |
| `rearcam.forget` | `{number}` | `{devices: [...]}` |
| `rearcam.get_photo` | `{number}` | `{path: <local jpeg>}` |
| `rearcam.get_status` | `{number}` | camera health + status merged |
| `rearcam.get_config` | `{number}` | `{frame: {width,height,fps}, frames: [...], saved_frame?}` |
| `rearcam.set_config` | `{number, width, height}` | `{frame: {width,height,fps}}` (persisted on the camera) |
| `rearcam.get_menu_commands` | — | `{commands: [{name, title, weigh}]}` |

## Gateway commands

For every paired camera the plugin registers a `/photo_N` gateway command
(`commands/photo.py`, wired into `rearcam.command` via the plugin-owned
`gateway_commands` dict kept in sync by `sync_gateway_commands()`). The bot
discovers the entries through the `bot.menu_commands_method` manifest key: it
calls `rearcam.get_menu_commands` when (re)building its command list
(`bot.reload_commands`), which this plugin triggers after pairing, forgetting,
adoption of a pending camera record and on startup.

Provisioning errors are machine-readable strings: `bad_password`, `ssid_not_found`,
`timeout`, `bleak_not_available`, `no_wifi_network`.

## HTTP endpoints (via `http.api` in manifest.yaml)

`GET /api/rearcam/devices`, `GET /api/rearcam/scan`, `POST /api/rearcam/provision`,
`POST /api/rearcam/forget`, `GET /api/rearcam/status?number=N`,
`GET /api/rearcam/config?number=N`, `POST /api/rearcam/config` (`{number, width, height}`).
