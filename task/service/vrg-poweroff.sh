#!/bin/bash
#
# Arms the PiSugar delayed power cut on poweroff.
#
# Runs as ExecStop of vrg-poweroff.service. Because that unit is ordered
# Before=basic.target, and systemd stops units in reverse start order, this runs
# after every other service has stopped — but while journald, local filesystems
# and the I2C bus are all still healthy. That is the whole point: the decision
# and the register writes happen in a working system with retries and a log,
# instead of in /lib/systemd/system-shutdown, where the rootfs is read-only,
# journald is dead and a failed read is invisible.
#
# It handles every poweroff regardless of who started it — the power plugin,
# `sudo poweroff` over ssh, the web UI — because it is triggered by the shutdown
# transaction itself rather than by videoreg code.
#
# Hands off to /run/vrg/pisugar-poweroff so that
# /lib/systemd/system-shutdown/shutdown-pisugar.sh needs no bus reads of its own:
#
#   decision=powercut|reboot|unknown
#   power_byte=0x..      byte that arms the cut, computed from a healthy read
#   charging=1|0         charging status observed here
#   alarm_in_future=1|0  a wakeup alarm is enabled and scheduled ahead of now
#   armed=yes|no         whether the cut was armed and verified here
#   force_powercut=yes|no  BLE-beacon shutdown: cut power even while charging
#   ts=<epoch>
#
# On external power with a future wakeup alarm the poweroff is turned into a
# reboot instead — the device should stay online while it has power. The one
# exception is a BLE-beacon-forced shutdown (force_powercut=yes): there the
# beacon vanished while external power stayed, and the device must actually power
# off and wait for the RTC alarm, so the cut is armed despite charging. The reboot
# itself is left to the shutdown hook (`reboot -f`), which runs once filesystems
# are already unmounted; issuing it here, mid-transaction with everything still
# mounted, would risk the filesystem.

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
STATE_FILE="$RUNTIME_DIR/pisugar-poweroff"

# The power plugin drops this marker (in its own data dir) right before a shutdown
# that must cut power despite external power being present — a vanished BLE beacon,
# where only the RTC alarm brings the device back. Honoured only when fresh, so a
# leftover marker cannot force a cut on an unrelated shutdown.
FORCE_POWERCUT_MARKER="$VIDEOREG_PROJECT_HOME/.videoreg/data/plugins/org_vrg_power/force-powercut"
FORCE_POWERCUT_MAX_AGE_SECONDS=120
FORCE_POWERCUT=no

LOG_DIR="$VIDEOREG_PROJECT_HOME/.videoreg/log/services"
LOG_FILE="$LOG_DIR/vrg-poweroff.log"

# Forced as short as it can safely be, overriding the pisugar.sh default. This
# ExecStop runs only after every other service has already stopped, so the sole
# thing left before the cut is the systemd teardown (unmount + halt, ~1-2s) —
# no service work can still be racing it. Keeping the delay minimal shrinks the
# window in which the OS is already down but power is not yet cut: if external
# power appears in that window the cut executes with power present, a state the
# PiSugar wakes from via neither the RTC alarm nor power-restore. The window is
# fixed in hardware and cannot be closed, only made as small as the teardown
# allows.
POWER_CUT_DELAY_SECONDS=4

log() {
    local line
    line="$(date +"%Y-%m-%d %H:%M:%S") vrg-poweroff: $1"
    echo "$line"
    mkdir -p "$LOG_DIR" 2>/dev/null
    echo "$line" >> "$LOG_FILE" 2>/dev/null
}

write_state() {
    local decision="$1"
    local power_byte="$2"
    local charging="$3"
    local alarm_in_future="$4"
    local armed="$5"

    mkdir -p "$RUNTIME_DIR" 2>/dev/null

    cat > "$STATE_FILE" <<EOF
decision=$decision
power_byte=$power_byte
charging=$charging
alarm_in_future=$alarm_in_future
armed=$armed
force_powercut=$FORCE_POWERCUT
ts=$(date +%s)
EOF
}

# poweroff, reboot or a plain `systemctl stop` of this unit. When systemctl
# cannot answer, stay undecided rather than guess: the shutdown hook is told the
# actual mode by systemd in its first argument and can still act on it.
get_shutdown_mode() {
    local jobs

    jobs=$(systemctl list-jobs --no-legend 2>/dev/null) || return 1

    if grep -qE '(poweroff|halt)\.target' <<< "$jobs"; then
        echo "poweroff"
    elif grep -qE '(reboot|kexec)\.target' <<< "$jobs"; then
        echo "reboot"
    else
        echo "none"
    fi

    return 0
}

# A wakeup alarm that is enabled and still ahead of us. Only meaningful together
# with charging: it is what makes staying online preferable to powering off.
is_alarm_in_future() {
    local enabled
    local alarm_time
    local alarm_ts

    enabled=$(bash "$PISUGAR" get_alarm_wakeup_enabled 2>/dev/null) || return 1
    if [ "$enabled" != "true" ]; then
        echo "0"
        return 0
    fi

    alarm_time=$(bash "$PISUGAR" get_alarm_wakeup_time 2>/dev/null) || return 1
    alarm_ts=$(date -d "$alarm_time" +%s 2>/dev/null) || return 1

    if [ "$alarm_ts" -gt "$(date +%s)" ]; then
        echo "1"
    else
        echo "0"
    fi

    return 0
}

# The power plugin's BLE-beacon handoff: cut power even though external power is
# present. Only honoured when the marker is fresh, so a marker left behind by an
# earlier beacon shutdown cannot force a cut on a later, unrelated poweroff.
is_force_powercut() {
    [ -f "$FORCE_POWERCUT_MARKER" ] || return 1

    local mtime now
    mtime=$(stat -c %Y "$FORCE_POWERCUT_MARKER" 2>/dev/null) || return 1
    now=$(date +%s)

    [ $(( now - mtime )) -le "$FORCE_POWERCUT_MAX_AGE_SECONDS" ]
}

MODE=$(get_shutdown_mode) || MODE="unknown"

if [ "$MODE" == "reboot" ] || [ "$MODE" == "none" ]; then
    log "nothing to do (mode=$MODE)"
    exit 0
fi

# No PiSugar on the bus, or the bus is unusable — either way there is nothing to
# arm, and the machine is powered by something that does not need us.
POWER_BYTE=$(bash "$PISUGAR" get_powercut_byte 2>/dev/null)
if [ $? -ne 0 ] || [ -z "$POWER_BYTE" ]; then
    log "cannot read power register, skipping (mode=$MODE)"
    exit 0
fi

CHARGING_RAW=$(bash "$PISUGAR" get_charging_status 2>/dev/null) || CHARGING_RAW="unknown"
CHARGING=0
if [ "$CHARGING_RAW" == "true" ]; then
    CHARGING=1
fi

ALARM_IN_FUTURE=$(is_alarm_in_future) || ALARM_IN_FUTURE=0

if is_force_powercut; then
    FORCE_POWERCUT=yes
fi

log "mode=$MODE power_byte=$POWER_BYTE charging=$CHARGING_RAW alarm_in_future=$ALARM_IN_FUTURE force_powercut=$FORCE_POWERCUT"

if [ "$MODE" == "unknown" ]; then
    # Could not tell poweroff from reboot. Publish what we measured and leave the
    # arming to the hook, which systemd tells the real mode.
    write_state "unknown" "$POWER_BYTE" "$CHARGING" "$ALARM_IN_FUTURE" "no"
    log "shutdown mode undetermined, leaving the decision to the shutdown hook"
    exit 0
fi

if [ "$FORCE_POWERCUT" != "yes" ] && [ "$CHARGING" -eq 1 ] && [ "$ALARM_IN_FUTURE" -eq 1 ]; then
    write_state "reboot" "$POWER_BYTE" "$CHARGING" "$ALARM_IN_FUTURE" "no"
    log "on external power with a pending alarm: the shutdown hook will reboot instead"
    exit 0
fi

if [ "$FORCE_POWERCUT" == "yes" ]; then
    log "force-powercut marker present (BLE beacon): arming the cut despite charging=$CHARGING"
fi

if bash "$PISUGAR" arm_powercut "$POWER_CUT_DELAY_SECONDS" > /dev/null 2>&1; then
    write_state "powercut" "$POWER_BYTE" "$CHARGING" "$ALARM_IN_FUTURE" "yes"
    log "power cut armed and verified (delay=${POWER_CUT_DELAY_SECONDS}s)"
else
    write_state "powercut" "$POWER_BYTE" "$CHARGING" "$ALARM_IN_FUTURE" "no"
    log "FAILED to arm the power cut, the shutdown hook will retry"
fi

exit 0
