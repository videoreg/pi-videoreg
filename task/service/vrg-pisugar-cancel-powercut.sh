#!/bin/bash
#
# Boot-time counterpart of task/service/vrg-poweroff.sh.
#
# Does three things, all of them cheap and all of them safe to repeat:
#
# 1. Cancels a power cut that was armed but never carried out. The PiSugar keeps
#    counting down regardless of what the Pi does afterwards, so a poweroff that
#    turned into a reboot — the on-external-power case, or a watchdog reset —
#    would otherwise have its power pulled seconds into the new boot. Cancelling
#    here unconditionally is what makes arming aggressively safe.
#
# 2. Publishes /run/vrg/pisugar-power-byte: the byte that arms the cut, read in a
#    healthy system. If a later shutdown never reaches vrg-poweroff.service
#    (panic, `reboot -f` from outside), the shutdown hook still has a valid value
#    and never has to compute one from a bus read that may fail.
#
# 3. Reports charging-enabled and wakeup-on-power-restore, restoring them if they
#    are off. Both bits being clear is the signature of a REG_POWER write derived
#    from a failed read — the failure mode this whole path was rebuilt to remove.
#    Since nothing can be logged during the last shutdown phase, catching it on
#    the next boot is the only way to learn that it happened.

set -u

VIDEOREG_PROJECT_HOME=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --videoreg-project-home)
            VIDEOREG_PROJECT_HOME="${2-}"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            echo "Usage: $0 --videoreg-project-home <path>"
            exit 1
            ;;
    esac
done

if [ -z "$VIDEOREG_PROJECT_HOME" ] || [ ! -d "$VIDEOREG_PROJECT_HOME" ]; then
    echo "Error: --videoreg-project-home is missing or not a directory"
    exit 1
fi

PISUGAR="$VIDEOREG_PROJECT_HOME/task/pisugar.sh"

RUNTIME_DIR="/run/vrg"
POWER_BYTE_FILE="$RUNTIME_DIR/pisugar-power-byte"

LOG_DIR="$VIDEOREG_PROJECT_HOME/.videoreg/log/services"
LOG_FILE="$LOG_DIR/vrg-pisugar-cancel-powercut.log"

log() {
    local line
    line="$(date +"%Y-%m-%d %H:%M:%S") vrg-pisugar-cancel-powercut: $1"
    echo "$line"
    mkdir -p "$LOG_DIR" 2>/dev/null
    echo "$line" >> "$LOG_FILE" 2>/dev/null
}

FLAGS=$(bash "$PISUGAR" get_power_flags 2>/dev/null)
if [ $? -ne 0 ] || [ -z "$FLAGS" ]; then
    log "no PiSugar on the bus, nothing to do"
    exit 0
fi

power_reg=""
charging_enabled=""
wakeup_on_power_restore=""
power_cut_armed=""

while IFS='=' read -r key value; do
    case "$key" in
        power_reg) power_reg="$value" ;;
        charging_enabled) charging_enabled="$value" ;;
        wakeup_on_power_restore) wakeup_on_power_restore="$value" ;;
        power_cut_armed) power_cut_armed="$value" ;;
    esac
done <<< "$FLAGS"

log "power_reg=$power_reg power_cut_armed=$power_cut_armed charging_enabled=$charging_enabled wakeup_on_power_restore=$wakeup_on_power_restore"

if [ "$power_cut_armed" == "1" ]; then
    if bash "$PISUGAR" cancel_powercut > /dev/null 2>&1; then
        log "cancelled a power cut left armed by the previous shutdown"
    else
        log "FAILED to cancel the armed power cut, power may be cut shortly"
    fi
fi

if [ "$charging_enabled" == "0" ]; then
    log "WARNING charging was disabled in REG_POWER, restoring"
    bash "$PISUGAR" set_charging_enabled 1 > /dev/null 2>&1
fi

if [ "$wakeup_on_power_restore" == "0" ]; then
    log "WARNING wakeup on power restore was disabled in REG_POWER, restoring"
    bash "$PISUGAR" set_wakeup_on_power_restore 1 > /dev/null 2>&1
fi

POWER_BYTE=$(bash "$PISUGAR" get_powercut_byte 2>/dev/null)
if [ $? -ne 0 ] || [ -z "$POWER_BYTE" ]; then
    log "cannot read the power cut byte to publish"
elif mkdir -p "$RUNTIME_DIR" 2>/dev/null && echo "$POWER_BYTE" > "$POWER_BYTE_FILE" 2>/dev/null; then
    log "published power cut byte $POWER_BYTE"
else
    log "FAILED to write power cut byte to $POWER_BYTE_FILE"
fi

exit 0
