"""Central configuration for the wos bot.

All runtime knobs are read from environment variables (optionally prefixed
with WOS_) so the same checkout works on any machine / device without code
edits. Nothing in this module touches ADB at import time.
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- Device -----------------------------------------------------------
# Preferred adb serial. If empty, the first connected device is used.
ADB_SERIAL = os.getenv("WOS_ADB_SERIAL", "").strip()

# --- Game -------------------------------------------------------------
# Android component of the game. International build by default; the CN
# build has a different package name — check with:
#   adb shell pm list packages | grep -i <keyword>
GAME_COMPONENT = os.getenv(
    "WOS_PACKAGE", "com.gof.global/com.unity3d.player.MyMainPlayerActivity"
)

# --- Language ---------------------------------------------------------
# UI language of the game client: "en" or "zh".
# Selects OCR model language and the TextArea text overlay.
LANG = os.getenv("WOS_LANG", "en").strip().lower()
OCR_LANG = os.getenv("WOS_OCR_LANG", LANG if LANG in ("en", "zh") else "en").strip().lower()

# --- Resolution -------------------------------------------------------
# Forces a resolution ("WxH", e.g. "1080x2460"). If empty the real device
# resolution is detected once via `adb shell wm size`.
RESOLUTION = os.getenv("WOS_RESOLUTION", "").strip()

# Fallback resolution when no device is connected (tests, offline imports).
FALLBACK_WIDTH = 1080
FALLBACK_HEIGHT = 2460

# --- Behaviour --------------------------------------------------------
# Per-task timeout in seconds (task isolation in bot/task_menu.py).
TASK_TIMEOUT_SEC = float(os.getenv("WOS_TASK_TIMEOUT", "1800"))

# Number of consecutive unknown-screen taps recalibrate() allows before it
# gives up safely (screenshots are saved to logs/).
RECALIBRATE_BLIND_TAP_LIMIT = int(os.getenv("WOS_RECAL_BLIND_TAPS", "8"))

# Directories (project-root relative, so cwd does not matter)
LOGS_DIR = PROJECT_ROOT / "logs"
CACHE_DIR = PROJECT_ROOT / "cache"
DB_DIR = PROJECT_ROOT / "db"
REFERENCES_DIR = PROJECT_ROOT / "references"
TEXT_AREA_DIR = REFERENCES_DIR / "text_area"
# Optional per-language overlay: {"TextArea.Key": {"text": "<localized text>"}}
TEXT_AREA_OVERLAY_FILE = REFERENCES_DIR / f"text_area.{LANG}.json"
