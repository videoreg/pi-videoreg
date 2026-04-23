#!/usr/bin/bash
#
# Takes a single JPEG photo using rpicam-jpeg at 2560x1440.
#
# Options:
#   --screenshot <file>        Output file path (default: <timestamp>.jpg)
#   --hdr <on|off>             HDR mode (default: off)
#   --night <0|1>              Night mode: long shutter (2s), low framerate, gain=1
#   --post-process-file <file> rpicam post-processing JSON config
#   --hflip                    Horizontal flip
#   --vflip                    Vertical flip

DATE=$(date +"%Y-%m-%d_%H-%M-%S")
SCREENSHOT_FILE="${DATE}.jpg"
HDR="off"
NIGHT=""

FRAMERATE_ARG=""
EXPOSURE_ARG=""
SHUTTER_ARG=""
GAIN_ARG=""
EV_ARG=""
TIMEOUT_ARG="--timeout 3s"
POST_PROCESS_FILE_ARG=""
HFLIP_ARG=""
VFLIP_ARG=""

function parse_and_validate_arguments() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
    --screenshot)
      SCREENSHOT_FILE="$2"
      shift 2
      ;;
    --hdr)
      HDR="$2"
      shift 2
      ;;
    --night)
      NIGHT="$2"
      shift 2
      ;;
    --post-process-file)
      if [[ ! -f "$2" ]]; then
        echo "Error: Post-process file '$2' does not exist."
        exit 1
      fi
      POST_PROCESS_FILE_ARG="--post-process-file $2"
      shift 2
      ;;
    --hflip)
      HFLIP_ARG="--hflip"
      shift
      ;;
    --vflip)
      VFLIP_ARG="--vflip"
      shift
      ;;
    *)
      echo "Error: Unknown option $1."
      exit 1
      ;;
    esac
  done

  # If --night is 1, add gain parameter
  if [[ "$NIGHT" == "1" ]]; then
    FRAMERATE_ARG="--framerate 0.1"
    EXPOSURE_ARG="--exposure long"
    SHUTTER_ARG="--shutter 2000000"
    GAIN_ARG="--gain 1" # was 10 before shutter 2s
    TIMEOUT_ARG="--immediate"
  fi
}

parse_and_validate_arguments "$@"

# --gain 10 \
# --denoise cdn_hq \
# --timeout 3s \
# --metering average \
# --shutter 4000000 \

rpicam-jpeg \
  -v 0 \
  --nopreview \
  --width 2560 \
  --height 1440 \
  --hdr $HDR \
  --autofocus-mode manual \
  --lens-position 0.0 \
  $FRAMERATE_ARG \
  $EXPOSURE_ARG \
  $SHUTTER_ARG \
  $GAIN_ARG \
  $EV_ARG \
  $TIMEOUT_ARG \
  $POST_PROCESS_FILE_ARG \
  $HFLIP_ARG \
  $VFLIP_ARG \
  --output $SCREENSHOT_FILE

echo "Photo taken to ${SCREENSHOT_FILE}"
