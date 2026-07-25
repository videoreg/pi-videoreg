#!/bin/bash
#
# PiSugar 3 management script — communicates with the PiSugar 3 power module via I2C.
#
# Provides CLI access to PiSugar registers: battery level, charging status,
# RTC clock (read/write), alarm wakeup (schedule + enable/disable),
# wakeup-on-power-restore flag, charging protection, and graceful shutdown.
#
# All RTC and alarm registers use BCD encoding. Alarm weekday is a 7-bit bitmask
# (bit 0 = Sunday … bit 6 = Saturday). Write operations temporarily disable
# the write-protect register (0x0b) and re-enable it after.
#
# Every register access goes through read_register/write_register, which retry
# transient bus errors and confirm writes by reading them back. A command that
# could not read what it needed exits non-zero and prints nothing, so callers
# never mistake a bus failure for a valid value.
#
# Usage: pisugar.sh <command> [arguments]
# Run without arguments or with an unknown command to see available commands.

set -u

# Check if i2c-tools is installed
if ! command -v i2cset &> /dev/null || ! command -v i2cget &> /dev/null; then
    echo "Error: i2cget or i2cset command not found. Please install i2c-tools package."
    exit 1
fi

I2C_BUS=1 # I2C Bus number (usually 1 on Raspberry Pi)
I2C_ADDR=0x57 # PiSugar I2C Device Address (0x57 often used for PiSugar 3-series write protect)

# REGISTERS

REG_WRITE_PROTECT=0x0b
BIT_NUM=7

# POWER
REG_POWER=0x02
BIT_NUM_WAKEUP_ON_POWER_RESTORE=4
BIT_NUM_POWER_CUT=5 # 0 = power cut armed, cut happens after REG_SHUTDOWN_DELAY
BIT_NUM_CHARGING_ENABLED=6
BIT_NUM_CHARGIN_STATUS=7

REG_SHUTDOWN_DELAY=0x09

# Conservative default delay between arming the power cut and the PiSugar
# actually cutting power. Used when arm_powercut is called from userspace while
# the system may still be running, so it must outlast whatever services still
# need to finish. The real shutdown path (vrg-poweroff.service) overrides this
# with a much shorter value, because by the time its ExecStop arms the cut every
# service has already stopped.
POWER_CUT_DELAY_SECONDS=15

# CHARGING PROTECTION
REG_CHARGING_PROTECTION=0x20
BIT_NUM_CHARGING_PROTECTION=7

# TEMP
REG_TEMP=0x04

# RTC
REG_RTC_YEAR=0x31
REG_RTC_MONTH=0x32
REG_RTC_DAY=0x33
REG_RTC_WEEKDAY=0x34
REG_RTC_HOUR=0x35
REG_RTC_MIN=0x36
REG_RTC_SEC=0x37

# BATTERY
REG_BAT_LEVEL=0x2A

# ALARM
REG_ALARM=0x40
BIT_NUM_ALARM_ENABLED=7

REG_ALARM_WEEKDAY=0x44
REG_ALARM_HOUR=0x45
REG_ALARM_MIN=0x46
REG_ALARM_SEC=0x47

# I2C ACCESS
#
# The PiSugar MCU shares the bus and NACKs while it is busy, so any single
# i2cget/i2cset can fail at any moment. Two rules follow, and both matter most on
# the shutdown path:
#
# 1. Never derive a value from a failed read. An empty i2cget result is 0 in bash
#    arithmetic, so `<empty> & 0xDF` is 0x00 — writing that to REG_POWER clears
#    not only the power-cut bit but also charging-enabled and
#    wakeup-on-power-restore, leaving the device unable to charge or wake.
# 2. Confirm every write by reading it back. This also covers a failed unlock:
#    if 0x0b never took 0x29, the write is silently ignored by the MCU.

I2C_RETRY_COUNT=5
I2C_RETRY_DELAY=0.05

BUS_LOCK_FILE="/run/lock/vrg-pisugar.lock"
BUS_LOCK_WAIT_SEC=5

# Serialize register access across processes. vrg-pisugar-watchdog.sh feeds the
# watchdog every 5 seconds; an unlucky interleaving drops another process's write
# or re-enables write protection in the middle of its sequence. The lock is held
# for the lifetime of the process through fd 9. It is skipped rather than fatal
# when the lock file cannot be created, and nested invocations do not re-lock.
acquire_bus_lock() {
    if [ -n "${VRG_PISUGAR_BUS_LOCKED-}" ]; then
        return 0
    fi

    if ! exec 9>"$BUS_LOCK_FILE" 2>/dev/null; then
        return 0
    fi

    export VRG_PISUGAR_BUS_LOCKED=1
    flock -w "$BUS_LOCK_WAIT_SEC" 9 2>/dev/null || true
}

# Read a register, retrying transient bus errors. Prints the value in decimal,
# exits non-zero when the register could not be read at all.
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

# Write a register with write protection lifted, then confirm it by reading back.
# The whole unlock/write/lock sequence is the retry unit, because a half-applied
# sequence is exactly what we are protecting against.
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

# Set or clear a single bit, preserving the rest of the register.
write_register_bit() {
    local reg="$1"
    local bit="$2"
    local value="$3"
    local current
    local target

    current=$(read_register "$reg") || return 1

    if [ "$value" -eq 1 ]; then
        target=$(( current | (1 << bit) ))
    else
        target=$(( current & ~(1 << bit) ))
    fi

    write_register "$reg" "$target"
}

# Print bit $2 of register $1 as true/false.
read_register_bit_bool() {
    local reg="$1"
    local bit="$2"
    local current

    current=$(read_register "$reg") || return 1

    if [ $(( (current >> bit) & 1 )) -eq 1 ]; then
        echo "true"
    else
        echo "false"
    fi
}

shutdown() {
    # Only asks the OS to go down. The power cut is armed by vrg-poweroff.service
    # (see task/service/vrg-poweroff.sh), which runs once every other service has
    # stopped but while the system is still healthy enough to read the bus, retry
    # and log. Arming here instead would start the countdown before the teardown,
    # which on a slow shutdown can cut power in the middle of unmounting.
    sudo systemd-run --on-active=1s --timer-property=AccuracySec=1s shutdown now
}

# Arm the delayed power cut. Prints the byte written to REG_POWER so the caller
# can hand it to the last-resort shutdown hook, which must not read the bus.
arm_powercut() {
    local delay="${1:-$POWER_CUT_DELAY_SECONDS}"
    local current
    local target

    current=$(read_register $REG_POWER)
    if [ $? -ne 0 ]; then
        echo "Error: cannot read power register, refusing to arm" >&2
        return 1
    fi

    # A rejected delay is not fatal: the register keeps its previous value and the
    # cut still happens, just on a different schedule.
    if ! write_register $REG_SHUTDOWN_DELAY "$delay"; then
        echo "Warning: cannot set power cut delay, keeping the previous one" >&2
    fi

    target=$(( current & ~(1 << BIT_NUM_POWER_CUT) ))

    if ! write_register $REG_POWER "$target"; then
        echo "Error: cannot arm power cut" >&2
        return 1
    fi

    printf "0x%02x\n" "$target"
    return 0
}

# Cancel a power cut that was armed but never carried out — the case where a
# poweroff turned into a reboot. Runs at boot, see
# task/service/vrg-pisugar-cancel-powercut.sh.
cancel_powercut() {
    if ! write_register_bit $REG_POWER $BIT_NUM_POWER_CUT 1; then
        echo "Error: cannot cancel power cut" >&2
        return 1
    fi

    echo "ok"
    return 0
}

# The byte that arms the power cut, without writing it. Published at boot so the
# shutdown hook has a valid value even if nothing else ran during shutdown.
get_powercut_byte() {
    local current

    current=$(read_register $REG_POWER) || return 1

    printf "0x%02x\n" $(( current & ~(1 << BIT_NUM_POWER_CUT) ))
    return 0
}

# Full decode of REG_POWER, used by the boot-time health check.
get_power_flags() {
    local current

    current=$(read_register $REG_POWER) || return 1

    printf "power_reg=0x%02x\n" "$current"
    echo "charging_status=$(( (current >> BIT_NUM_CHARGIN_STATUS) & 1 ))"
    echo "charging_enabled=$(( (current >> BIT_NUM_CHARGING_ENABLED) & 1 ))"
    echo "wakeup_on_power_restore=$(( (current >> BIT_NUM_WAKEUP_ON_POWER_RESTORE) & 1 ))"
    echo "power_cut_armed=$(( ( (current >> BIT_NUM_POWER_CUT) & 1 ) ^ 1 ))"
    return 0
}

bcd_to_dec() {
    local val=$(printf "%d" $1)
    echo $(( (val / 16) * 10 + (val % 16) ))
}

# Decimal → BCD  
dec_to_bcd() {
    local dec=$1
    printf "0x%02x" $(( (dec / 10) * 16 + (dec % 10) ))
}

get_rtc_time() {
    local RAW_YEAR RAW_MONTH RAW_DAY RAW_HOUR RAW_MIN RAW_SEC

    # hwclock writes the year in BCD too, so every register is decoded the same way
    RAW_YEAR=$(read_register $REG_RTC_YEAR) || return 1
    RAW_MONTH=$(read_register $REG_RTC_MONTH) || return 1
    RAW_DAY=$(read_register $REG_RTC_DAY) || return 1
    RAW_HOUR=$(read_register $REG_RTC_HOUR) || return 1
    RAW_MIN=$(read_register $REG_RTC_MIN) || return 1
    RAW_SEC=$(read_register $REG_RTC_SEC) || return 1

    local REG_RTC_VALUE_YEAR=$(bcd_to_dec "$RAW_YEAR")
    local REG_RTC_VALUE_MONTH=$(bcd_to_dec "$RAW_MONTH")
    local REG_RTC_VALUE_DAY=$(bcd_to_dec "$RAW_DAY")

    local REG_RTC_VALUE_HOUR=$(bcd_to_dec "$RAW_HOUR")
    local REG_RTC_VALUE_MIN=$(bcd_to_dec "$RAW_MIN")
    local REG_RTC_VALUE_SEC=$(bcd_to_dec "$RAW_SEC")

    local RTC_RAW_DATETIME="20${REG_RTC_VALUE_YEAR}-${REG_RTC_VALUE_MONTH}-${REG_RTC_VALUE_DAY} ${REG_RTC_VALUE_HOUR}:${REG_RTC_VALUE_MIN}:${REG_RTC_VALUE_SEC}"

    echo $(date -d "${RTC_RAW_DATETIME} UTC" +"%Y-%m-%dT%H:%M:%S%:z")

    return 0
}

set_rtc_time() {
    local PARAM_DATETIME=${1-}

    if [ -z "$PARAM_DATETIME" ]; then
        echo "Usage: $0 <datetime>"
        echo "Example: $0 2020-01-01T16:30:50+03:00"
        exit 1
    fi

    if ! date -d "$PARAM_DATETIME" &>/dev/null; then
        echo "Invalid date"
        exit 1
    fi

    local YEAR=$(TZ=UTC date -d "$PARAM_DATETIME" +%y)
    local MONTH=$(TZ=UTC date -d "$PARAM_DATETIME" +%m)
    local DAY=$(TZ=UTC date -d "$PARAM_DATETIME" +%d)

    local WEEK_DAY=$(TZ=UTC date -d "$PARAM_DATETIME" +%u) # u w

    local HOUR=$(TZ=UTC date -d "$PARAM_DATETIME" +%H)
    local MIN=$(TZ=UTC date -d "$PARAM_DATETIME" +%M)
    local SEC=$(TZ=UTC date -d "$PARAM_DATETIME" +%S)

    # HEX

    # local YEAR_HEX=$(printf "0x%x\n" $YEAR) # all registers except year in BCD format
    local YEAR_HEX=$(dec_to_bcd $YEAR) # same as hwclock writes BCD to year also
    local MONTH_HEX=$(dec_to_bcd $MONTH)
    local DAY_HEX=$(dec_to_bcd $DAY)

    local WEEK_DAY_HEX=$(dec_to_bcd $WEEK_DAY)

    local HOUR_HEX=$(dec_to_bcd $HOUR)
    local MIN_HEX=$(dec_to_bcd $MIN)
    local SEC_HEX=$(dec_to_bcd $SEC)

    # Disable RW protect
    i2cset -y $I2C_BUS $I2C_ADDR $REG_WRITE_PROTECT 0x29

    # Write value
    i2cset -y $I2C_BUS $I2C_ADDR $REG_RTC_YEAR    $YEAR_HEX
    i2cset -y $I2C_BUS $I2C_ADDR $REG_RTC_MONTH   $MONTH_HEX
    i2cset -y $I2C_BUS $I2C_ADDR $REG_RTC_DAY     $DAY_HEX

    i2cset -y $I2C_BUS $I2C_ADDR $REG_RTC_WEEKDAY $WEEK_DAY_HEX

    i2cset -y $I2C_BUS $I2C_ADDR $REG_RTC_HOUR    $HOUR_HEX
    i2cset -y $I2C_BUS $I2C_ADDR $REG_RTC_MIN     $MIN_HEX
    i2cset -y $I2C_BUS $I2C_ADDR $REG_RTC_SEC     $SEC_HEX

    # Enable RW protect
    i2cset -y $I2C_BUS $I2C_ADDR $REG_WRITE_PROTECT 0x00

    echo "ok"

    return 0
}

get_bat_level() {
    local REG_VALUE

    REG_VALUE=$(read_register $REG_BAT_LEVEL) || return 1

    echo "$REG_VALUE"
    return 0
}

get_charging_status() {
    read_register_bit_bool $REG_POWER $BIT_NUM_CHARGIN_STATUS
}

get_charging_enabled() {
    read_register_bit_bool $REG_POWER $BIT_NUM_CHARGING_ENABLED
}

set_charging_enabled() {
    local TARGET_BIT_VALUE="${1-}"

    if [[ $TARGET_BIT_VALUE != "0" && $TARGET_BIT_VALUE != "1" ]]; then
        echo "Error: parameter must be 0 or 1" >&2
        exit 1
    fi

    if ! write_register_bit $REG_POWER $BIT_NUM_CHARGING_ENABLED "$TARGET_BIT_VALUE"; then
        echo "Error: cannot set charging enabled" >&2
        return 1
    fi

    echo "ok"

    return 0
}

get_temp() {
    local REG_VALUE

    REG_VALUE=$(read_register $REG_TEMP) || return 1

    echo $(( REG_VALUE - 40 ))
    return 0
}

get_alarm_wakeup_enabled() {
    read_register_bit_bool $REG_ALARM $BIT_NUM_ALARM_ENABLED
}

set_alarm_wakeup_enabled() {
    local TARGET_BIT_VALUE="${1-}"

    if [[ $TARGET_BIT_VALUE != "0" && $TARGET_BIT_VALUE != "1" ]]; then
        echo "Error: parameter must be 0 or 1" >&2
        exit 1
    fi

    if ! write_register_bit $REG_ALARM $BIT_NUM_ALARM_ENABLED "$TARGET_BIT_VALUE"; then
        echo "Error: cannot set alarm wakeup enabled" >&2
        return 1
    fi

    echo "ok"

    return 0
}

get_nearest_weekday_bitmask() {
    local bitmask="${1-}"  # 0-127 (binary: 0000000-1111111)
    local time="${2-}"     # HH:MM:SS (in UTC)

    # Validate bitmask
    if [ "$bitmask" -lt 0 ] || [ "$bitmask" -gt 127 ]; then
        echo "Error: bitmask must be between 0 and 127" >&2
        return 1
    fi

    if [ "$bitmask" -eq 0 ]; then
        echo "Error: no weekday selected" >&2
        return 1
    fi

    # Capture current UTC time once to avoid day boundary issues
    local current_date_utc=$(TZ=UTC date +"%Y-%m-%d")
    local current_ts=$(date +%s)
    local current_dow=$(TZ=UTC date -d "$current_date_utc" +%w)

    # Check if today is included in the bitmask
    local today_bit=$((1 << $current_dow))

    if [ $((bitmask & today_bit)) -ne 0 ]; then
        # Today matches, check the time
        local today_target=$(TZ=UTC date -d "$current_date_utc $time" +%s 2>/dev/null)

        if [ $? -eq 0 ] && [ $today_target -gt $current_ts ]; then
            # Time has not passed yet — return today (converted to local timezone)
            date -d "$current_date_utc $time UTC" +"%Y-%m-%dT%H:%M:%S%:z"
            return 0
        fi
    fi

    # Find the nearest day in the future
    for offset in {1..7}; do
        local check_dow=$(( (current_dow + offset) % 7 ))
        local check_bit=$((1 << check_dow))

        if [ $((bitmask & check_bit)) -ne 0 ]; then
            # This day matches (working in UTC, output in local timezone)
            date -d "$current_date_utc +${offset} days $time UTC" +"%Y-%m-%dT%H:%M:%S%:z"
            return 0
        fi
    done

    # Should never reach here, but just in case
    echo "Error: could not find a matching day" >&2
    return 1
}

get_alarm_wakeup_time() {
    local REG_VALUE_WEEKDAY RAW_HOUR RAW_MIN RAW_SEC

    REG_VALUE_WEEKDAY=$(read_register $REG_ALARM_WEEKDAY) || return 1
    RAW_HOUR=$(read_register $REG_ALARM_HOUR) || return 1
    RAW_MIN=$(read_register $REG_ALARM_MIN) || return 1
    RAW_SEC=$(read_register $REG_ALARM_SEC) || return 1

    local REG_VALUE_HOUR=$(bcd_to_dec "$RAW_HOUR")
    local REG_VALUE_MIN=$(bcd_to_dec "$RAW_MIN")
    local REG_VALUE_SEC=$(bcd_to_dec "$RAW_SEC")

    get_nearest_weekday_bitmask $REG_VALUE_WEEKDAY "${REG_VALUE_HOUR}:${REG_VALUE_MIN}:${REG_VALUE_SEC}"
}

set_alarm_wakeup_time() {
    local PARAM_DATETIME=${1-}
    local PARAM_WEEK_DAY=${2-}

    if [ -z "$PARAM_DATETIME" ] || [ -z "$PARAM_WEEK_DAY" ]; then
        echo "Usage: $0 <datetime> <number>"
        echo "Example: $0 2020-01-01T16:30:50+03:00 127"
        exit 1
    fi

    if ! date -u -d "$PARAM_DATETIME" &>/dev/null; then
        echo "Invalid date"
        exit 1
    fi

    # Validate week day value
    if [ "$PARAM_WEEK_DAY" -lt 0 ] || [ "$PARAM_WEEK_DAY" -gt 127 ]; then
        echo "Error: week day must be between 0 and 127" >&2
        return 1
    fi

    local ALARM_HOUR=$(date -u -d "$PARAM_DATETIME" +%-H)
    local ALARM_MIN=$(date -u -d "$PARAM_DATETIME" +%-M)
    local ALARM_SEC=$(date -u -d "$PARAM_DATETIME" +%-S)

    # local ALARM_HOUR_HEX=$(printf "0x%x\n" $ALARM_HOUR)
    # local ALARM_MIN_HEX=$(printf "0x%x\n" $ALARM_MIN)
    # local ALARM_SEC_HEX=$(printf "0x%x\n" $ALARM_SEC)

    local ALARM_HOUR_HEX=$(dec_to_bcd $ALARM_HOUR)
    local ALARM_MIN_HEX=$(dec_to_bcd $ALARM_MIN)
    local ALARM_SEC_HEX=$(dec_to_bcd $ALARM_SEC)

    # Disable RW protect
    i2cset -y $I2C_BUS $I2C_ADDR $REG_WRITE_PROTECT 0x29

    # Write value
    i2cset -y $I2C_BUS $I2C_ADDR $REG_ALARM_WEEKDAY $PARAM_WEEK_DAY
    i2cset -y $I2C_BUS $I2C_ADDR $REG_ALARM_HOUR $ALARM_HOUR_HEX
    i2cset -y $I2C_BUS $I2C_ADDR $REG_ALARM_MIN $ALARM_MIN_HEX
    i2cset -y $I2C_BUS $I2C_ADDR $REG_ALARM_SEC $ALARM_SEC_HEX

    # Enable RW protect
    i2cset -y $I2C_BUS $I2C_ADDR $REG_WRITE_PROTECT 0x00

    # echo "ok"
    sleep 0.2
    
    get_alarm_wakeup_time

    return 0
}

get_wakeup_on_power_restore() {
    read_register_bit_bool $REG_POWER $BIT_NUM_WAKEUP_ON_POWER_RESTORE
}

set_wakeup_on_power_restore() {
    local TARGET_BIT_VALUE="${1-}"

    if [[ $TARGET_BIT_VALUE != "0" && $TARGET_BIT_VALUE != "1" ]]; then
        echo "Error: parameter must be 0 or 1" >&2
        exit 1
    fi

    if ! write_register_bit $REG_POWER $BIT_NUM_WAKEUP_ON_POWER_RESTORE "$TARGET_BIT_VALUE"; then
        echo "Error: cannot set wakeup on power restore" >&2
        return 1
    fi

    echo "ok"

    return 0
}

get_charging_protection() {
    read_register_bit_bool $REG_CHARGING_PROTECTION $BIT_NUM_CHARGING_PROTECTION
}

set_charging_protection() {
    local TARGET_BIT_VALUE="${1-}"

    if [[ $TARGET_BIT_VALUE != "0" && $TARGET_BIT_VALUE != "1" ]]; then
        echo "Error: parameter must be 0 or 1" >&2
        exit 1
    fi

    if ! write_register_bit $REG_CHARGING_PROTECTION $BIT_NUM_CHARGING_PROTECTION "$TARGET_BIT_VALUE"; then
        echo "Error: cannot set charging protection" >&2
        return 1
    fi

    echo "ok"

    return 0
}

function_help() {
    cat << EOF
Usage: $0 [command] [arguments]

Commands:
    get_bat_level
    get_charging_status
    get_rtc_time
    get_temp
    get_alarm_wakeup_enabled
    get_alarm_wakeup_time
    get_alarm_wakeup_weekday
    get_wakeup_on_power_restore
    get_charging_protection
    set_rtc_time 2020-06-26T16:09:34+08:00
    set_alarm_wakeup_time 2020-06-26T16:09:34+08:00 127
    set_alarm_wakeup_enabled 0/1
    set_wakeup_on_power_restore 0/1
    set_charging_enabled 0/1
    set_charging_protection 0/1
    shutdown
    arm_powercut [delay_seconds]
    cancel_powercut
    get_powercut_byte
    get_power_flags
EOF
}

acquire_bus_lock

case "${1-}" in
    get_bat_level)
        get_bat_level
        ;;
    
    get_charging_status)
        get_charging_status
        ;;
    
    get_charging_enabled)
        get_charging_enabled
        ;;
    
    get_rtc_time)
        get_rtc_time
        ;;
    
    get_temp)
        get_temp
        ;;
        
    get_alarm_wakeup_enabled)
        get_alarm_wakeup_enabled
        ;;

    get_alarm_wakeup_time)
        get_alarm_wakeup_time
        ;;

    get_alarm_wakeup_weekday)
        echo "Not implemented"
        ;;

    get_wakeup_on_power_restore)
        get_wakeup_on_power_restore
        ;;

    set_rtc_time)
        shift
        set_rtc_time "$@"
        ;;

    set_alarm_wakeup_time)
        shift
        set_alarm_wakeup_time "$@"
        ;;

    set_alarm_wakeup_enabled)
        shift
        set_alarm_wakeup_enabled "$@"
        ;;

    set_wakeup_on_power_restore)
        shift
        set_wakeup_on_power_restore "$@"
        ;;

    set_charging_enabled)
        shift
        set_charging_enabled "$@"
        ;;

    get_charging_protection)
        get_charging_protection
        ;;

    set_charging_protection)
        shift
        set_charging_protection "$@"
        ;;

    shutdown)
        shift
        shutdown
        ;;

    arm_powercut)
        shift
        arm_powercut "$@"
        ;;

    cancel_powercut)
        cancel_powercut
        ;;

    get_powercut_byte)
        get_powercut_byte
        ;;

    get_power_flags)
        get_power_flags
        ;;

    "")
        echo "Error: no command specified"
        function_help
        exit 1
        ;;

    *)
        echo "Error: unknown command '$1'"
        function_help
        exit 1
        ;;

esac
