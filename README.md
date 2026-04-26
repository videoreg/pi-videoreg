# Pi-Videoreg

[Videoreg.org](https://videoreg.org) — an open project exploring DIY dashcam builds for cars with remote access.

**Pi-Videoreg** — a Raspberry Pi-based implementation.

## Features
- Video recording while driving
- Parking mode (periodic photos)
- Telegram Bot
- Web UI
- WireGuard
- USB-modem support for remote access over mobile network, GPS, SMS

## Hardware

- Raspberry Pi Zero 2W
- OV5647 camera
- PiSugar 3 UPS
- 4G USB modem (e.g. SIM7600)

## Installation

Videoreg is a complex system that requires OS configuration and a custom build of [rpicam-apps](https://github.com/videoreg/rpicam-apps). The only supported installation method at this time is using a pre-built `.img` image based on Raspberry Pi OS.

Download the `.img` image here: https://github.com/videoreg/pi-gen.

Flash the image using the official Raspberry Pi Imager:

1. Select "Raspberry Pi Zero 2W" or "No filtering"
2. At the bottom of the list, choose to install from a local `.img` file

## First Boot

By default, the device creates a WiFi network named `videoreg` with password `12345678`.

After connecting, open https://10.0.0.1:8443 in your browser (the browser may warn about an untrusted certificate — this is expected).

Web UI login credentials: username `admin`, password `videoreg`.

>[!WARNING]
>Change the user password and WiFi password immediately!

## Running with Docker

To explore the system or develop locally, run `docker compose up --build` (subsequently just `docker compose up`).

## License

This project is licensed under the [GNU Affero General Public License v3.0](LICENSE).
