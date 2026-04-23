#!/bin/bash
# Generates a self-signed SSL certificate (RSA 2048, 10 years) for the HTTPS server.
# Includes Subject Alternative Names (SANs) for the provided IP addresses so that
# modern browsers accept the certificate as valid for the device IP.

show_help() {
  echo "Usage: $0 --keyout <key_path> --certout <cert_path> [--ips <ip1,ip2,...>]"
  echo ""
  echo "Required parameters:"
  echo "  --keyout    Path to save the private key"
  echo "  --certout   Path to save the certificate"
  echo ""
  echo "Optional parameters:"
  echo "  --ips       Comma-separated list of IP addresses to include as SANs"
  echo ""
  echo "Example:"
  echo "  $0 --keyout /path/to/key.pem --certout /path/to/cert.pem --ips 192.168.1.100,127.0.0.1"
  exit 1
}

KEYOUT_PATH=""
CERT_PATH=""
IPS_PARAM=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --keyout)
      KEYOUT_PATH="$2"
      shift 2
      ;;
    --certout)
      CERT_PATH="$2"
      shift 2
      ;;
    --ips)
      IPS_PARAM="$2"
      shift 2
      ;;
    -h|--help)
      show_help
      ;;
    *)
      echo "Unknown parameter: $1"
      show_help
      ;;
  esac
done

# Check required parameters
if [ -z "$KEYOUT_PATH" ]; then
  echo "Error: --keyout parameter is required"
  show_help
fi

if [ -z "$CERT_PATH" ]; then
  echo "Error: --certout parameter is required"
  show_help
fi

# Create directories if they do not exist
mkdir -p "$(dirname "$KEYOUT_PATH")"
mkdir -p "$(dirname "$CERT_PATH")"

# Build subjectAltName string from comma-separated IPs
SAN_STRING=""
if [ -n "$IPS_PARAM" ]; then
  IFS=',' read -ra IP_ARRAY <<< "$IPS_PARAM"
  for ip in "${IP_ARRAY[@]}"; do
    ip=$(echo "$ip" | tr -d ' ')
    if [ -n "$ip" ]; then
      if [ -n "$SAN_STRING" ]; then
        SAN_STRING="$SAN_STRING,IP:$ip"
      else
        SAN_STRING="IP:$ip"
      fi
    fi
  done
fi

# Generate certificate
if [ -n "$SAN_STRING" ]; then
  openssl \
    req -x509 \
    -newkey rsa:2048 \
    -keyout "$KEYOUT_PATH" \
    -out "$CERT_PATH" \
    -days 3650 \
    -nodes \
    -subj "/CN=Videoreg" \
    -addext "subjectAltName=$SAN_STRING"
else
  openssl \
    req -x509 \
    -newkey rsa:2048 \
    -keyout "$KEYOUT_PATH" \
    -out "$CERT_PATH" \
    -days 3650 \
    -nodes \
    -subj "/CN=Videoreg"
fi

echo "SSL certificate created successfully:"
echo "  Key: $KEYOUT_PATH"
echo "  Certificate: $CERT_PATH"
if [ -n "$SAN_STRING" ]; then
  echo "  SANs: $SAN_STRING"
fi
