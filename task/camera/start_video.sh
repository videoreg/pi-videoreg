#!/usr/bin/bash
#
# Starts video recording from the camera using rpicam-vid.
#
# Supports three output modes (--mode):
#   file   — segments H.264 stream into 120-second files saved to --h264-dir
#   stream — re-streams video via RTSP at rtsp://0.0.0.0:8554/videoreg
#   both   — file + stream simultaneously (default)
#
# Optional --screenshot triggers periodic JPEG snapshot output to --screenshots-dir.
# Optional --duration N limits recording to N seconds; without it recording runs until
# the process receives SIGTERM/SIGINT, which triggers a clean shutdown forwarded to all
# child processes.
#
# Usage:
#   start_video.sh --h264-dir DIR --screenshots-dir DIR [OPTIONS]
#
# Required:
#   --h264-dir DIR          Directory for H.264 segment files
#   --screenshots-dir DIR   Directory for JPEG screenshots
#
# Optional:
#   --fps N                 Frame rate (default: 30)
#   --mode MODE             Output mode: file | stream | both (default: both)
#   --camera-mode WxH       Sensor mode (default: 1296:972)
#   --width N               Output width in pixels (default: 1296)
#   --height N              Output height in pixels (default: 729)
#   --bitrate N             H.264 bitrate in bits/s (default: 2000000)
#   --post-process-file F   rpicam post-processing JSON config file
#   --hflip                 Flip image horizontally
#   --vflip                 Flip image vertically
#   --screenshot INTERVAL   Save a JPEG every INTERVAL milliseconds
#   --duration N            Stop after N seconds (default: run indefinitely)
#   --path PATH             Override the default output file path template

H264_DIR=""
SCREENSHOTS_DIR=""
FPS=30
MODE="both"
CAMERA_MODE="1296:972"
WIDTH=1296
HEIGHT=729
BITRATE=2000000
POST_PROCESS_FILE_ARG=""
HFLIP_ARG=""
VFLIP_ARG=""
SCREENSHOT_ARG=""
DURATION=""
PATH_OVERRIDE=""
# Array to store child process PIDs
declare -a CHILDREN=()

function parse_and_validate_arguments() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
    --h264-dir)
      H264_DIR="$2"
      shift 2
      ;;
    --screenshots-dir)
      SCREENSHOTS_DIR="$2"
      shift 2
      ;;
    --fps)
      FPS="$2"
      shift 2
      ;;
    --mode)
      MODE="$2"
      shift 2
      ;;
    --camera-mode)
      CAMERA_MODE="$2"
      shift 2
      ;;
    --width)
      WIDTH="$2"
      shift 2
      ;;
    --height)
      HEIGHT="$2"
      shift 2
      ;;
    --bitrate)
      BITRATE="$2"
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
    --screenshot)
      SCREENSHOT_ARG="--screenshot $2"
      shift 2
      ;;
    --duration)
      DURATION="$2"
      shift 2
      ;;
    --path)
      PATH_OVERRIDE="$2"
      shift 2
      ;;
    *)
      echo "Error: Unknown option $1."
      exit 1
      ;;
    esac
  done

  if [ -z "${H264_DIR}" ]; then
    echo "Error: --h264-dir is required."
    exit 1
  fi
  if [ -z "${SCREENSHOTS_DIR}" ]; then
    echo "Error: --screenshots-dir is required."
    exit 1
  fi
  if [ ! -d "${H264_DIR}" ]; then
    echo "Error: h264 directory does not exist."
    exit 1
  fi
  if [ ! -d "${SCREENSHOTS_DIR}" ]; then
    echo "Error: screenshots directory does not exist."
    exit 1
  fi
  if ! [[ "${FPS}" =~ ^[0-9]+$ ]]; then
    echo "Error: fps should be a number."
    exit 1
  fi
  if [[ "${MODE}" != "file" && "${MODE}" != "stream" && "${MODE}" != "both" ]]; then
    echo "Error: --mode should be 'file', 'stream' or 'both'."
    exit 1
  fi
  if ! [[ "${WIDTH}" =~ ^[0-9]+$ ]]; then
    echo "Error: width should be a number."
    exit 1
  fi
  if ! [[ "${HEIGHT}" =~ ^[0-9]+$ ]]; then
    echo "Error: height should be a number."
    exit 1
  fi
  if ! [[ "${BITRATE}" =~ ^[0-9]+$ ]]; then
    echo "Error: bitrate should be a number."
    exit 1
  fi
  if [[ -n "${DURATION}" ]] && ! [[ "${DURATION}" =~ ^[0-9]+$ ]]; then
    echo "Error: duration should be a number."
    exit 1
  fi
}

# Signal handler
forward_signal() {
    local signal=$1
    echo "Received $signal, forwarding to child processes..."
    for pid in "${CHILDREN[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill -"$signal" "$pid" 2>/dev/null || true
        fi
    done
}

cleanup() {
    forward_signal TERM
    
    for pid in "${CHILDREN[@]}"; do
        wait "$pid" 2>/dev/null || true
    done
    
    exit 0
}

# Set up signal handlers
trap 'cleanup' TERM INT QUIT HUP
trap 'forward_signal USR1' USR1
trap 'forward_signal USR2' USR2

parse_and_validate_arguments "$@"

# Build ffmpeg command based on mode
FFMPEG_OUTPUTS=""

if [[ "${MODE}" == "file" || "${MODE}" == "both" ]]; then
  FFMPEG_OUTPUTS="${FFMPEG_OUTPUTS} -map 0:v -c:v copy -f segment -segment_time 120 -reset_timestamps 1 -strftime 1 ${H264_DIR}/%Y-%m-%d_%H-%M-%S.h264"
fi

if [[ "${MODE}" == "stream" || "${MODE}" == "both" ]]; then
  # FFMPEG_OUTPUTS="${FFMPEG_OUTPUTS} -map 0:v -c:v copy -f mpegts udp://0.0.0.0:8002/videoreg?pkt_size=1316"
  FFMPEG_OUTPUTS="${FFMPEG_OUTPUTS} -map 0:v -c:v copy -f rtsp -rtsp_transport tcp rtsp://0.0.0.0:8554/videoreg"
fi

if [[ -n "${DURATION}" ]]; then
  TIMEOUT_ARG="--timeout $((DURATION * 1000))"
  SEGMENT_ARG=""
else
  TIMEOUT_ARG="--timeout 0"
  SEGMENT_ARG="--segment 120000"
fi

rpicam-vid \
  -v 0 \
  --nopreview \
  --framerate $FPS \
  --mode $CAMERA_MODE \
  --width $WIDTH \
  --height $HEIGHT \
  --bitrate $BITRATE \
  $TIMEOUT_ARG \
  --denoise cdn_off \
  --autofocus-mode manual \
  --lens-position 0.0 \
  --codec h264 \
  --profile main \
  --level 4.2 \
  --flush \
  --inline \
  $POST_PROCESS_FILE_ARG \
  $HFLIP_ARG \
  $VFLIP_ARG \
  $SEGMENT_ARG \
  $SCREENSHOT_ARG \
  --output "${PATH_OVERRIDE:-${H264_DIR}/%F_%H-%M-%S.h264}" \
  &

# -o - | \
#   ffmpeg -loglevel error \
#     -fflags +genpts+nobuffer \
#     -flags low_delay \
#     -probesize 32 \
#     -analyzeduration 0 \
#     -f h264 \
#     -y \
#     -i - \
#     ${FFMPEG_OUTPUTS} \

CHILDREN+=($!)

# Wait for all children
for pid in "${CHILDREN[@]}"; do
  wait "$pid"
done
