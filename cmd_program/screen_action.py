import os
import cv2
import time
import subprocess
import numpy as np

from core import config

# Lazily detected device serial and screen size (do NOT touch adb at import).
_device_id = None
_screen_size = None


def get_adb_devices():
    result = subprocess.run(
        ["adb", "devices"],
        capture_output=True,
        text=True
    )
    lines = result.stdout.strip().split("\n")[1:]
    devices = []
    for line in lines:
        if line.strip():
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
    return devices


def get_device_id():
    """Return the adb serial to use, detecting it on first call.

    Priority: WOS_ADB_SERIAL env -> first connected device.
    Raises RuntimeError if no device is attached.
    """
    global _device_id
    if _device_id:
        return _device_id

    if config.ADB_SERIAL:
        _device_id = config.ADB_SERIAL
        return _device_id

    devices = get_adb_devices()
    if not devices:
        raise RuntimeError(
            "No ADB devices found. Connect a device (or set WOS_ADB_SERIAL) "
            "before running the bot."
        )
    _device_id = devices[0]
    return _device_id


def get_screen_size():
    """Detect the real device resolution via `wm size` (cached).

    Override size wins over physical size. WOS_RESOLUTION env wins over
    everything. Falls back to 1080x2460 when no device is attached.
    """
    global _screen_size
    if _screen_size:
        return _screen_size

    if config.RESOLUTION:
        try:
            w, h = config.RESOLUTION.lower().split("x")
            _screen_size = (int(w), int(h))
            return _screen_size
        except ValueError:
            print(f"Ignoring invalid WOS_RESOLUTION={config.RESOLUTION!r}")

    try:
        device = get_device_id()
        result = subprocess.run(
            ["adb", "-s", device, "shell", "wm", "size"],
            capture_output=True, text=True, timeout=10,
        )
        override = physical = None
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("Override size:"):
                override = line.split(":", 1)[1].strip()
            elif line.startswith("Physical size:"):
                physical = line.split(":", 1)[1].strip()
        size = override or physical
        if size:
            w, h = size.split("x")
            _screen_size = (int(w), int(h))
            return _screen_size
    except Exception as e:
        print(f"Screen size detection failed ({e}), using fallback")

    _screen_size = (config.FALLBACK_WIDTH, config.FALLBACK_HEIGHT)
    return _screen_size


def _convert_if_percentage(value, max_value):
    """Convert a coordinate to pixels.

    Any number (int or float) within 0..100 is treated as a percentage of
    the live screen size; anything else is an absolute pixel value. Pixel
    coordinates are clamped to the screen bounds.
    """
    if 0 <= value <= 100:
        return int(round((value / 100) * max_value))
    px = int(value)
    return max(0, min(px, max_value))


def _screen_width():
    return get_screen_size()[0]


def _screen_height():
    return get_screen_size()[1]


def run_adb_command(cmd, device_id=None, retries=1):
    device_id = device_id or get_device_id()
    last_err = None
    for attempt in range(retries + 1):
        try:
            subprocess.run(["adb", "-s", str(device_id)] + cmd, check=True)
            return
        except Exception as e:
            last_err = e
            # transient adb hiccups (device reconnecting) — brief backoff
            if attempt < retries:
                time.sleep(1.5)
    raise RuntimeError(f"adb command failed - {last_err}")


def _resolve_coord(*args):
    if len(args) == 1:
        if args[0] is None:
            raise RuntimeError("Coordination not found")
        x, y = args[0]
    elif len(args) == 2:
        x, y = args
    else:
        raise ValueError("Expected (x, y) or x, y")
    return _convert_if_percentage(x, _screen_width()), _convert_if_percentage(y, _screen_height())


def tap_screen(*args):
    x, y = _resolve_coord(*args)
    run_adb_command(["shell", "input", "tap", str(x), str(y)])


def swipe_screen(*args, duration=300):
    if len(args) == 2:
        (x1, y1), (x2, y2) = args
    elif len(args) == 4:
        x1, y1, x2, y2 = args
    else:
        raise ValueError("Expected ((x1,y1),(x2,y2)) or x1, y1, x2, y2")

    w, h = get_screen_size()
    x1 = _convert_if_percentage(x1, w)
    y1 = _convert_if_percentage(y1, h)
    x2 = _convert_if_percentage(x2, w)
    y2 = _convert_if_percentage(y2, h)

    run_adb_command(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)])


def long_press(*args, duration=300):
    x, y = _resolve_coord(*args)
    run_adb_command(["shell", "input", "swipe", str(x), str(y), str(x), str(y), str(duration)])


def take_screenshot(save=False):
    device = get_device_id()
    raw = subprocess.check_output(["adb", "-s", str(device), "exec-out", "screencap", "-p"])

    img_array = np.frombuffer(raw, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if img is None:
        raise RuntimeError("Failed to decode the image")
    elif save:
        os.makedirs(config.CACHE_DIR, exist_ok=True)
        cv2.imwrite(str(config.CACHE_DIR / f"wos-{int(time.time())}.png"), img)

    return img


def is_game_running(package=None):
    """True if the game process exists on the device."""
    component = package or config.GAME_COMPONENT
    package_name = component.split("/")[0]
    try:
        device = get_device_id()
        result = subprocess.run(
            ["adb", "-s", device, "shell", "pidof", package_name],
            capture_output=True, text=True, timeout=10,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def start_game(component=None):
    component = component or config.GAME_COMPONENT
    run_adb_command(["shell", "am", "start", "-n", component])


def ensure_game_running(component=None, wait_sec=25):
    """Start the game if it is not running and wait for its process."""
    if is_game_running(component):
        return True
    start_game(component)
    deadline = time.time() + wait_sec
    while time.time() < deadline:
        time.sleep(2)
        if is_game_running(component):
            time.sleep(5)  # allow the splash screen to settle
            return True
    return False


def clear_input(count=6):
    run_adb_command(["shell", "input", "keyevent", "123"])
    for _ in range(count):
        run_adb_command(["shell", "input", "keyevent", "67"])


def input_text(text, backspace=6):
    text = text.replace(" ", "%s")
    clear_input(count=backspace)
    run_adb_command(["shell", "input", "text", text])
    run_adb_command(["shell", "input", "keyevent", "66"])
    print(f"Text Input: {text}")
