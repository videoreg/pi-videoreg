# NetworkManager connection profile names provisioned by tools/install/nm-connections/.
# The vrg- prefix keeps the project's own profiles apart from connections the user
# created by hand. Not to be confused with the API-level connection types
# ("ap" / "wifi" / "modem") used by the http and bot layers.
NM_CONNECTION_AP = "vrg-ap"
NM_CONNECTION_WIFI = "vrg-wifi"
NM_CONNECTION_MODEM = "vrg-modem"

KEY_WG_AUTO = "wg_auto"
KEY_WG_SKIP_ON_WIFI = "wg_skip_on_wifi"
# Ids of plugins whose outbound traffic goes through WireGuard (see sdk/egress.py).
# Empty by default: even with the tunnel up, everything uses the default interface.
KEY_WG_EGRESS_PLUGINS = "wg_egress_plugins"
KEY_WIFI_BLOCKED = "wifi_blocked"
KEY_WIFI_AUTO = "wifi_auto"
KEY_LAST_NET_SERVICES_START = "last_net_services_start"

# Optional WiFi settings file in the root of the SD card data partition, applied once
# on start and then deleted (see wifi_file.py).
WIFI_FILE_PATH = "/mnt/data/wifi.txt"

WG_CONFIG_PATH = "/etc/wireguard/wg0.conf"

# Routing table for traffic sourced from the WireGuard address.
# Must match TABLE in task/net/wg-routes.sh.
WG_ROUTE_TABLE = 51821
