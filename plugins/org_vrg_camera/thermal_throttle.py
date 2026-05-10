from enum import Enum

import plugins.org_vrg_camera.const as const


class ThermalAction(Enum):
    NONE = "none"
    DOWNSCALE = "downscale"              # throttle entered while recording — restart at 720p
    RESTORE = "restore"                  # throttle exited while recording — restart at full res
    STOP = "stop"                        # hard thermal stop
    START = "start"                      # temperature recovered — start recording
    TAKE_PHOTO_AND_WAIT = "take_photo"   # too hot to start — take photo and wait


class ThermalThrottle:
    # Three-stage hysteresis (only active when user resolution > 720p):
    #
    #   < 57°C  │  throttled → full res  (TEMP_DOWNSCALE_OFF)
    #   57–60°C │  stay in current state
    #   60–65°C │  full res → 720p       (TEMP_DOWNSCALE_ON / TEMP_VIDEO_STOP)
    #   > 65°C  │  720p → recording stop  (TEMP_VIDEO_STOP)
    #
    # At > 65°C the throttle flag is set silently (no restart) because STOP follows
    # immediately. This ensures the recording resumes at 720p after a hard stop,
    # not at full res, and stays there until the CPU fully cools below TEMP_DOWNSCALE_OFF.

    def __init__(self) -> None:
        self._throttled = False

    @property
    def throttled(self) -> bool:
        return self._throttled

    def update(
        self,
        cpu_temp: float,
        user_width: int,
        is_recording: bool,   # VideoState.START
        is_active: bool,      # VideoState.START or STREAM
        is_stopped: bool,     # VideoState.STOP
    ) -> ThermalAction:
        capable = user_width > const.DEFAULT_STREAM_VIDEO_WIDTH

        if capable:
            if not self._throttled:
                if const.TEMP_DOWNSCALE_ON < cpu_temp <= const.TEMP_VIDEO_STOP:
                    self._throttled = True
                    if is_recording:
                        return ThermalAction.DOWNSCALE
                elif cpu_temp > const.TEMP_VIDEO_STOP:
                    # Set flag silently — STOP returned below; resume will use 720p
                    self._throttled = True
            elif cpu_temp < const.TEMP_DOWNSCALE_OFF:
                self._throttled = False
                if is_recording:
                    return ThermalAction.RESTORE

        if is_active and cpu_temp > const.TEMP_VIDEO_STOP:
            return ThermalAction.STOP
        if is_stopped:
            if cpu_temp < const.TEMP_VIDEO_RESUME:
                return ThermalAction.START
            return ThermalAction.TAKE_PHOTO_AND_WAIT

        return ThermalAction.NONE
