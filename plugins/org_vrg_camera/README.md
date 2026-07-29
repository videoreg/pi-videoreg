# Plugin camera (org_vrg_camera)

## What it does

- Continuous video recording in H.264 (2-minute segments) via `rpicam-vid`
- Photo capture: raw photo (`rpicam-jpeg`) or screenshot from the RTSP stream
- OSD overlay with metadata (time, GPS, temperature, battery) on top of the video
- Automatic management: stops recording on overheating (>65°C) or when running on battery, starts when power is available and temperature is normal. When the BLE parking beacon feature is active, external power counts as a reason to record only once the beacon is confirmed present — on a parking wake-up (power present, beacon absent) the camera takes a single wakeup photo and does not record, then the power plugin shuts the device down (via `power.get_beacon_state`)
- File rotation: keeps at most 400 H.264 and 400 JPEG files, deletes the oldest
- Live streaming to Mediamtx HLS

## Key files

- `hw.py` — `CameraHardware`: camera operation queue, subprocess start/stop
- `osd.py` — OSD token management (writes to `~/.videoreg/camera-annotate.txt`)
- `task/camera/start_video.sh` — launches `rpicam-vid | ffmpeg` (segmentation + RTSP)
- `task/camera/take_photo.sh` — raw photo via `rpicam-jpeg`
- `task/camera/take_screenshot.sh` — frame screenshot from RTSP via ffmpeg

## OSD system

Tokens with weights are sorted and rendered left to right:
- weight 0: header "VIDEOREG.ORG"
- weight 10: time (formatted by rpicam automatically)
- weight 20-60: GPS, location, charging, battery, CPU temperature

Other services write tokens via the event bus (channel "osd").
