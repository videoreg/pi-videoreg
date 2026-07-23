#!/bin/bash
#
# systemd shutdown hook for PiSugar battery.
# Called by systemd at system poweroff (argument "poweroff") or reboot (argument "reboot").
# On reboot — exits immediately without touching the hardware.
# On poweroff — if external power is connected AND a wakeup alarm is set to a
#   future time, the poweroff is converted into a forced reboot (reboot -f) so
#   the device stays online while on external power instead of relying on the
#   wakeup alarm (rescheduling it here proved unreliable). Otherwise sends a
#   delayed power-cut command to the PiSugar via I2C: disables write protection,
#   sets the power-cut delay, clears the "auto power-on" bit in the power
#   register, then re-enables write protection.
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
REG_ALARM=0x40
REG_ALARM_WEEKDAY=0x44
REG_ALARM_HOUR=0x45
REG_ALARM_MIN=0x46
REG_ALARM_SEC=0x47

bcd_to_dec() {
    local val=$(printf "%d" $1)
    echo $(( (val / 16) * 10 + (val % 16) ))
}

# If external power is connected and a wakeup alarm is scheduled for the future,
# convert this poweroff into a forced reboot: the device should stay online
# while on external power instead of cycling through poweroff/wakeup.
POWER_REG=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_POWER)
IS_CHARGING=$(( (POWER_REG >> 7) & 1 ))

if [ $IS_CHARGING -eq 1 ]; then
    ALARM_REG=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_ALARM)
    IS_ALARM_ENABLED=$(( (ALARM_REG >> 7) & 1 ))

    if [ $IS_ALARM_ENABLED -eq 1 ]; then
        ALARM_WEEKDAY=$(printf "%d" $(i2cget -y $I2C_BUS $I2C_ADDR $REG_ALARM_WEEKDAY))
        ALARM_HOUR=$(bcd_to_dec $(i2cget -y $I2C_BUS $I2C_ADDR $REG_ALARM_HOUR))
        ALARM_MIN=$(bcd_to_dec $(i2cget -y $I2C_BUS $I2C_ADDR $REG_ALARM_MIN))
        ALARM_SEC=$(bcd_to_dec $(i2cget -y $I2C_BUS $I2C_ADDR $REG_ALARM_SEC))

        CURRENT_DATE_UTC=$(TZ=UTC date +"%Y-%m-%d")
        CURRENT_TS=$(date +%s)
        CURRENT_DOW=$(TZ=UTC date -d "$CURRENT_DATE_UTC" +%w)
        ALARM_TIME="${ALARM_HOUR}:${ALARM_MIN}:${ALARM_SEC}"

        NEXT_ALARM_TS=""
        TODAY_BIT=$((1 << CURRENT_DOW))
        if [ $((ALARM_WEEKDAY & TODAY_BIT)) -ne 0 ]; then
            TODAY_TARGET=$(TZ=UTC date -d "$CURRENT_DATE_UTC $ALARM_TIME" +%s 2>/dev/null)
            if [ $? -eq 0 ] && [ "$TODAY_TARGET" -gt "$CURRENT_TS" ]; then
                NEXT_ALARM_TS=$TODAY_TARGET
            fi
        fi

        if [ -z "$NEXT_ALARM_TS" ]; then
            for offset in 1 2 3 4 5 6 7; do
                CHECK_DOW=$(( (CURRENT_DOW + offset) % 7 ))
                CHECK_BIT=$((1 << CHECK_DOW))
                if [ $((ALARM_WEEKDAY & CHECK_BIT)) -ne 0 ]; then
                    NEXT_ALARM_TS=$(date -d "$CURRENT_DATE_UTC +${offset} days $ALARM_TIME UTC" +%s)
                    break
                fi
            done
        fi

        if [ -n "$NEXT_ALARM_TS" ] && [ "$NEXT_ALARM_TS" -gt "$CURRENT_TS" ]; then
            # Cancel the delayed power-cut previously armed by task/pisugar.sh
            # `shutdown` (clears bit 5 of REG_POWER) — set bit 5 back so the
            # PiSugar does not cut power mid-reboot.
            i2cset -y $I2C_BUS $I2C_ADDR $REG_WRITE_PROTECT 0x29
            CURRENT_POWER=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_POWER)
            RESTORED_POWER=$(printf "0x%x" $(( CURRENT_POWER | 0x20 )))
            i2cset -y $I2C_BUS $I2C_ADDR $REG_POWER $RESTORED_POWER
            i2cset -y $I2C_BUS $I2C_ADDR $REG_WRITE_PROTECT 0x00

            exec reboot -f
        fi
    fi
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