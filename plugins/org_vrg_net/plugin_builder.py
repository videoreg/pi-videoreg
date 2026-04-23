from argparse import Namespace

from plugins.org_vrg_net.commands.get_commands import CommandGetCommands
from plugins.org_vrg_net.commands.get_connection import CommandGetConnection
from plugins.org_vrg_net.commands.get_connections import CommandGetConnections
from plugins.org_vrg_net.commands.set_wifi_blocked import CommandSetWifiBlocked
from plugins.org_vrg_net.methods.connection_update import MethodConnectionUpdate
from plugins.org_vrg_net.methods.get_connection import MethodGetConnection
from plugins.org_vrg_net.methods.get_connections import MethodGetConnections
from plugins.org_vrg_net.methods.get_modem_info import MethodGetModemInfo
from plugins.org_vrg_net.methods.set_connection_enabled import MethodSetConnectionEnabled
from plugins.org_vrg_net.methods.set_wifi_blocked import MethodSetWifiBlocked
from plugins.org_vrg_net.methods.wg_auto import MethodWgAuto
from plugins.org_vrg_net.methods.wg_show import MethodWgShow
from plugins.org_vrg_net.plugin import NetPlugin
from plugins.org_vrg_net.wg import Config
from sdk.interface import Interface, InterfaceCommand, InterfaceCommandMethod
from sdk.service import ServiceRunner


async def build_plugin(runner: ServiceRunner, args: Namespace, plugin_manifest: dict) -> NetPlugin:
  id = plugin_manifest.get("id")
  name = plugin_manifest.get("name")

  plugin = NetPlugin(id, name, runner)
  plugin.init_logger(args.log_level)
  plugin.init_socket(client_id=name, channels=[], socket_path=None)

  wg_monitor_config = Config(
    connection_name_wifi="wifi",
    connection_name_modem="modem",
    wg_interface="wg0",
    wg_config_path="/etc/wireguard/wg0.conf",
    check_interval=10,
  )

  if args.env == "dev":
    from plugins.org_vrg_net.dev.modem_controls import ModemControlsImpl
    from plugins.org_vrg_net.dev.net_controls import NetControlsImpl
    from plugins.org_vrg_net.dev.net_services import NetServicesManagerImpl
    from plugins.org_vrg_net.dev.wg import WireguardMonitorImpl

    net_controls = NetControlsImpl()
    net_services = NetServicesManagerImpl()
    modem_controls = ModemControlsImpl()
    wg_monitor = WireguardMonitorImpl()
  else:
    from plugins.org_vrg_net.prod.modem_controls import ModemControlsImpl
    from plugins.org_vrg_net.prod.net_controls import NetControlsImpl
    from plugins.org_vrg_net.prod.net_services import NetServicesManagerImpl
    from plugins.org_vrg_net.prod.wg import WireguardMonitorImpl

    net_controls = NetControlsImpl(plugin.logger, runner.videoreg)
    net_services = NetServicesManagerImpl(plugin.logger)
    modem_controls = ModemControlsImpl()
    wg_monitor = WireguardMonitorImpl(plugin.logger, wg_monitor_config)

  plugin.init_net_controls(net_controls)
  plugin.init_net_services(net_services)
  plugin.init_wg_monitor(wg_monitor)
  plugin.init_api_client()

  interfaces = Interface.parse_interfaces(
    runner.videoreg.manifest.interfaces, plugin.logger, plugin.api_client
  )
  commands: dict[str, InterfaceCommand] = {
    "net": CommandGetCommands(plugin),
    "connections": CommandGetConnections(plugin, net_controls),
    "connection": CommandGetConnection(plugin, net_controls),
    "wifi_block": CommandSetWifiBlocked(net_controls, plugin.state, blocked=True),
    "wifi_unblock": CommandSetWifiBlocked(net_controls, plugin.state, blocked=False),
  }

  plugin.init_api_servier(
    methods={
      "command": InterfaceCommandMethod(interfaces, commands),
      "connections": MethodGetConnections(net_controls),
      "connection": MethodGetConnection(net_controls),
      "connection_update": MethodConnectionUpdate(plugin.logger, net_controls),
      "connection_up": MethodSetConnectionEnabled(net_controls, enabled=True),
      "connection_down": MethodSetConnectionEnabled(net_controls, enabled=False),
      "wg_auto": MethodWgAuto(plugin),
      "wg_show": MethodWgShow(plugin),
      "wifi_block": MethodSetWifiBlocked(net_controls, plugin.state, blocked=True),
      "wifi_unblock": MethodSetWifiBlocked(net_controls, plugin.state, blocked=False),
      "modem_info": MethodGetModemInfo(plugin.logger, modem_controls),
    }
  )

  return plugin
