#!/bin/bash
#
# Last-resort PiSugar power cut, run by systemd at the very end of shutdown with
# the mode as its first argument ("poweroff", "reboot", "halt", "kexec").
#
# During installation (tools/bin/vrg-install) this script is placed at:
#   /lib/systemd/system-shutdown/shutdown-pisugar.sh
# That location is the standard directory systemd scans for shutdown executables.
#
# By this point every process has been killed, the rootfs is read-only and
# journald is gone, so nothing here can be logged and every failure is invisible.
# Therefore this script decides nothing and computes nothing. All of that happens
# earlier, in task/service/vrg-poweroff.sh, which normally has already armed the
# cut; what is left here is a fallback for when it did not run.
#
# Everything needed comes from tmpfs, written while the system was healthy:
#   /run/vrg/pisugar-poweroff     handoff from vrg-poweroff.sh (this boot's decision)
#   /run/vrg/pisugar-power-byte   byte published at boot, used if the first is absent
#
# The single exception is one control read of REG_POWER. External power can
# appear during the shutdown — stopping the services can take tens of seconds —
# and this is the last moment at which that can still change the outcome. It is
# retried, and when it fails we fall back to the charging status measured
# earlier rather than assuming there is no power: an empty i2cget result is 0 in
# bash arithmetic, and treating that as "not charging" is exactly the silent
# misread this script used to make.
#
# The script is deliberately self-contained: the project directory may already be
# unmounted here, so nothing outside /run and the i2c-tools binaries is touched.
# The helpers below therefore duplicate their counterparts in task/pisugar.sh.

set -u

case "${1-}" in
    reboot|kexec)
        exit 0
        ;;
esac

I2C_BUS=1 # I2C Bus number (usually 1 on Raspberry Pi)
I2C_ADDR=0x57 # PiSugar I2C Device Address (0x57 often used for PiSugar 3-series write protect)

REG_WRITE_PROTECT=0x0b
REG_SHUTDOWN_DELAY=0x09
REG_POWER=0x02

BIT_NUM_POWER_CUT=5
BIT_NUM_CHARGIN_STATUS=7

DELAY_SECONDS=10

I2C_RETRY_COUNT=5
I2C_RETRY_DELAY=0.05

STATE_FILE="/run/vrg/pisugar-poweroff"
POWER_BYTE_FILE="/run/vrg/pisugar-power-byte"

# Read a register, retrying transient bus errors. Prints decimal, non-zero exit
# when the register could not be read at all — never an empty "value".
read_register() {
    local reg="$1"
    local attempt=0
    local raw=""

    while [ "$attempt" -lt "$I2C_RETRY_COUNT" ]; do
        raw=$(i2cget -y "$I2C_BUS" "$I2C_ADDR" "$reg" 2>/dev/null)

        if [[ "$raw" =~ ^0[xX][0-9a-fA-F]+$ ]]; then
            printf "%d" "$raw"
            return 0
        fi

        attempt=$((attempt + 1))
        sleep "$I2C_RETRY_DELAY"
    done

    return 1
}

# Write with write protection lifted and confirm by reading back. The read-back
# also covers a failed unlock: without 0x29 in 0x0b the write is ignored.
write_register() {
    local reg="$1"
    local target=$(( $2 ))
    local attempt=0
    local readback=""

    while [ "$attempt" -lt "$I2C_RETRY_COUNT" ]; do
        i2cset -y "$I2C_BUS" "$I2C_ADDR" "$REG_WRITE_PROTECT" 0x29 2>/dev/null
        i2cset -y "$I2C_BUS" "$I2C_ADDR" "$reg" "$(printf '0x%02x' "$target")" 2>/dev/null
        readback=$(read_register "$reg") || readback=""
        i2cset -y "$I2C_BUS" "$I2C_ADDR" "$REG_WRITE_PROTECT" 0x00 2>/dev/null

        if [ -n "$readback" ] && [ "$readback" -eq "$target" ]; then
            return 0
        fi

        attempt=$((attempt + 1))
        sleep "$I2C_RETRY_DELAY"
    done

    return 1
}

DECISION="unknown"
POWER_BYTE=""
CHARGING=0
ALARM_IN_FUTURE=0
ARMED="no"
FORCE_POWERCUT="no"

if [ -f "$STATE_FILE" ]; then
    while IFS='=' read -r key value; do
        case "$key" in
            decision) DECISION="$value" ;;
            power_byte) POWER_BYTE="$value" ;;
            charging) CHARGING="$value" ;;
            alarm_in_future) ALARM_IN_FUTURE="$value" ;;
            armed) ARMED="$value" ;;
            force_powercut) FORCE_POWERCUT="$value" ;;
        esac
    done < "$STATE_FILE"
fi

if [ -z "$POWER_BYTE" ] && [ -f "$POWER_BYTE_FILE" ]; then
    POWER_BYTE=$(cat "$POWER_BYTE_FILE" 2>/dev/null)
fi

# The last chance to notice that external power came back during the shutdown.
CURRENT_POWER_REG=$(read_register $REG_POWER)
if [ $? -eq 0 ]; then
    CHARGING=$(( (CURRENT_POWER_REG >> BIT_NUM_CHARGIN_STATUS) & 1 ))
    POWER_BYTE=$(printf "0x%02x" $(( CURRENT_POWER_REG & ~(1 << BIT_NUM_POWER_CUT) )))
fi

# On external power with a pending wakeup alarm, stay online: reboot instead of
# cutting power. Safe here because the filesystems are already unmounted.
# Exception: a BLE-beacon-forced shutdown (force_powercut=yes, set by
# vrg-poweroff.sh) must actually power off and wait for the RTC alarm — the
# beacon is gone though external power stayed — so we let the armed cut proceed.
if [ "$FORCE_POWERCUT" != "yes" ] && [ "$CHARGING" == "1" ] && [ "$ALARM_IN_FUTURE" == "1" ]; then
    if [ "$ARMED" == "yes" ] && [ -n "$POWER_BYTE" ]; then
        # vrg-poweroff.sh armed the cut before the power appeared — undo it, or
        # the PiSugar will pull power in the middle of the reboot.
        write_register $REG_POWER $(( POWER_BYTE | (1 << BIT_NUM_POWER_CUT) ))
    fi

    exec reboot -f
fi

if [ "$ARMED" == "yes" ]; then
    exit 0
fi

if [ -z "$POWER_BYTE" ]; then
    # Nothing was published and the bus is unreadable: there is no value we could
    # write without inventing one, and inventing one is what used to clear the
    # charging and wakeup bits. Leave the register alone.
    exit 0
fi

write_register $REG_SHUTDOWN_DELAY $DELAY_SECONDS
write_register $REG_POWER "$POWER_BYTE"

# bye bye
