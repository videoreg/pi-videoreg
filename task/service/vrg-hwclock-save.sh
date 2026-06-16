#!/bin/sh

ntp_synced() {
    [ "$(timedatectl show -p NTPSynchronized --value 2>/dev/null)" = "yes" ]
}

i=1
while [ "$i" -le 8 ]; do
    if ntp_synced; then
        /usr/sbin/hwclock --systohc --rtc=/dev/rtc0 --utc
        logger "RTC synced from system time (attempt $i)"
        exit 0
    fi

    logger "NTP not synced (attempt $i), retrying"
    sleep 2
    i=$((i + 1))
done

logger "RTC from system time sync gave up after 8 attempts"
exit 1