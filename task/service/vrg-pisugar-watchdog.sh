#!/bin/bash

# PiSugar 3 software watchdog

I2C_BUS=1 # I2C Bus number (usually 1 on Raspberry Pi)
I2C_ADDR=0x57 # PiSugar I2C Device Address (0x57 often used for PiSugar 3-series write protect)
REG_WATCHDOG=0x06
REG_WATCHDOG_TIMEOUT=0x07

# Loop control flag
RUNNING=1

VIDEOREG_PROJECT_HOME=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --videoreg-project-home)
            VIDEOREG_PROJECT_HOME="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            echo "Usage: $0 --videoreg-project-home <path>"
            exit 1
            ;;
    esac
done

# Check that the working directory is specified
if [ -z "$VIDEOREG_PROJECT_HOME" ]; then
    echo "Error: working directory not specified"
    echo "Usage: $0 --videoreg-project-home <path>"
    exit 1
fi

# Check that the directory exists
if [ ! -d "$VIDEOREG_PROJECT_HOME" ]; then
    echo "Error: directory $VIDEOREG_PROJECT_HOME does not exist"
    exit 1
fi

# Convert a number to its binary representation
to_binary() {
  local num=$1
  # If the number is in hex format (0x...), convert to decimal
  if [[ $num == 0x* ]]; then
    num=$((num))
  fi

  local binary=""
  local n=$num

  if [ $n -eq 0 ]; then
    echo "0"
    return
  fi

  while [ $n -gt 0 ]; do
    binary="$((n % 2))$binary"
    n=$((n / 2))
  done

  echo "$binary"
}

# Graceful shutdown handler
cleanup() {
  echo "Shutdown signal received, disabling watchdog..."
  RUNNING=0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT SIGHUP SIGQUIT


# Check if previous run ended correctly
WATCHDOG_FILE="${VIDEOREG_PROJECT_HOME}/.videoreg/data/pisugar-watchdog.txt"
ERRORS_FILE="${VIDEOREG_PROJECT_HOME}/.videoreg/data/pisugar-watchdog-errors.txt"
if [ -f "$WATCHDOG_FILE" ]; then
    FIRST_LINE=$(head -n 1 "$WATCHDOG_FILE")
    if [[ "$FIRST_LINE" != "Watchdog stopped correctly at"* ]]; then
        echo "$(date +"%Y-%m-%d %H:%M:%S")" >> "$ERRORS_FILE"
    fi
fi

# Boot watchdog
REG_VAL=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_WATCHDOG)
NEW_REG_VAL=$((0x18 | REG_VAL )) # Set 3 and 4 bits to 1
i2cset -y $I2C_BUS $I2C_ADDR $REG_WATCHDOG $NEW_REG_VAL
i2cset -y $I2C_BUS $I2C_ADDR 0x0a 3 # Set the maximum number of restarts
echo "Boot watchdog feed succesfully"

REG_VAL=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_WATCHDOG)

# WatchdogOn
NEW_REG_VAL=$((0x80 | REG_VAL ))

# Set timeout duration 5 * 2sec
i2cset -y $I2C_BUS $I2C_ADDR $REG_WATCHDOG_TIMEOUT 5

# Write register
i2cset -y $I2C_BUS $I2C_ADDR $REG_WATCHDOG $NEW_REG_VAL

DATETIME=$(date +"%Y-%m-%d %H:%M:%S")

echo "Watchdog enabled, starting monitoring..."
echo "Watchdog started at ${DATETIME}" > "$WATCHDOG_FILE"

while [ $RUNNING -eq 1 ]; do
  REG_VAL=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_WATCHDOG)

  # Make sure the watchdog is on
  NEW_REG_VAL=$((0x80 | REG_VAL ))

  # feed watchdog
  NEW_REG_VAL=$((0x20 | NEW_REG_VAL ))

  i2cset -y $I2C_BUS $I2C_ADDR $REG_WATCHDOG $NEW_REG_VAL
  sleep 5
done

# Disable watchdog after loop exits
echo "Shutting down, disabling watchdog..."

DATETIME=$(date +"%Y-%m-%d %H:%M:%S")
echo "Watchdog stopped correctly at ${DATETIME}" > "$WATCHDOG_FILE"

REG_VAL=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_WATCHDOG)

# Clear bit 7 (0x80) using mask 0x7F
NEW_REG_VAL=$((REG_VAL & 0x7F))

# Write new value to register
i2cset -y $I2C_BUS $I2C_ADDR $REG_WATCHDOG $NEW_REG_VAL

echo "Watchdog disabled (register 0x06, bit 7 = 0)."

exit 0
