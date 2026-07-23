#!/bin/sh

# Skips the RTC->system copy if NTP has already synchronized the clock:
# in that case the system time is authoritative and must not be overwritten
# by the (less accurate) hardware RTC. Saving time back TO the RTC after NTP
# is the job of hwclock-save.service, not this script.

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PISUGAR_SH="$SCRIPT_DIR/../pisugar.sh"

ntp_synced() {
    [ "$(timedatectl show -p NTPSynchronized --value 2>/dev/null)" = "yes" ]
}

# Fallback: PiSugar sometimes fails to expose its RTC as /dev/rtc0, but the
# clock is still readable over I2C. Ask pisugar.sh for the time and push it
# into the system clock with `date`.
load_from_pisugar() {
    # pisugar.sh is not marked executable and relies on bash-only syntax,
    # so run it through bash explicitly (same as sdk/power/pisugar.py does).
    if [ ! -r "$PISUGAR_SH" ]; then
        logger "PiSugar RTC fallback unavailable: $PISUGAR_SH not found or not readable"
        return 1
    fi

    local rtc_time epoch
    rtc_time=$(bash "$PISUGAR_SH" get_rtc_time 2>/dev/null)

    # Convert to epoch seconds and feed `date -s @<epoch>`. The "@seconds" form
    # is unambiguous (always UTC) and avoids any ISO-8601 / timezone-offset
    # parsing quirks in the `date -s` path.
    epoch=$(date -d "$rtc_time" +%s 2>/dev/null)
    if [ -z "$epoch" ]; then
        logger "PiSugar RTC fallback failed: could not parse time read over I2C ('$rtc_time')"
        return 1
    fi

    local err
    if err=$(date -s "@$epoch" 2>&1 >/dev/null); then
        logger "System clock set from PiSugar over I2C: $rtc_time (epoch $epoch)"
        return 0
    fi

    logger "PiSugar RTC fallback failed: could not set system clock from '$rtc_time' (epoch $epoch): ${err:-unknown error}"
    return 1
}

i=1
while [ "$i" -le 4 ]; do
    if ntp_synced; then
        logger "RTC load skipped: NTP already synchronized (attempt $i)"
        exit 0
    fi

    if [ -e /dev/rtc0 ]; then
        if /sbin/hwclock --hctosys --utc; then
            logger "RTC synced to system on attempt $i"
            exit 0
        fi
        logger "RTC read failed (attempt $i), retrying"
    else
        logger "/dev/rtc0 not present yet (attempt $i), waiting"
    fi

    sleep 2
    i=$((i + 1))
done

logger "/dev/rtc0 not available after 12 attempts, trying PiSugar I2C fallback"
if load_from_pisugar; then
    exit 0
fi

logger "RTC sync gave up after 12 attempts (rtc0 missing/unreadable, PiSugar fallback failed)"
exit 1