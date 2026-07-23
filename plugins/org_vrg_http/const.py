HTTP_PORT = 80  # available for non-root with CAP_NET_BIND_SERVICE for .service
HTTPS_PORT = 8443  # available for non-root, not available even with CAP_NET_BIND_SERVICE ¯\_(ツ)_/¯

# Interfaces whose addresses are put into the SSL certificate SANs.
#
# This is an allowlist on purpose. The modem must never get in: its address is
# assigned by the carrier and changes on every reconnect, which would regenerate
# the certificate and make the browser show the "untrusted certificate" warning
# again. The device is not reachable from the internet by that address anyway.
# Depending on the mode the modem enumerates as usb0 (RNDIS/ECM), wwan0 or ppp0,
# so listing what is allowed is safer than trying to name every modem interface.
CERT_SAN_INTERFACES = ["wlan0", "eth0", "wg0"]

# Addresses that are always included, regardless of the interface state.
# 10.0.0.1 is the static AP address, see tools/install/nm-connections/vrg-ap.nmconnection
CERT_SAN_STATIC_IPS = ["10.0.0.1"]
