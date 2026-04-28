#!/bin/bash
#
# systemd shutdown hook for PiSugar battery.
# Called by systemd at system poweroff (argument "poweroff") or reboot (argument "reboot").
# On reboot — exits immediately without touching the hardware.
# On poweroff — if external power is connected, the poweroff is converted into a
#   forced reboot (reboot -f) so the device stays online while on external power
#   instead of relying on the wakeup alarm (which is unreliable when rescheduled
#   here). Otherwise sends a delayed power-cut command to the PiSugar via I2C:
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

REG_WRITE_PROTECT=0x0b
REG_SHUTDOWN_DELAY=0x09
REG_POWER=0x02

# If external power is connected, convert this poweroff into a forced reboot:
# the device should stay online while on external power.
POWER_REG=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_POWER)
IS_CHARGING=$(( (POWER_REG >> 7) & 1 ))

if [ $IS_CHARGING -eq 1 ]; then
    exec reboot -f
fi

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