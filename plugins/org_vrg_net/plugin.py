import asyncio
import time

import plugins.org_vrg_net.const as const
from plugins.org_vrg_net.net_controls import NetControls
from plugins.org_vrg_net.net_services import NetServicesManager
from plugins.org_vrg_net.wg import WireguardMonitor
from sdk.service import Plugin


class NetPlugin(Plugin):
  _last_ip: str
  wg_monitor: WireguardMonitor = None
  _last_charging_state = 0
  _wifi_was_disabled_once = False
  _net_services_was_started_once = False
  net_services: NetServicesManager
  net_controls: NetControls

  def __init__(self, id, name, videoreg):
    super().__init__(id, name, videoreg)
    self._last_ip = None

  async def start(self):
    await super().start()

    if self.state.get(const.KEY_WIFI_BLOCKED, False):
      self.logger.debug("block wifi")
      await self.net_controls.set_wifi_blocked(blocked=True)
    else:
      self.logger.debug("unblock wifi")
      await self.net_controls.set_wifi_blocked(blocked=False)

    asyncio.create_task(self._start_lifecycle_loop())
    if self.state.get(const.KEY_WG_AUTO, True):
      asyncio.create_task(self.start_wg_monitor_loop())

  async def stop(self):
    await super().stop()
    if self.wg_monitor:
      self.wg_monitor.stop_monitor_loop()

    # Need to prevent auto wifi on next boot
    # self.logger.debug("Disable wifi autoconnect on stop")
    # await self._disable_wifi_autoconnect()

  def init_net_services(self, net_services: NetServicesManager):
    self.net_services = net_services

  def init_net_controls(self, net_controls: NetControls):
    self.net_controls = net_controls

  def init_wg_monitor(self, wg_monitor: WireguardMonitor):
    self.wg_monitor = wg_monitor

  def stop_wg_monitor_loop(self):
    if not self.wg_monitor:
      return
    self.wg_monitor.stop_monitor_loop()

  async def start_wg_monitor_loop(self):
    if self.wg_monitor:
      await self.wg_monitor.start_monitor_loop()
    else:
      self.logger.info("WireGuard monitor not started (wg_monitor is None)")

  async def _start_lifecycle_loop(self):
    try:
      while self.runner.is_running():
        is_charging = await self.runner.pisugar.get_charging_status_slow_but_safe()

        if is_charging == self._last_charging_state:
          await asyncio.sleep(5)
          continue

        await self._start_net_services_if_needed(is_charging)

        #
        #
        # TODO: join logic
        #
        #

        # if is_charging == -1:
        # if self.state.get(const.KEY_WIFI_AUTO, True):
        #   self.logger.debug("Charging off: will disable wifi")
        #   await self._disable_wifi()
        #   self._wifi_was_disabled_once = True
        # else:
        # if self.state.get(const.KEY_WIFI_AUTO, True):
        #   self.logger.debug("Charging on: will enable wifi")
        #   # await self._enable_wifi(up_conenction=self._wifi_was_disabled_once) # don't up connection on startup
        #   await self._enable_wifi(up_conenction=True)
        # else:
        #   self.logger.debug("Charging on but wifi configured to disable autoconnect: disable wifi")
        #   await self._disable_wifi()
        #   self._wifi_was_disabled_once = True

        self._last_charging_state = is_charging

        await asyncio.sleep(5)

    except Exception as e:
      self.logger.error(f"lifecycle loop error: {e}", exc_info=True)

  # async def _enable_wifi(self, up_conenction: bool):
  # await wifi.wifi_unblock(self.runner.videoreg, self.logger)
  # await wifi.connection_autoconnect(self.runner.videoreg, self.logger, "wifi", autoconnect=True)
  # if up_conenction:
  #   await wifi.connection_up(self.runner.videoreg, self.logger, "wifi")

  # async def _disable_wifi(self):
  #   await self._disable_wifi_autoconnect()
  #   await wifi.wifi_block(self.runner.videoreg, self.logger)

  # async def _disable_wifi_autoconnect(self):
  #   await wifi.connection_autoconnect(self.runner.videoreg, self.logger, "wifi", autoconnect=False)

  async def _start_net_services_if_needed(self, is_charging: bool):
    if is_charging == -1:
      last_time_started = self.state.get(const.KEY_LAST_NET_SERVICES_START, None)

      # Start if missing timestamp
      if not last_time_started:
        self.logger.info("will start net services due to missing last timestamp")
        await self._start_net_services()

      time_diff = time.time() - last_time_started

      #
      # ⚠️
      #
      if time_diff > 1:
        self.logger.info("will start net services due to pass more than 2 min")
        await self._start_net_services()

      # TODO: problem if net down first but power up second
      # else:
      #   self.logger.info(f"will disable net services due to pass less than 2 min")
      #   await self._stop_net_services()
    else:
      if not self._net_services_was_started_once:
        self.logger.info("will start net services due to charging is on")
        await self._start_net_services()

  async def _start_net_services(self):
    self.state.save({const.KEY_LAST_NET_SERVICES_START: time.time()})
    result = await self.net_services.start()

    if result.returncode == 0:
      self._net_services_was_started_once = True
      self.logger.info("net services started")
      # give NetworkManager some time to start
      # because in next steps we probably will manage wifi connection
      await asyncio.sleep(3)
    else:
      self.logger.warning("net services not started")

  async def _stop_net_services(self):
    result = await self.net_services.stop()

    if result.returncode == 0:
      self._net_services_was_started_once = True
      self.logger.info("net services stopped")
    else:
      self.logger.warning("net services not stopped")
