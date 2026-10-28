import os

import plugins.org_vrg_net.const as const
from plugins.org_vrg_net.plugin import NetPlugin
from plugins.org_vrg_net.wg_config import build_config, normalize_settings, parse_config
from sdk.socket.api import ApiMethod


class MethodSaveWireguardConfig(ApiMethod):
  """Generates the WireGuard config file from the form settings and applies it.

  Args: {"settings": {<wg_config.FIELDS>}}. An empty `private_key` keeps the current one.
  The previous file is kept as `.backup`. If the tunnel is up, it is restarted right away
  so the new config takes effect (connections through the tunnel drop for a moment).
  Data: {"active": bool, "restarted": bool}
  """

  _plugin: NetPlugin
  _routes_script: str

  def __init__(self, plugin: NetPlugin, routes_script: str):
    super().__init__()
    self._plugin = plugin
    self._routes_script = routes_script

  async def exec(self, args):
    i18n = self._plugin.runner.i18n
    settings = dict((args or {}).get("settings") or {}) if isinstance(args, dict) else {}

    try:
      previous = None
      if os.path.exists(const.WG_CONFIG_PATH):
        with open(const.WG_CONFIG_PATH, encoding="utf-8") as f:
          previous = f.read()

      if not str(settings.get("private_key") or "").strip() and previous:
        settings["private_key"] = parse_config(previous)[0]["private_key"]

      normalized, invalid_field = normalize_settings(settings)
      if invalid_field:
        field = i18n.t(f"net.wireguard.field_{invalid_field}")
        error = i18n.t("net.wireguard.error_invalid_field", field=field)
        return {"status": "error", "error": error}

      content = build_config(normalized, self._routes_script)

      if previous is not None:
        self._write(f"{const.WG_CONFIG_PATH}.backup", previous)
      self._write(const.WG_CONFIG_PATH, content)
      self._plugin.logger.info("WireGuard config file updated")

      monitor = self._plugin.wg_monitor
      if not await monitor.is_wg_active():
        return {"status": "ok", "data": {"active": False, "restarted": False}}

      if not await monitor.restart_wireguard():
        return {"status": "error", "error": i18n.t("net.wireguard.error_restart")}

      return {"status": "ok", "data": {"active": await monitor.is_wg_active(), "restarted": True}}

    except PermissionError:
      self._plugin.logger.error(f"Permission denied writing to {const.WG_CONFIG_PATH}")
      return {"status": "error", "error": "Permission denied"}
    except Exception as e:
      self._plugin.logger.error(f"Error writing WireGuard config: {e}", exc_info=True)
      return {"status": "error", "error": str(e)}

  def _write(self, path: str, content: str):
    # The config holds the private key: readable by its owner only
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
      f.write(content)
    try:
      os.chmod(path, 0o600)
    except OSError:
      pass
