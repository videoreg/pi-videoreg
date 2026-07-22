import asyncio
import re
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
import plugins.org_vrg_http.handlers.plugins.org_vrg_camera.hls_handlers as hls_handlers
import plugins.org_vrg_http.handlers.plugins.org_vrg_core.journal_handlers as journal_handlers
import plugins.org_vrg_http.handlers.plugins.org_vrg_core.system_handlers as system_handlers
import plugins.org_vrg_http.handlers.static_handlers as static_handlers
import plugins.org_vrg_http.handlers.user_handlers as user_handlers
from plugins.org_vrg_http.bundle import build_bundle
from plugins.org_vrg_http.handlers.generic_api_handler import make_api_handler
from plugins.org_vrg_http.jwt_handler import JwtHandler
from plugins.org_vrg_http.manifest_reader import read_plugin_http_configs
from plugins.org_vrg_http.middleware import create_auth_middleware
from sdk.helper import stream_subprocess
from sdk.service import Plugin
from sdk.user_manager import UserManager


class HttpPlugin(Plugin):
  _runner: web.AppRunner = None
  _jwt_handler: JwtHandler = None
  _user_manager: UserManager = None
  _http_manifests: list = None

  async def start(self):
    await super().start()

    # Initialize authorization components
    jwt_secret_path = self.runner.videoreg.private_path("data/jwt_secret.txt")
    users_file_path = self.runner.videoreg.private_path("data/users.json")

    self._jwt_handler = JwtHandler(jwt_secret_path)
    self._user_manager = UserManager(users_file_path)

    self.logger.info("Authorization components initialized")

    # Read every enabled plugin's `http` manifest block once and keep it in
    # memory. Plugins disabled in the merged manifest contribute no menu / api.
    self._http_manifests = read_plugin_http_configs(
      self.runner.videoreg.merged_manifest()["plugins"]
    )
    self.logger.info(
      f"Loaded http manifests from {len(self._http_manifests)} plugin(s)"
    )

    # The http service only runs the http plugin, so i18n has loaded only its own
    # translations. Load every plugin's translations so moved tokens (e.g. bot.*)
    # are served by /api/i18n.
    plugins_dir = self.runner.videoreg.app_path("plugins")
    for plugin_dir in sorted(plugins_dir.glob("*/")):
      self.runner.i18n.load_plugin(plugin_dir)

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
    app["http_manifests"] = self._http_manifests

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
    app.router.add_get("/api/statusbar/status", dashboard_handlers.handle_get_statusbar_status)

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

    # HLS live stream
    app.router.add_get("/hls/{filename}", hls_handlers.handle_get_hls)

    # Manifest-driven plugin API endpoints (authorized zone)
    self._register_manifest_api_routes(app)

    # Bundle (re)build endpoint
    app.router.add_post("/api/http/bundle/rebuild", self._handle_bundle_rebuild)

    access_log = self.logger if self.logger.level == DEBUG else None

    await self._ensure_cert()

    ssl_ctx = self._create_ssl_context()

    runner = web.AppRunner(app, access_log=access_log)
    await runner.setup()

    # http_site = web.TCPSite(runner, host="0.0.0.0", port=const.HTTP_PORT)

    https_site = web.TCPSite(runner, host="0.0.0.0", port=const.HTTPS_PORT, ssl_context=ssl_ctx)
    await https_site.start()

  def _register_manifest_api_routes(self, app: web.Application):
    """Register one generic handler per `http.api` entry of every plugin.

    During the http-decoupling transition a plugin's `http.api` may still overlap
    with hardcoded routes (and the matching api-methods may not be migrated yet).
    To keep the server bootable, a manifest route is skipped when its
    (method, path) is already registered — hardcoded routes win until they are
    removed, at which point the generic route takes over automatically.
    """
    method_map = {
      "get": app.router.add_get,
      "post": app.router.add_post,
      "put": app.router.add_put,
      "patch": app.router.add_patch,
      "delete": app.router.add_delete,
    }

    existing = {(r.method, r.resource.canonical) for r in app.router.routes()}

    for config in self._http_manifests:
      for entry in config["http"].get("api") or []:
        url = entry.get("url")
        method = (entry.get("method") or "get").lower()
        api_method = entry.get("plugin")
        timeout = entry.get("timeout")

        register = method_map.get(method)
        if register is None or not url or not api_method:
          self.logger.warning(f"Skipping invalid http.api entry: {entry}")
          continue

        path = f"/api/{url}"
        key = (method.upper(), path)
        if key in existing:
          self.logger.info(f"Skipping {method.upper()} {path} (already registered)")
          continue

        register(path, make_api_handler(api_method, timeout))
        existing.add(key)
        self.logger.info(f"Registered {method.upper()} {path} -> {api_method}")

  async def _handle_bundle_rebuild(self, request: web.Request):
    plugins_dir = self.runner.videoreg.app_path("plugins")
    out_path = self.runner.videoreg.app_path(
      "plugins/org_vrg_http/static/js/bundle.js"
    )
    merged_plugins = self.runner.videoreg.merged_manifest()["plugins"]
    count = build_bundle(plugins_dir, out_path, merged_plugins)
    return web.json_response({"status": "ok", "components": count})

  async def _get_local_ips(self) -> list[str]:
    ips = list(const.CERT_SAN_STATIC_IPS)
    try:
      proc = await asyncio.create_subprocess_exec(
        "ip", "-o", "-4", "addr", "show",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
      )
      stdout, _ = await proc.communicate()
      for line in stdout.decode().splitlines():
        # Format: "3: wlan0    inet 192.168.1.5/24 brd 192.168.1.255 scope global wlan0"
        parts = line.split()
        if len(parts) < 4 or parts[2] != "inet":
          continue
        interface, ip = parts[1], parts[3].split("/")[0]
        if interface in const.CERT_SAN_INTERFACES and ip not in ips:
          ips.append(ip)
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
      cert_ips = set(re.findall(r"IP Address:([0-9.]+)", stdout.decode()))
      return set(ips).issubset(cert_ips)
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
