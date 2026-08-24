"""
Coordinate conversion utilities for percentage-based screen coordinates.

Percentages are relative to the LIVE device resolution (auto-detected via
`adb shell wm size`, see cmd_program.screen_action.get_screen_size). When no
device is attached the 1080x2460 fallback is used so imports/tests work.
"""
from cmd_program.screen_action import get_screen_size
from core import config

BASE_WIDTH = config.FALLBACK_WIDTH
BASE_HEIGHT = config.FALLBACK_HEIGHT


def _live_size(screen_width=None, screen_height=None):
    if screen_width and screen_height:
        return screen_width, screen_height
    try:
        return get_screen_size()
    except Exception:
        return BASE_WIDTH, BASE_HEIGHT


def pixel_to_percent(x: float, y: float) -> tuple[float, float]:
    """Convert pixel coordinates (live resolution) to percentage coordinates."""
    w, h = _live_size()
    return (x / w) * 100, (y / h) * 100


def percent_to_pixel(x_percent: float, y_percent: float,
                     screen_width: int = None,
                     screen_height: int = None) -> tuple[int, int]:
    """Convert percentage coordinates to pixels using the live resolution."""
    w, h = _live_size(screen_width, screen_height)
    return int((x_percent / 100) * w), int((y_percent / 100) * h)


def box_pixel_to_percent(box: list[int]) -> list[float]:
    """Convert box [x1, y1, x2, y2] from pixels (live resolution) to percentages."""
    x1, y1, x2, y2 = box
    x1_p, y1_p = pixel_to_percent(x1, y1)
    x2_p, y2_p = pixel_to_percent(x2, y2)
    return [x1_p, y1_p, x2_p, y2_p]


def box_percent_to_pixel(box: list[float],
                         screen_width: int = None,
                         screen_height: int = None) -> list[int]:
    """Convert box [x1%, y1%, x2%, y2%] from percentages to pixels (live resolution)."""
    x1_p, y1_p, x2_p, y2_p = box
    w, h = _live_size(screen_width, screen_height)
    x1, y1 = percent_to_pixel(x1_p, y1_p, w, h)
    x2, y2 = percent_to_pixel(x2_p, y2_p, w, h)
    return [x1, y1, x2, y2]


def round_percentages(box: list[float], decimals: int = 2) -> list[float]:
    """Round percentage values to specified decimal places."""
    return [round(v, decimals) for v in box]
