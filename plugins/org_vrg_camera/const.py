KEY_CAMERA = "camera"
KEY_VIDEO_SIZE = "video_size"
KEY_PHOTO_SIZE = "photo_size"

DEFAULT_VIDEO_SIZE = "1920x1080"

KEY_VIDEO_FPS = "video_fps"
KEY_VIDEO_BITRATE = "video_bitrate"
KEY_CAMERA_MODE_STR = "camera_mode_str"
KEY_VIDEO_WIDTH = "video_width"
KEY_VIDEO_HEIGHT = "video_height"

DEFAULT_VIDEO_FPS = 30
DEFAULT_VIDEO_BITRATE = 4000000
DEFAULT_CAMERA_MODE_STR = "1920:1080"
DEFAULT_VIDEO_WIDTH = 1920
DEFAULT_VIDEO_HEIGHT = 1080

KEY_HFLIP = "hflip"
KEY_VFLIP = "vflip"
KEY_SCREENSHOT = "screenshot"

DEFAULT_HFLIP = False
DEFAULT_VFLIP = False
DEFAULT_SCREENSHOT = True

# Maximum number of stored H.264 files (each with its companion MP4). Older files
# are pruned in _check_files_loop. JPEG, MP4 and favorites are not counted against
# this limit — they are expected to fit in the reserved disk space (see below).
KEY_MAX_H264_FILES = "max_h264_files"
DEFAULT_MAX_H264_FILES = 400

# Fraction of total disk space kept free as a reserve. When suggesting the maximum
# safe file limit, only (1 - reserve) of the disk is considered usable by H.264 files.
DISK_RESERVE_FRACTION = 0.2

# H.264 segment duration (seconds). Used to estimate the size of a single recording
# file from the current bitrate when no recordings exist yet (see start_video.sh).
H264_SEGMENT_SECONDS = 120

KEY_STREAM_CAMERA_MODE_STR = "stream_camera_mode_str"
KEY_STREAM_VIDEO_WIDTH = "stream_video_width"
KEY_STREAM_VIDEO_HEIGHT = "stream_video_height"

DEFAULT_STREAM_CAMERA_MODE_STR = "1280:720"
DEFAULT_STREAM_VIDEO_WIDTH = 1280
DEFAULT_STREAM_VIDEO_HEIGHT = 720

# Thermal throttle thresholds (Celsius)
TEMP_VIDEO_STOP = 65
TEMP_VIDEO_RESUME = 60
TEMP_DOWNSCALE_ON = 60
TEMP_DOWNSCALE_OFF = 57

THROTTLE_VIDEO_FPS = 15  # max fps when thermal throttle is active
