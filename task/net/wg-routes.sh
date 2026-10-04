#!/bin/bash
# Policy routing for the WireGuard interface. Runs as root from the PostUp / PreDown hooks
# of /etc/wireguard/wg0.conf. org_vrg_net generates that file (plugins/org_vrg_net/wg_config.py)
# with `Table = off`, so wg-quick does not touch routing itself.
#
# Unlike wg-quick's own routing, the tunnel never becomes the default route:
#   - every AllowedIPs prefix except the default one is routed through the tunnel for
#     everyone (main table), so the VPN subnet and networks behind the peer stay reachable;
#   - all AllowedIPs prefixes, the default one included, go into a dedicated table that is
#     looked up only for packets sourced from the tunnel's own address.
#
# Traffic sourced from the tunnel address leaves through the tunnel: replies to connections
# that came in through it (web UI, ssh) and sockets that plugins bind to it (sdk/egress.py).
# Everything else keeps using the default interface (WiFi / modem).
#
# Usage: wg-routes.sh up|down <interface>
#
# TABLE must match WG_ROUTE_TABLE in plugins/org_vrg_net/const.py.

ACTION="$1"
IFACE="$2"
TABLE=51821
PRIORITY=1000

if [ -z "$ACTION" ] || [ -z "$IFACE" ]; then
    echo "Usage: $0 up|down <interface>"
    exit 1
fi

flush() {
    for family in -4 -6; do
        while ip "$family" rule del table "$TABLE" 2>/dev/null; do :; done
        ip "$family" route flush table "$TABLE" 2>/dev/null
    done
}

up() {
    # Start from a clean table: the hook may run again without a matching "down"
    flush

    # `wg show <if> allowed-ips` prints "<peer key>\t<prefix> <prefix> ..." per peer
    for prefix in $(wg show "$IFACE" allowed-ips | cut -f2); do
        [ "$prefix" = "(none)" ] && continue

        family=-4
        [[ "$prefix" == *:* ]] && family=-6

        if [ "$prefix" = "0.0.0.0/0" ] || [ "$prefix" = "::/0" ]; then
            ip "$family" route replace default dev "$IFACE" table "$TABLE"
        else
            ip "$family" route replace "$prefix" dev "$IFACE" table "$TABLE"
            ip "$family" route replace "$prefix" dev "$IFACE"
        fi
    done

    for family in -4 -6; do
        for addr in $(ip "$family" -o addr show dev "$IFACE" scope global | awk '{print $4}' | cut -d/ -f1); do
            ip "$family" rule add from "$addr" table "$TABLE" priority "$PRIORITY"
        done
    done
}

case "$ACTION" in
    up) up ;;
    down) flush ;;
    *)
        echo "Unknown action: $ACTION"
        exit 1
        ;;
esac

# Never fail the wg-quick hook: a routing problem must not tear the interface down
exit 0
