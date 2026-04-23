#!/bin/bash
#
# systemd shutdown hook for PiSugar battery.
# Called by systemd at system poweroff (argument "poweroff") or reboot (argument "reboot").
# On reboot — exits immediately without touching the hardware.
# On poweroff — sends a delayed power-cut command to the PiSugar via I2C:
#   disables write protection, sets the power-cut delay, clears the "auto power-on"
#   bit in the power register, then re-enables write protection.
#
# During installation (tools/bin/vrg-install) this script is placed at:
#   /lib/systemd/system-shutdown/shutdown-pisugar.sh
# That location is the standard directory systemd scans for shutdown executables.
#

[ "$1" == "reboot" ] && exit 0

I2C_BUS=1 # I2C Bus number (usually 1 on Raspberry Pi)
I2C_ADDR=0x57 # PiSugar I2C Device Address (0x57 often used for PiSugar 3-series write protect)

DELAY_SECONDS=3

# local DELAY_SECONDS=${1:-7}
# if (( DELAY_SECONDS < 0 || DELAY_SECONDS > 255 )); then
#     echo "Error: Shutdown delay time ($DELAY_SECONDS seconds) is out of the valid range (0-255)."
#     exit 1
# fi

REG_WRITE_PROTECT=0x0b
REG_SHUTDOWN_DELAY=0x09
REG_POWER=0x02

# Disable Write Protection (Write 0x29 to 0x0b)
i2cset -y $I2C_BUS $I2C_ADDR $REG_WRITE_PROTECT 0x29

# Set the desired delay time (Write DELAY_SECONDS to 0x09)
DELAY_HEX=$(printf "0x%x" $DELAY_SECONDS)
i2cset -y $I2C_BUS $I2C_ADDR $REG_SHUTDOWN_DELAY $DELAY_HEX

# Read original value of 0x02 register
ORIGINAL_VAL_HEX=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_POWER b)
# Clear Bit 5 of 0x02 to enable delayed shutdown
NEW_VAL_DEC=$(( ORIGINAL_VAL_HEX & 0xDF ))
NEW_VAL_HEX=$(printf "0x%x" $NEW_VAL_DEC)

i2cset -y $I2C_BUS $I2C_ADDR $REG_POWER $NEW_VAL_HEX

# Enable Write Protection (Write 0x00 to 0x0b)
i2cset -y $I2C_BUS $I2C_ADDR $REG_WRITE_PROTECT 0x00

# bye bye