# Pi-Videoreg

🇬🇧 English | [🇷🇺 Русский](README.ru.md)

[Videoreg.org](https://videoreg.org) — an open project exploring DIY dashcam builds for cars with remote access.

**Pi-Videoreg** — a Raspberry Pi-based implementation.

## Features

- Video recording while driving
- Live stream mode
- Parking mode (periodic photos)
- Telegram Bot
- Web UI
- WireGuard
- USB-modem support for remote access over mobile network, GPS, SMS
- Multi-user

## Hardware

- Raspberry Pi Zero 2W
- RPi supported CSI camera with wide lense (OV5647, PiCamera Module 3)
- PiSugar 3 UPS
- 4G USB modem (e.g. SIM7600 or A7670. Consider an [A7670.md note](A7670.md))

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

## Discussion

### Raspberry Pi, Linux and Python in a dashcam?

- RPi + Linux + Python is the fastest way to build a prototype and answer the question "is this even possible?"
- Low barrier to entry.
- Optimal performance: we managed to implement all the required features (1080p30 video recording, live streaming, HTTP) and stay within reasonable limits in terms of CPU headroom, temperature, and power consumption.

### Power: UPS and the challenges of lithium-ion batteries

The main reason a UPS is needed is to gracefully shut down the RPi after it is disconnected from the external power source. The battery is also needed to implement the periodic-photo scenario while parked.

#### Continuous power from the car battery
In this case we need to solve the problem of shutting down the RPi when the ignition is turned off. By default this would be an instant power cut to the board — better not even experiment with it. One direction worth trying: use dashcam power devices that plug into the fuse box and keep the 5V voltage from the battery when the ignition is off, and also provide an indicator wire signaling whether the engine is running or not.

#### UPS based on lithium-ion or lithium-polymer batteries
As already mentioned, [PiSugar 3](https://www.pisugar.com/products/pisugar-3-raspberry-pi-zero-battery) is the most suitable and feature-rich UPS, implementing everything that is needed:

- powering off the RPi (by default `shutdown` does not cut power to the RPi);
- RTC;
- RTC Alarm (powering on the RPi at a scheduled time);
- I2C: controlling the UPS and reading its status.

**Other UPS options without the ability to programmatically power off the RPi:**

- [Waveshare UPS HAT (C)](https://www.waveshare.com/ups-hat-c.htm): I2C support, Pogo pins.
- [Geekworm X306 UPS Shield](https://geekworm.com/products/x306): no I2C, Pogo pins, 18650 battery.
- [DFRobot UPS HAT](https://www.dfrobot.com/product-1932.html): I2C support, requires soldering a 40-pin connector onto the RPi.

**Obvious drawbacks of a battery-based UPS:**

- the hazard associated with the instability of lithium batteries;
- battery degradation due to elevated temperatures.

#### UPS based on supercapacitors

Such a solution makes it possible to gracefully shut down the RPi when external power is lost (the car engine stops). At the same time, however, it is impossible to implement the parking-mode logic (timer-based wakeup).

Overall, this is perhaps one of the most preferable UPS options, but the market offering is very limited.

### Temperature

**Factor 1:** elevated RPi temperature during video recording.

Logic for degrading video quality when the CPU heats up is implemented:

- `> 60°C`: video quality is forcibly reduced to `720p 15 fps`.
- `> 65°C`: video recording stops and the periodic-photo mode is enabled (one photo every 10 sec).
- If degradation mode was enabled, once the temperature drops to `55°C` the recording settings revert to the user-defined values.

**Factor 2:** heating from the PiSugar UPS while charging the battery.

Observation: with the 80% charge threshold disabled (battery-saver mode turned off in the settings), the UPS heats up noticeably less.

**Factor 3:** high ambient temperature.

Please do not use the device at an ambient temperature above `55°C`.
