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

# How long past the PiSugar countdown we keep waiting for the cut before
# concluding it is not going to happen. The countdown has 1s resolution.
CUT_DEADLINE_MARGIN_SECONDS=3
CUT_POLL_DELAY=0.2

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
ARMED_DELAY=""
ARMED_TS=""

if [ -f "$STATE_FILE" ]; then
    while IFS='=' read -r key value; do
        case "$key" in
            decision) DECISION="$value" ;;
            power_byte) POWER_BYTE="$value" ;;
            charging) CHARGING="$value" ;;
            alarm_in_future) ALARM_IN_FUTURE="$value" ;;
            armed) ARMED="$value" ;;
            force_powercut) FORCE_POWERCUT="$value" ;;
            delay) ARMED_DELAY="$value" ;;
            ts) ARMED_TS="$value" ;;
        esac
    done < "$STATE_FILE"
fi

# Whether external power was seen when the poweroff was decided. Captured before
# the samples below can add to it: a cut armed while on battery is expected to
# take the power away, a cut armed on external power (a manual poweroff, a
# BLE-beacon shutdown) may legitimately end in a halt.
ON_POWER_AT_DECISION="$CHARGING"

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

# Stay up until the armed cut takes the power away, instead of returning and
# letting Linux halt with the cut still pending.
#
# External power that appears in the last seconds before the cut — after every
# sample above — is the one case nothing else covers: the PiSugar does not leave
# the board in a state the power-restore wake or the RTC alarm can start, and
# the device stays dark until someone power-cycles it (2026-10-04, 10-12, 10-14
# and 10-16 on a test device with power scheduled at 07:00/13:00/19:00, every
# time with the cut falling 1-4s after the power came back).
#
# So, while waiting:
#   charging shows up    -> the power is back, cancel the cut and reboot
#   past the deadline    -> we are still running, so the cut did not happen;
#                           cancel it and reboot rather than halt for good
# A reboot here is safe: the filesystems are already unmounted. A cut that does
# fire simply ends this loop.
#
# Only for a cut decided on battery. One decided on external power (a manual
# poweroff, a BLE-beacon shutdown) keeps ending in a halt when the cut does not
# fire, as before — rebooting there would undo the poweroff that was asked for.
cancel_cut_and_reboot() {
    if [ -n "$POWER_BYTE" ]; then
        write_register $REG_POWER $(( POWER_BYTE | (1 << BIT_NUM_POWER_CUT) ))
    fi

    exec reboot -f
}

wait_for_cut() {
    local deadline="$1"
    local reg

    if [ "$ON_POWER_AT_DECISION" == "1" ] || [ "$FORCE_POWERCUT" == "yes" ]; then
        exit 0
    fi

    while [ "$(date +%s)" -lt "$deadline" ]; do
        reg=$(read_register $REG_POWER) || reg=""

        if [ -n "$reg" ] && [ $(( (reg >> BIT_NUM_CHARGIN_STATUS) & 1 )) -eq 1 ]; then
            POWER_BYTE=$(printf "0x%02x" $(( reg & ~(1 << BIT_NUM_POWER_CUT) )))
            cancel_cut_and_reboot
        fi

        sleep "$CUT_POLL_DELAY"
    done

    cancel_cut_and_reboot
}

if [ "$ARMED" == "yes" ]; then
    if [[ "$ARMED_TS" =~ ^[0-9]+$ ]] && [[ "$ARMED_DELAY" =~ ^[0-9]+$ ]]; then
        wait_for_cut $(( ARMED_TS + ARMED_DELAY + CUT_DEADLINE_MARGIN_SECONDS ))
    fi

    # Armed by a vrg-poweroff.sh that did not publish the countdown: no deadline
    # to hold the wait against, keep the old behaviour.
    exit 0
fi

if [ -z "$POWER_BYTE" ]; then
    # Nothing published and the bus is unreadable. Inventing a value is what
    # used to clear the charging and wakeup bits — leave the register alone.
    exit 0
fi

write_register $REG_SHUTDOWN_DELAY $DELAY_SECONDS
write_register $REG_POWER "$POWER_BYTE" || exit 0

wait_for_cut $(( $(date +%s) + DELAY_SECONDS + CUT_DEADLINE_MARGIN_SECONDS ))
