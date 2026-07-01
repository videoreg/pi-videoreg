# Pi-Videoreg

🇬🇧 English | [🇷🇺 Русский](README.ru.md)

[Videoreg.org](https://videoreg.org) — an open project exploring DIY dashcam builds for cars with remote access.

**Pi-Videoreg** — a Raspberry Pi-based implementation.

## Features

- Video recording (dashcam mode)
- Live stream mode
- Parking mode (periodic photos)
- Remote access over the internet (WiFi or USB modem)
- Telegram Bot
- Web UI
- WireGuard
- GPS, SMS via USB modem
- Multi-user

## Hardware

- Raspberry Pi Zero 2W
- RPi supported CSI camera, e.g. OV5647 (see [more about the camera](#-camera))
- PiSugar 3 UPS (see [more about power](#-power-ups))
- 4G USB modem, e.g. SIM7600 or A7670 (see [more about the internet connection](#-internet-connection))
- Heatsink for RPi (see [more about temperature](#-temperature))

## 3D Case and Assembly

[Download model](https://github.com/videoreg/3d-models/tree/main/pi-videoreg)

[Open instructions](docs/images/assembly.png)

<img src="docs/images/assembly.png" width="300">


## Installation

Pi-Videoreg is a comprehensive system that requires OS configuration and a custom build of [rpicam-apps](https://github.com/videoreg/rpicam-apps). The only supported installation method at this time is using a pre-built `.img` image based on Raspberry Pi OS.

Download the `.img` image here: https://github.com/videoreg/pi-gen.

Flash the image using the official Raspberry Pi Imager:

1. Select "Raspberry Pi Zero 2W" or "No filtering"
2. At the bottom of the list, choose to install from a local `.img` file

## First Boot and Initial Setup

By default, the device creates a WiFi network (Access Point) named `videoreg` with password `12345678`.

After connecting, open https://10.0.0.1:8443 in your browser (the browser may warn about an untrusted certificate — this is expected).

Web UI login credentials: username `admin`, password `videoreg`.

>[!WARNING]
>Change the user password and WiFi password immediately!

### Date and Time

On first boot, set the timezone in the Web UI (`Settings → Date & Time`).

Note that the Raspberry Pi board itself cannot keep time across reboots. There are 2 ways to determine the time automatically after a reboot:

1. When [connected to the internet](#-internet-connection), the RPi queries an NTP server on every start to obtain the current time.
2. The current time is stored in the RTC of the PiSugar 3 (also updated after NTP synchronization), so on the next start the time will be correct even without an internet connection.

### Telegram Bot

1. In the Web UI, under the `Telegram Bot` settings, set your bot token.
2. On the `Users` tab, specify the Telegram user id you will use to talk to the bot.
3. In the chat with the bot, run the `/start` command — it initializes the bot menu.

### WireGuard

If you plan to keep access to the Web UI over a USB modem or from outside your "home WiFi network", set up WireGuard.

### Wakeup Interval

When using a PiSugar 3 UPS, you can set the wakeup interval for parking mode in the power settings: `Settings → Power`.

### SMS

If you use a SIM7600 USB modem, you can set up command execution and SMS forwarding to your mobile phone. To do this, specify your phone number in the `SMS` settings.

SMS features are not yet supported on the A7670 modem.

### SSH

For SSH access, use the `vrg` user with the password `videoreg123`

## Running with Docker

To explore the system or develop locally, run `docker compose up --build` (subsequently just `docker compose up`).

## Considerations

### 🤔 Raspberry Pi, Linux and Python in a dashcam?

- RPi + Linux + Python is the fastest way to build a prototype and answer the question "is this even possible?"
- Low barrier to entry.
- Optimal performance: we managed to implement all the required features (1080p30 video recording, live streaming, HTTP) and stay within reasonable limits in terms of CPU headroom, temperature, and power consumption.

That said, porting the current implementation to a compiled language looks like a quite reasonable evolution of the project. `C/C++` seem the most promising, since the logic could be reused in an ESP32-based implementation.

> [!TIP]
> It's worth emphasizing that the core task — video recording — is implemented in C++ by default and uses hardware codecs. Specifically, video and photo capture go through a customized version of [rpicam-apps](https://github.com/videoreg/rpicam-apps).

### 📷 Camera

Key camera requirements:

- A camera with a CSI MIPI connection is required. USB cameras cannot deliver the necessary performance on the Raspberry Pi Zero 2W.
- A wide field of view. `160°` is ideal. Keep in mind that video is usually recorded not from the full sensor but with a crop. This means the actual field of view on the video will be `~120°` instead of `160°`.

Tested models:

- [Waveshare RPi Camera (G)](https://www.waveshare.com/rpi-camera-g.htm)
- [Pi Camera Module 3](https://www.raspberrypi.com/products/camera-module-3/)

### 🔋 Power, UPS

The main reason a UPS is needed is to gracefully shut down the RPi after it is disconnected from the external power source. The battery is also needed to implement the periodic-photo scenario while parked.

#### Option: continuous power from the car battery without a UPS

In this case we need to solve the problem of shutting down the RPi when the ignition is turned off. By default this would be an instant power cut to the board — better not even experiment with it. One direction worth experimenting with: use dashcam power devices that plug into the fuse box and keep the 5V voltage from the battery when the ignition is off, and also provide an indicator wire signaling whether the engine is running or not.

#### Option: UPS based on lithium-ion or lithium-polymer batteries

As already mentioned, [PiSugar 3](https://www.pisugar.com/products/pisugar-3-raspberry-pi-zero-battery) is the most suitable and feature-rich UPS, implementing everything that is needed:

- powering off the RPi (by default `shutdown` does not cut power to the RPi);
- RTC (emulated);
- RTC Alarm (powering on the RPi at a scheduled time);
- I2C: controlling the UPS and reading its status.

**Other UPS options without the ability to programmatically power off the RPi:**

- [Waveshare UPS HAT (C)](https://www.waveshare.com/ups-hat-c.htm): I2C support, Pogo pins.
- [Geekworm X306 UPS Shield](https://geekworm.com/products/x306): no I2C, Pogo pins, 18650 battery.
- [DFRobot UPS HAT](https://www.dfrobot.com/product-1932.html): I2C support, requires soldering a 40-pin connector onto the RPi.

**Obvious drawbacks of a battery-based UPS:**

- the hazard associated with the instability of lithium batteries;
- battery degradation due to elevated temperatures.

#### Option: UPS based on supercapacitors

Such a solution makes it possible to gracefully shut down the RPi when external power is lost (the car engine stops). At the same time, however, it is impossible to implement the parking-mode logic (timer-based wakeup).

Overall, this is perhaps one of the most preferable UPS options, but the market offering is very limited.

### 📡 Internet Connection

#### Option 1: no internet connection

You can use the core dashcam features: video recording and parking mode (only together with PiSugar 3). You can access the Web UI through the WiFi access point (Access Point) that the device creates.

#### Option 2: connecting to a WiFi router

You can connect the device to any WiFi network with internet access (a phone, a car, a home or portable router). In that case, interaction via the Telegram Bot becomes available.

Connecting to a WiFi router unlocks the following capabilities:

- Integration into the local network via WireGuard: you can open the Web UI remotely, and the dashcam gains the ability to interact with devices on that network, for example uploading content to a home NAS (not yet implemented).
- Live video streaming.

#### Option 2: connecting via a USB modem

> [!CAUTION]
> Be sure to keep the WiFi access point enabled if you are not certain you can reach the Web UI through the connected USB modem. Only after WireGuard has been successfully configured should you disable the WiFi module.

The device has been tested with the SIM7600 and A7670 modems (see the [A7670.md note](A7670.md) for details).

Connecting a modem unlocks the following capabilities (in addition to the previous ones):

- Remote access to the device anywhere there is mobile network coverage.
- GPS tracking: a track of every trip is recorded automatically.
- SMS: controlling the device via SMS commands, as well as forwarding incoming SMS to the Telegram Bot.

### 📅 RTC: Date and Time

Keeping the date and time across restarts is a fundamental requirement for the system to work correctly. As mentioned [above](#date-and-time), there are 2 ways to preserve the date and time after a reboot: NTP synchronization over the internet and the RTC in the PiSugar 3 UPS. For this reason, running the system without either an internet connection or an RTC is currently not supported.

The specifics of the software RTC emulation based on PiSugar 3 are handled in the `vrg-hwclock-load.service` & `vrg-hwclock-save.service` systemd services.

### 🌡️ Temperature

Essential build requirements:

- A heatsink for the Raspberry Pi, for example the [Geekworm C296](https://geekworm.com/products/c296) 10mm Aluminum Alloy Heatsink.
- A case with plenty of ventilation holes.

**Factor 1:** elevated RPi temperature during video recording.

Logic for degrading video quality when the CPU heats up is implemented:

- `> 60°C`: video quality is forcibly reduced to `720p 15 fps`.
- `> 65°C`: video recording stops and the periodic-photo mode is enabled (one photo every 10 sec).
- If degradation mode was enabled, once the temperature drops to `55°C` the recording settings revert to the user-defined values.

**Factor 2:** heating from the PiSugar UPS while charging the battery.

Observation: with the 80% charge threshold disabled (battery-saver mode turned off in the settings), the UPS heats up noticeably less.

**Factor 3:** high ambient temperature.

Please do not use the device at an ambient temperature above `35°C`.

### 🏛️ Architecture

The main components are `systemd services` and `plugins`.

**Systemd services** with the `vrg-*` prefix are the main processes that run one or more plugins.

**Plugins** implement specific logic: working with the camera, networking, power, and so on.

Components communicate with each other through a Unix socket (event bus) implemented in the `org_vrg_bus` plugin.

The mapping between services and plugins is defined in `videoreg.manifest.yaml`. The current configuration:

| systemd service | plugins |
|---|---|
| **vrg-core** | **core** — general logic<br>**bus** — event bus (Unix socket)<br>**net** — networking: WiFi, WireGuard, modem<br>**power** — power, battery, PiSugar<br>**stat** — statistics: CPU, disk, traffic |
| **vrg-camera** | **camera** — video, photo, live stream |
| **vrg-modem** | **modem** — modem AT access: GPS tracking, SMS, modem info |
| **vrg-http** | **http** — HTTPS server |
| **vrg-bot** | **bot** — Telegram bot |
| **vrg-pisugar-watchdog** | Watchdog (no plugins) |
| **vrg-mediamtx** | MediaMTX for live streaming (no plugins) |

> [!TIP]
> The systemd services depend on `vrg-boot.target`, so you can restart them all with `systemctl restart vrg-boot.target`.

> [!NOTE]
> Starting the system with the `--env dev` flag (for example via `docker compose up`) uses `videoreg.manifest.dev.yaml`, where all plugins run within a single (pseudo) service.

#### Why functionality is split across separate systemd services

- A more resilient system. For example, problems in the Telegram Bot do not affect the core video-recording feature.
- The ability to build services implemented with different technologies. For example, a service can be written in `C/C++` and interact with other `Python` services through the event bus.
- The ability to isolate parts of the system that start conditionally (a "target" in `systemd` terms). For example, a service can be started only when an external power source is connected, via `vrg-charging.target`.
- In the future: running services under different Linux users for more flexible access control across parts of the system and improved privacy/security.

## Roadmap and Open Problems

### Track: hardware

**The modem power-off problem in parking mode**: with the PiSugar UPS, the USB modem loses power together with the RPi. It also powers back on unconditionally together with the RPi. For the periodic parking-monitoring mode, this behavior has the following drawbacks:

- The modem has to reconnect to the mobile network on every start. The RPi is forced to stay powered on longer to wait for an internet connection (there is a 20-second limit) — this drains the battery faster.
- While connecting to the network, the modem draws several times more current than in normal mode, and such periodic "wake-ups" noticeably drain the battery.
- The GPS receiver starts "cold" and does not have enough time to obtain a fix in such a short window.
- The periodic-monitoring logic tolerates very long delays in responding to user commands. And in general, to save battery, the USB modem could be powered on only on some RPi starts rather than every one.

Possible solutions:

1. Connect the modem to the RPi through a GPIO-controlled USB switch. This would make it possible to control the modem's power from the RPi in software.
2. Instead of cutting power to the USB modem, put it into sleep mode. This is not possible with the PiSugar 3, and no other off-the-shelf solution was found. So this likely requires designing a custom PCB with power management.

### Track: development

**Unify the interaction with QMI-type USB modems and the rest:** as mentioned above, unlike the SIM7600, the A7670 modem requires manual configuration and is not supported by ModemManager (through which we access SMS and GPS). As a solution to the latter problem, we could drop ModemManager and read the data (SMS and location) directly from `/dev/ttyUSB2` and `/dev/ttyUSB3` respectively.

**Improve the security of the initial setup:** on first boot the device automatically creates an `admin` user with a preset password, as well as a `videoreg` WiFi access point.

On the first Web UI login the user is required to set **their own** new password, but changing the WiFi password is still only a recommendation, which is a problem. A solution needs to be found.

**Cover the code with tests:** to improve stability, the code needs both unit tests and a solution for integration tests.

**Create a plugin for uploading content to remote network storage:** upload photos and videos to, say, a home NAS.

**Add support for installing third-party plugins:** the plugin-based architecture already assumes the set of plugins can be arbitrary. A solution for installing additional third-party plugins is needed. As part of the same task, each plugin should run under its own user.

**Create a user-notification engine:** consider the problem using SMS-to-Telegram forwarding as an example. If for some reason sending the message to Telegram fails (for example, due to network issues), the send will not be retried. Similar behavior currently applies in all such cases.

## License

This project is licensed under the [GNU Affero General Public License v3.0](LICENSE).
