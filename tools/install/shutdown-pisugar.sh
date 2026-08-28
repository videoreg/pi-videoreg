#!/bin/bash
#
# Last-resort PiSugar power cut. systemd runs it at the very end of shutdown, as
# /lib/systemd/system-shutdown/shutdown-pisugar.sh (placed there by
# tools/bin/vrg-install), with the mode as $1: poweroff, reboot, halt or kexec.
#
# By this point every process is killed, the rootfs is read-only and journald is
# gone: nothing can be logged and every failure is invisible. So the script
# decides nothing. task/service/vrg-poweroff.sh has normally armed the cut
# already and handed its decision over through tmpfs:
#   /run/vrg/pisugar-poweroff     handoff from vrg-poweroff.sh (this boot's decision)
#   /run/vrg/pisugar-power-byte   byte published at boot, used if the first is absent
# What is left here is the fallback for when vrg-poweroff.sh did not run, plus a
# few control reads of REG_POWER — see the sampling loop below.
#
# Self-contained by design: the project directory may already be unmounted, so
# nothing outside /run and i2c-tools is touched and the helpers below duplicate
# their counterparts in task/pisugar.sh.

set -u

case "${1-}" in
    reboot|kexec)
        exit 0
        ;;
esac

I2C_BUS=1 # usually 1 on Raspberry Pi
I2C_ADDR=0x57 # PiSugar 3-series

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
# when the register could not be read at all — never an empty "value": empty is 0
# in bash arithmetic, and a silent "not charging" is exactly the misread that
# this script used to make.
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

# The last chance to notice external power that appeared during the shutdown —
# stopping the services can take tens of seconds.
#
# Sampled more than once, and the samples may only add power, never take it away:
#
#   charging_status means "current is flowing into the battery", not "a charger
#   is attached", so it drops on its own whenever the charger idles — a full
#   battery does that continuously — and a corrupted i2cget answer is
#   indistinguishable from a real change.
#
#   Withdrawing a decision is worse than making the wrong one. vrg-poweroff.sh
#   deliberately leaves the cut unarmed when it decides to reboot; if one sample
#   overrules that, we arm a cut that will not fire, because the power really is
#   still there. Linux halts, the rails stay live, nothing power-cycles the board
#   and the RTC alarm has nothing to start. Recoverable only by hand.
#
# Seeing power that is not there costs one wasted boot: the machine comes up,
# notices the power loss and shuts down again, this time with everything armed.
CHARGING_SAMPLE_COUNT=3
CHARGING_SAMPLE_DELAY=0.2

sample=0
while [ "$sample" -lt "$CHARGING_SAMPLE_COUNT" ]; do
    CURRENT_POWER_REG=$(read_register $REG_POWER) || CURRENT_POWER_REG=""

    if [ -n "$CURRENT_POWER_REG" ]; then
        POWER_BYTE=$(printf "0x%02x" $(( CURRENT_POWER_REG & ~(1 << BIT_NUM_POWER_CUT) )))

        if [ $(( (CURRENT_POWER_REG >> BIT_NUM_CHARGIN_STATUS) & 1 )) -eq 1 ]; then
            CHARGING=1
            break
        fi
    fi

    sample=$((sample + 1))
    sleep "$CHARGING_SAMPLE_DELAY"
done

# On external power with a pending wakeup alarm, stay online: reboot instead of
# cutting power. Safe here because the filesystems are already unmounted.
# Exception: a BLE-beacon-forced shutdown (force_powercut=yes) must power off and
# wait for the RTC alarm, so its armed cut proceeds.
if [ "$FORCE_POWERCUT" != "yes" ] && [ "$CHARGING" == "1" ] && [ "$ALARM_IN_FUTURE" == "1" ]; then
    if [ "$ARMED" == "yes" ] && [ -n "$POWER_BYTE" ]; then
        # Armed before the power appeared — undo it, or the PiSugar will pull
        # power in the middle of the reboot.
        write_register $REG_POWER $(( POWER_BYTE | (1 << BIT_NUM_POWER_CUT) ))
    fi

    exec reboot -f
fi

if [ "$ARMED" == "yes" ]; then
    exit 0
fi

if [ -z "$POWER_BYTE" ]; then
    # Nothing published and the bus is unreadable. Inventing a value is what
    # used to clear the charging and wakeup bits — leave the register alone.
    exit 0
fi

write_register $REG_SHUTDOWN_DELAY $DELAY_SECONDS
write_register $REG_POWER "$POWER_BYTE"
