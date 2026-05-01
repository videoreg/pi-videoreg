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
# Usage: pisugar.sh <command> [arguments]
# Run without arguments or with an unknown command to see available commands.

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
BIT_NUM_CHARGING_ENABLED=6
BIT_NUM_CHARGIN_STATUS=7

REG_SHUTDOWN_DELAY=0x09

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

shutdown() {
    # In theory, PiSugar is powered off by /lib/systemd/system-shutdown/shutdown-pisugar.sh,
    # which runs early after `shutdown now`. In practice it does not always fire,
    # so we set a longer delay here as a fallback.

    local DELAY_SECONDS=20

    # Disable Write Protection (Write 0x29 to 0x0b)
    i2cset -y $I2C_BUS $I2C_ADDR $REG_WRITE_PROTECT 0x29

    # Set the desired delay time (Write DELAY_SECONDS to 0x09)
    local DELAY_HEX=$(printf "0x%x" $DELAY_SECONDS)
    i2cset -y $I2C_BUS $I2C_ADDR $REG_SHUTDOWN_DELAY $DELAY_HEX

    # Read original value of 0x02 register
    local ORIGINAL_VAL_HEX=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_POWER)
    # Clear Bit 5 of 0x02 to enable delayed shutdown
    local NEW_VAL_DEC=$(( ORIGINAL_VAL_HEX & 0xDF ))
    local NEW_VAL_HEX=$(printf "0x%x" $NEW_VAL_DEC)

    i2cset -y $I2C_BUS $I2C_ADDR $REG_POWER $NEW_VAL_HEX

    # Enable Write Protection (Write 0x00 to 0x0b)
    i2cset -y $I2C_BUS $I2C_ADDR $REG_WRITE_PROTECT 0x00

    sudo systemd-run --on-active=1s --timer-property=AccuracySec=1s shutdown now
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
    # local REG_RTC_VALUE_YEAR=$(printf "%d" $(i2cget -y $I2C_BUS $I2C_ADDR $REG_RTC_YEAR)) # all registers except year in BCD format
    local REG_RTC_VALUE_YEAR=$(bcd_to_dec $(i2cget -y $I2C_BUS $I2C_ADDR $REG_RTC_YEAR)) # hwclock writes BCD to year also
    local REG_RTC_VALUE_MONTH=$(bcd_to_dec $(i2cget -y $I2C_BUS $I2C_ADDR $REG_RTC_MONTH))
    local REG_RTC_VALUE_DAY=$(bcd_to_dec $(i2cget -y $I2C_BUS $I2C_ADDR $REG_RTC_DAY))

    local REG_RTC_VALUE_HOUR=$(bcd_to_dec $(i2cget -y $I2C_BUS $I2C_ADDR $REG_RTC_HOUR))
    local REG_RTC_VALUE_MIN=$(bcd_to_dec $(i2cget -y $I2C_BUS $I2C_ADDR $REG_RTC_MIN))
    local REG_RTC_VALUE_SEC=$(bcd_to_dec $(i2cget -y $I2C_BUS $I2C_ADDR $REG_RTC_SEC))

    local RTC_RAW_DATETIME="20${REG_RTC_VALUE_YEAR}-${REG_RTC_VALUE_MONTH}-${REG_RTC_VALUE_DAY} ${REG_RTC_VALUE_HOUR}:${REG_RTC_VALUE_MIN}:${REG_RTC_VALUE_SEC}"

    echo $(date -d "${RTC_RAW_DATETIME} UTC" +"%Y-%m-%dT%H:%M:%S%:z")

    return 0
}

set_rtc_time() {
    local PARAM_DATETIME=$1

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
    printf "%d\n" $(i2cget -y $I2C_BUS $I2C_ADDR $REG_BAT_LEVEL)
    return 0
}

get_charging_status() {
    local REG_VALUE=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_POWER)
    local BIT4_VALUE=$((($REG_VALUE >> $BIT_NUM_CHARGIN_STATUS) & 1))

    if [ $BIT4_VALUE -eq 1 ]; then
        echo "true"
    else
        echo "false"
    fi

    return 0
}

get_charging_enabled() {
    local REG_VALUE=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_POWER)
    local BIT4_VALUE=$((($REG_VALUE >> $BIT_NUM_CHARGING_ENABLED) & 1))

    if [ $BIT4_VALUE -eq 1 ]; then
        echo "true"
    else
        echo "false"
    fi

    return 0
}

get_temp() {
    local REG_VALUE=$(printf "%d" $(i2cget -y $I2C_BUS $I2C_ADDR $REG_TEMP))
    echo $(( $REG_VALUE - 40 ))
    return 0
}

get_alarm_wakeup_enabled() {
    local REG_VALUE=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_ALARM)
    local BIT7_VALUE=$((($REG_VALUE >> $BIT_NUM_ALARM_ENABLED) & 1))

    if [ $BIT7_VALUE -eq 1 ]; then
        echo "true"
    else
        echo "false"
    fi

    return 0
}

set_alarm_wakeup_enabled() {
    local TARGET_BIT_VALUE="$1"

    if [[ $TARGET_BIT_VALUE != "0" && $TARGET_BIT_VALUE != "1" ]]; then
        echo "Error: parameter must be 0 or 1" >&2
        exit 1
    fi

    # Disable RW protect
    i2cset -y $I2C_BUS $I2C_ADDR $REG_WRITE_PROTECT 0x29

    local REG_VALUE=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_ALARM)

    if [ $TARGET_BIT_VALUE -eq "1" ]; then
        local NEW_VALUE=$(($REG_VALUE | 0x80))
    else
        local NEW_VALUE=$(($REG_VALUE & 0x7F))
    fi

    local NEW_VAL_HEX=$(printf "0x%x" $NEW_VALUE)

    echo "NEW_VALUE=${NEW_VALUE} NEW_VAL_HEX=${NEW_VAL_HEX}"

    # Write value
    i2cset -y $I2C_BUS $I2C_ADDR $REG_ALARM $NEW_VAL_HEX

    # Enable RW protect
    i2cset -y $I2C_BUS $I2C_ADDR $REG_WRITE_PROTECT 0x00

    echo "ok"

    return 0
}

get_nearest_weekday_bitmask() {
    local bitmask="$1"  # 0-127 (binary: 0000000-1111111)
    local time="$2"     # HH:MM:SS (in UTC)

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
    local REG_VALUE_WEEKDAY=$(printf "%d" $(i2cget -y $I2C_BUS $I2C_ADDR $REG_ALARM_WEEKDAY))
    # local REG_VALUE_HOUR=$(printf "%d" $(i2cget -y $I2C_BUS $I2C_ADDR $REG_ALARM_HOUR))
    # local REG_VALUE_MIN=$(printf "%d" $(i2cget -y $I2C_BUS $I2C_ADDR $REG_ALARM_MIN))
    # local REG_VALUE_SEC=$(printf "%d" $(i2cget -y $I2C_BUS $I2C_ADDR $REG_ALARM_SEC))

    local REG_VALUE_HOUR=$(bcd_to_dec $(i2cget -y $I2C_BUS $I2C_ADDR $REG_ALARM_HOUR))
    local REG_VALUE_MIN=$(bcd_to_dec $(i2cget -y $I2C_BUS $I2C_ADDR $REG_ALARM_MIN))
    local REG_VALUE_SEC=$(bcd_to_dec $(i2cget -y $I2C_BUS $I2C_ADDR $REG_ALARM_SEC))

    get_nearest_weekday_bitmask $REG_VALUE_WEEKDAY "${REG_VALUE_HOUR}:${REG_VALUE_MIN}:${REG_VALUE_SEC}"

    return 0
}

set_alarm_wakeup_time() {
    local PARAM_DATETIME=$1
    local PARAM_WEEK_DAY=$2

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
    local REG_VALUE=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_POWER)
    local BIT_VALUE=$((($REG_VALUE >> $BIT_NUM_WAKEUP_ON_POWER_RESTORE) & 1))

    if [ $BIT_VALUE -eq 1 ]; then
        echo "true"
    else
        echo "false"
    fi

    return 0
}

set_wakeup_on_power_restore() {
    local TARGET_BIT_VALUE="$1"

    if [[ $TARGET_BIT_VALUE != "0" && $TARGET_BIT_VALUE != "1" ]]; then
        echo "Error: parameter must be 0 or 1" >&2
        exit 1
    fi

    # Disable RW protect
    i2cset -y $I2C_BUS $I2C_ADDR $REG_WRITE_PROTECT 0x29

    local REG_VALUE=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_POWER)

    if [ $TARGET_BIT_VALUE -eq "1" ]; then
        NEW_VALUE=$(($REG_VALUE | 0x10))
    else
        NEW_VALUE=$(($REG_VALUE & 0xEF))
    fi

    local NEW_VAL_HEX=$(printf "0x%x" $NEW_VALUE)

    # Write value
    i2cset -y $I2C_BUS $I2C_ADDR $REG_POWER $NEW_VAL_HEX

    # Enable RW protect
    i2cset -y $I2C_BUS $I2C_ADDR $REG_WRITE_PROTECT 0x00

    echo "ok"

    return 0
}

get_charging_protection() {
    local REG_VALUE=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_CHARGING_PROTECTION)
    local BIT_VALUE=$((($REG_VALUE >> $BIT_NUM_CHARGING_PROTECTION) & 1))

    if [ $BIT_VALUE -eq 1 ]; then
        echo "true"
    else
        echo "false"
    fi

    return 0
}

set_charging_protection() {
    local TARGET_BIT_VALUE="$1"

    if [[ $TARGET_BIT_VALUE != "0" && $TARGET_BIT_VALUE != "1" ]]; then
        echo "Error: parameter must be 0 or 1" >&2
        exit 1
    fi

    # Disable RW protect
    i2cset -y $I2C_BUS $I2C_ADDR $REG_WRITE_PROTECT 0x29

    local REG_VALUE=$(i2cget -y $I2C_BUS $I2C_ADDR $REG_CHARGING_PROTECTION)

    if [ $TARGET_BIT_VALUE -eq "1" ]; then
        NEW_VALUE=$(($REG_VALUE | 0x80))
    else
        NEW_VALUE=$(($REG_VALUE & 0x7F))
    fi

    local NEW_VAL_HEX=$(printf "0x%x" $NEW_VALUE)

    # Write value
    i2cset -y $I2C_BUS $I2C_ADDR $REG_CHARGING_PROTECTION $NEW_VAL_HEX

    # Enable RW protect
    i2cset -y $I2C_BUS $I2C_ADDR $REG_WRITE_PROTECT 0x00

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
    set_charging_protection 0/1
    shutdown [0-255]
EOF
}

case "$1" in
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
