#!/bin/sh

# Skips the RTC->system copy if NTP has already synchronized the clock:
# in that case the system time is authoritative and must not be overwritten
# by the (less accurate) hardware RTC. Saving time back TO the RTC after NTP
# is the job of hwclock-save.service, not this script.

ntp_synced() {
    [ "$(timedatectl show -p NTPSynchronized --value 2>/dev/null)" = "yes" ]
}

i=1
while [ "$i" -le 12 ]; do
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

logger "RTC sync gave up after 12 attempts (rtc0 missing or unreadable)"
exit 1