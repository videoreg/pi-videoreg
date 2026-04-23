#!/bin/bash

# Runs once on first boot to expand the /dev/mmcblk0p3 partition
# to 100% of the SD card and recreate the FAT32 filesystem.
#
# Completion marker: /var/lib/vrg-resize3fs-once.done
# Once this file exists the service no longer starts (ConditionPathExists).

set -e

DEVICE="/dev/mmcblk0p3"
DISK="/dev/mmcblk0"
MOUNT_POINT="/mnt/data"
DONE_MARKER="/var/lib/vrg-resize3fs-once.done"

log() {
    echo "[vrg-resize3fs-once] $*"
}

# Check that the partition exists
if ! lsblk "$DEVICE" &>/dev/null; then
    log "ERROR: partition $DEVICE not found, skipping"
    exit 1
fi

# Check that the partition is FAT32
FSTYPE=$(lsblk -no FSTYPE "$DEVICE" 2>/dev/null || true)
if [[ "$FSTYPE" != "vfat" ]]; then
    log "ERROR: $DEVICE is not FAT32 (detected: '$FSTYPE'), skipping"
    exit 1
fi

# Unmount if mounted
if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
    log "Unmounting $MOUNT_POINT..."
    umount "$MOUNT_POINT"
fi

# Expand partition to 100% of disk
log "Expanding partition $DEVICE to 100% of disk..."
parted -s "$DISK" resizepart 3 100%

# Format as FAT32
log "Formatting $DEVICE as FAT32..."
mkfs.vfat "$DEVICE"

# Mount to create directories (from fstab, without specifying device)
log "Mounting $MOUNT_POINT..."
mount "$MOUNT_POINT"

# Create directories
log "Creating directories..."
mkdir -p "$MOUNT_POINT/videoreg/h264"
mkdir -p "$MOUNT_POINT/videoreg/jpeg"
mkdir -p "$MOUNT_POINT/videoreg/gps"

# Mark successful completion
touch "$DONE_MARKER"
log "Partition successfully expanded and formatted"
