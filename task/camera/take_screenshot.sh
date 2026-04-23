#!/usr/bin/bash
# Captures a single JPEG frame from the RTSP stream via ffmpeg.
# Usage: take_screenshot.sh [-s <output_file>]
#   -s  output filename (default: YYYY-MM-DD_HH-MM-SS.jpg)

DATE=$(date +"%Y-%m-%d_%H-%M-%S")
SCREENSHOT_FILE="${DATE}.jpg"

function parse_and_validate_arguments() {
  while getopts "s:h:" opt; do
    case "${opt}" in
    s)
      SCREENSHOT_FILE="${OPTARG}"
      ;;
    ?)
      echo "Error: Unknown option -${OPTARG}."
      exit 1
      ;;
    *)
      echo "Error: Unknown error while processing options."
      exit 1
      ;;
    esac
  done
}

parse_and_validate_arguments "$@"

ffmpeg -hide_banner \
  -loglevel error \
  -i rtsp://0.0.0.0:8554/videoreg \
  -vframes 1 \
  -q:v 2 \
  -f image2 $SCREENSHOT_FILE

echo "Screenshot taken to ${SCREENSHOT_FILE}"