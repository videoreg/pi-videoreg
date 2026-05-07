import asyncio
import ssl
import subprocess
import time
from logging import DEBUG

from aiohttp import web

import plugins.org_vrg_http.const as const
import plugins.org_vrg_http.handlers.auth_handlers as auth_handlers
import plugins.org_vrg_http.handlers.dashboard_handlers as dashboard_handlers
import plugins.org_vrg_http.handlers.i18n_handlers as i18n_handlers
import plugins.org_vrg_http.handlers.media_handlers as media_handlers
import plugins.org_vrg_http.handlers.plugins.org_vrg_bot.bot_handlers as bot_handlers
import plugins.org_vrg_http.handlers.plugins.org_vrg_camera.camera_handlers as camera_handlers
import plugins.org_vrg_http.handlers.plugins.org_vrg_camera.hls_handlers as hls_handlers
import plugins.org_vrg_http.handlers.plugins.org_vrg_camera.media_feed_handlers as media_feed_handlers
import plugins.org_vrg_http.handlers.plugins.org_vrg_core.journal_handlers as journal_handlers
import plugins.org_vrg_http.handlers.plugins.org_vrg_core.system_handlers as system_handlers
import plugins.org_vrg_http.handlers.plugins.org_vrg_gps.gps_handlers as gps_handlers
import plugins.org_vrg_http.handlers.plugins.org_vrg_net.modem_handlers as modem_handlers
import plugins.org_vrg_http.handlers.plugins.org_vrg_net.nm_connection_handlers as nm_connection_handlers
import plugins.org_vrg_http.handlers.plugins.org_vrg_net.wireguard_handlers as wireguard_handlers
import plugins.org_vrg_http.handlers.plugins.org_vrg_power.power_handlers as power_handlers
import plugins.org_vrg_http.handlers.plugins.org_vrg_sms.sms_handlers as sms_handlers
import plugins.org_vrg_http.handlers.plugins.org_vrg_stat.stat_handlers as stat_handlers
import plugins.org_vrg_http.handlers.plugins.org_vrg_stat.storage_handlers as storage_handlers
import plugins.org_vrg_http.handlers.static_handlers as static_handlers
import plugins.org_vrg_http.handlers.user_handlers as user_handlers
from plugins.org_vrg_http.jwt_handler import JwtHandler
from plugins.org_vrg_http.middleware import create_auth_middleware
from sdk.helper import stream_subprocess
from sdk.service import Plugin
from sdk.user_manager import UserManager


class HttpPlugin(Plugin):
  _runner: web.AppRunner = None
  _jwt_handler: JwtHandler = None
  _user_manager: UserManager = None

  async def start(self):
    await super().start()

    # Initialize authorization components
    jwt_secret_path = self.runner.videoreg.private_path("data/jwt_secret.txt")
    users_file_path = self.runner.videoreg.private_path("data/users.json")

    self._jwt_handler = JwtHandler(jwt_secret_path)
    self._user_manager = UserManager(users_file_path)

    self.logger.info("Authorization components initialized")

    asyncio.create_task(self._start_server())

  async def stop(self):
    await super().stop()
    if self._runner:
      await self._runner.cleanup()

  async def _start_server(self):
    # Create authorization middleware
    auth_middleware = create_auth_middleware(self._jwt_handler, self._user_manager)

    app = web.Application(middlewares=[self._error_middleware, auth_middleware])

    # Pass dependencies into app for use in handlers
    app["jwt_handler"] = self._jwt_handler
    app["user_manager"] = self._user_manager
    app["logger"] = self.logger
    app["videoreg"] = self.runner.videoreg
    app["api_client"] = self.api_client
    app["i18n"] = self.runner.i18n
    app["static_version"] = self._get_static_version()

    # Main page and SPA routes (all serve index.html)
    app.router.add_get("/", static_handlers.handle_index)
    for _spa_page in [
      "home",
      "change-password",
      "settings",
      "sms-inbox",
      "gps-tracks",
      "stat",
      "trips",
      "media-feed",
      "media-fave",
      "live-broadcast",
    ]:
      app.router.add_get(f"/{_spa_page}", static_handlers.handle_index)
    app.router.add_get("/settings/{sub:.*}", static_handlers.handle_index)
    app.router.add_get("/static/{filename:.*}", static_handlers.handle_static)

    # Auth API endpoints
    app.router.add_post("/api/auth/login", auth_handlers.handle_login)
    app.router.add_post("/api/auth/logout", auth_handlers.handle_logout)
    app.router.add_post("/api/auth/refresh", auth_handlers.handle_refresh)
    app.router.add_post("/api/auth/change-password", auth_handlers.handle_change_password)
    app.router.add_get("/api/auth/me", auth_handlers.handle_me)

    # System API endpoints
    app.router.add_get("/api/system/info", system_handlers.handle_get_system_info)
    app.router.add_post("/api/system/plugin/enabled", system_handlers.handle_set_plugin_enabled)
    app.router.add_post("/api/system/service/action", system_handlers.handle_service_action)

    # Core API endpoints
    app.router.add_get("/api/core/journal", journal_handlers.handle_get_journal)

    app.router.add_get("/api/i18n", i18n_handlers.handle_get_i18n)
    app.router.add_get("/api/dashboard/status", dashboard_handlers.handle_get_dashboard_status)

    # Users API endpoints
    app.router.add_get("/api/users", user_handlers.handle_get_users)
    app.router.add_post("/api/users", user_handlers.handle_post_user)
    app.router.add_delete("/api/users/{username}", user_handlers.handle_delete_user)
    app.router.add_patch(
      "/api/users/{username}/plugin-fields/{plugin}", user_handlers.handle_patch_user_plugin_fields
    )

    # Media endpoints
    app.router.add_get("/video/{name}", media_handlers.handle_video)
    app.router.add_get("/photo/{name}", media_handlers.handle_photo)
    app.router.add_get("/fave_photo/{name}", media_handlers.handle_fave_photo)
    app.router.add_get("/gps/{name}", media_handlers.handle_gps_track)

    # Net API endpoints
    app.router.add_get(
      "/api/net/wireguard_status", wireguard_handlers.handle_net_get_wireguard_status
    )
    app.router.add_get(
      "/api/net/wireguard_config", wireguard_handlers.handle_net_get_wireguard_config
    )
    app.router.add_post(
      "/api/net/wireguard_config", wireguard_handlers.handle_net_set_wireguard_config
    )
    app.router.add_post(
      "/api/net/generate_wireguard_key", wireguard_handlers.handle_net_generate_wireguard_key
    )
    app.router.add_get("/api/net/modem_info", modem_handlers.handle_net_get_modem_info)
    app.router.add_get(
      "/api/net/connection_config", nm_connection_handlers.handle_net_get_connection_config
    )
    app.router.add_post(
      "/api/net/connection_config", nm_connection_handlers.handle_net_post_connection_config
    )
    app.router.add_post(
      "/api/net/connection_enable", nm_connection_handlers.handle_net_post_connection_enable
    )
    app.router.add_post("/api/net/wifi_block", nm_connection_handlers.handle_net_set_wifi_block)

    # Bot API endpoints
    app.router.add_get("/api/bot/config", bot_handlers.handle_bot_get_config)
    app.router.add_post("/api/bot/config", bot_handlers.handle_bot_config)

    # HLS live stream
    app.router.add_get("/hls/{filename}", hls_handlers.handle_get_hls)

    # Camera API endpoints
    app.router.add_get("/api/camera/info", camera_handlers.handle_get_camera_info)
    app.router.add_get("/api/camera/modes", camera_handlers.handle_get_camera_modes)
    app.router.add_post("/api/camera/settings", camera_handlers.handle_post_camera_settings)
    app.router.add_post("/api/camera/photo", camera_handlers.handle_post_camera_photo)
    app.router.add_post("/api/camera/video_start", camera_handlers.handle_post_camera_video_start)
    app.router.add_post("/api/camera/video_pause", camera_handlers.handle_post_camera_video_pause)
    app.router.add_post("/api/camera/short_video", camera_handlers.handle_post_camera_short_video)
    app.router.add_get("/api/camera/list_media", media_feed_handlers.handle_get_camera_list)
    app.router.add_get(
      "/api/camera/convert_check", media_feed_handlers.handle_get_camera_convert_check
    )
    app.router.add_post("/api/camera/convert", media_feed_handlers.handle_post_camera_convert)
    app.router.add_get("/api/camera/fave_list", media_feed_handlers.handle_get_camera_fave_list)
    app.router.add_post("/api/camera/fave", media_feed_handlers.handle_post_camera_fave)
    app.router.add_delete("/api/camera/fave", media_feed_handlers.handle_delete_camera_fave)
    app.router.add_get("/api/camera/stream_status", camera_handlers.handle_get_camera_stream_status)
    app.router.add_post("/api/camera/stream_start", camera_handlers.handle_post_camera_stream_start)
    app.router.add_post("/api/camera/stream_stop", camera_handlers.handle_post_camera_stream_stop)
    app.router.add_post("/api/camera/stream_settings", camera_handlers.handle_post_camera_stream_settings)

    # Power API endpoints
    app.router.add_get("/api/power/status", power_handlers.handle_get_power_status)
    app.router.add_get("/api/power/wakeup", power_handlers.handle_get_power_wakeup)
    app.router.add_post("/api/power/wakeup", power_handlers.handle_set_power_wakeup)
    app.router.add_get(
      "/api/power/charging-protection", power_handlers.handle_get_power_charging_protection
    )
    app.router.add_post(
      "/api/power/charging-protection", power_handlers.handle_post_power_charging_protection
    )
    app.router.add_post("/api/power/keep_alive", power_handlers.handle_post_power_keep_alive)
    app.router.add_post("/api/power/reboot", power_handlers.handle_post_power_reboot)
    app.router.add_post("/api/power/shutdown", power_handlers.handle_post_power_shutdown)

    # Stat API endpoints
    app.router.add_get("/api/stat/temp", stat_handlers.handle_get_stat_temp)
    app.router.add_get("/api/stat/pisugar", stat_handlers.handle_get_stat_pisugar)
    app.router.add_get("/api/stat/traffic", stat_handlers.handle_get_stat_traffic)
    app.router.add_get("/api/stat/storage_info", storage_handlers.handle_get_stat_storage_info)

    # SMS API endpoints
    app.router.add_get("/api/sms", sms_handlers.handle_get_sms)
    app.router.add_delete("/api/sms/{filename}", sms_handlers.handle_delete_sms)

    # GPS API endpoints
    app.router.add_get("/api/gps/tracks", gps_handlers.handle_get_gps_tracks)
    app.router.add_delete("/api/gps/tracks/{filename}", gps_handlers.handle_delete_gps_track)

    access_log = self.logger if self.logger.level == DEBUG else None

    await self._ensure_cert()

    ssl_ctx = self._create_ssl_context()

    runner = web.AppRunner(app, access_log=access_log)
    await runner.setup()

    # http_site = web.TCPSite(runner, host="0.0.0.0", port=const.HTTP_PORT)

    https_site = web.TCPSite(runner, host="0.0.0.0", port=const.HTTPS_PORT, ssl_context=ssl_ctx)
    await https_site.start()

  async def _get_local_ips(self) -> list[str]:
    ips = ["10.0.0.1"]
    try:
      proc = await asyncio.create_subprocess_exec(
        "hostname", "-I",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
      )
      stdout, _ = await proc.communicate()
      ips += [ip for ip in stdout.decode().split() if ip]
    except Exception as e:
      self.logger.warning(f"Could not determine local IPs: {e}")
    return ips

  async def _cert_covers_ips(self, cert_file, ips: list[str]) -> bool:
    try:
      proc = await asyncio.create_subprocess_exec(
        "openssl", "x509", "-in", str(cert_file), "-text", "-noout",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
      )
      stdout, _ = await proc.communicate()
      cert_text = stdout.decode()
      return all(f"IP Address:{ip}" in cert_text for ip in ips)
    except Exception as e:
      self.logger.warning(f"Could not inspect certificate SANs: {e}")
      return False

  async def _ensure_cert(self):
    cert_file = self.runner.videoreg.private_path("cert/cert.pem")
    key_file = self.runner.videoreg.private_path("cert/key.pem")

    local_ips = await self._get_local_ips()

    needs_regen = not cert_file.exists() or not key_file.exists()
    if not needs_regen:
      needs_regen = not await self._cert_covers_ips(cert_file, local_ips)
      if needs_regen:
        self.logger.info(f"SSL certificate does not cover current IPs {local_ips}, regenerating...")

    if needs_regen:
      self.logger.info("Creating SSL certificate...")
      result = await stream_subprocess(
        cmd=[
          "bash",
          str(self.runner.videoreg.app_path("task/ssl.sh")),
          "--keyout",
          str(key_file),
          "--certout",
          str(cert_file),
          "--ips",
          ",".join(local_ips),
        ],
        start_cb=lambda pid, cmd: self.logger.debug(f"CMD (pid={pid}): {cmd}"),
        stdout_cb=lambda pid, s: self.logger.debug(f"STDOUT (pid={pid}): {s}"),
        stderr_cb=lambda pid, s: self.logger.debug(f"STDERR (pid={pid}): {s}"),
      )
      if result.returncode == 0:
        self.logger.info(f"SSL certificate created successfully for IPs: {local_ips}")
      else:
        self.logger.error(f"Failed to create SSL certificate, returncode={result.returncode}")

  def _create_ssl_context(self):
    cert_file = self.runner.videoreg.private_path("cert/cert.pem")
    key_file = self.runner.videoreg.private_path("cert/key.pem")

    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_ctx.load_cert_chain(str(cert_file), str(key_file))

    return ssl_ctx

  def _get_static_version(self) -> str:
    try:
      result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        cwd=str(self.runner.videoreg.app_path(".")),
      )
      if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    except Exception:
      pass
    return str(int(time.time()))

  # Middleware to suppress client disconnection errors
  @web.middleware
  async def _error_middleware(self, request, handler):
    try:
      return await handler(request)
    except (ConnectionResetError, BrokenPipeError, ConnectionError):
      # Silently ignore — client simply disconnected
      raise web.HTTPClientError()
