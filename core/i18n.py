"""Lightweight i18n for hardcoded UI strings.

The game UI text the bot looks for comes from three places:
  1. references/text_area/*.json  — key -> {"text": <english sample>, "box": ...}
  2. literal strings passed to tap_on_text() in usecases (e.g. "meat")
  3. inline comparisons in code (e.g. `title != "city"`)

For WOS_LANG=zh:
  - key-based texts are overridden by references/text_area.zh.json
  - literals are mapped through LITERAL_ZH below

The Chinese values are best-effort and MUST be verified against real
screenshots of the CN client (真机截图确认) — adjust them in
text_area.zh.json / LITERAL_ZH as needed. Matching is fuzzy (rapidfuzz),
so close-but-not-exact values usually still work.
"""
import json

from core import config

# English literal -> Chinese (verify on a real CN-client screenshot)
LITERAL_ZH = {
    # world / page titles
    "city": "城市",
    "world": "世界",
    # resource names (world search panel)
    "meat": "肉",
    "wood": "木",
    "coal": "煤",
    "iron": "铁",
    # common buttons
    "claim": "领取",
    "gather": "采集",
    "search": "搜索",
    "deploy": "出征",
    "help": "帮助",
    "train": "训练",
    # troop types
    "infantry": "步兵",
    "lancer": "矛兵",
    "marksman": "弓兵",
    # dialogs / reconnect prompts
    "tap anywhere to continue": "点击任意位置继续",
    "tap to exit": "点击退出",
    "click to continue": "点击继续",
    "click anywhere to exit": "点击任意位置退出",
    "reconnect": "重新连接",
}

_text_area_overlay = None


def _load_overlay():
    global _text_area_overlay
    if _text_area_overlay is None:
        _text_area_overlay = {}
        path = config.TEXT_AREA_OVERLAY_FILE
        if config.LANG != "en" and path.exists():
            try:
                with open(path, "r") as f:
                    _text_area_overlay = json.load(f)
            except Exception as e:
                print(f"Failed to load TextArea overlay {path}: {e}")
    return _text_area_overlay


def t(text):
    """Translate a literal UI string for the configured language."""
    if config.LANG == "zh" and isinstance(text, str):
        return LITERAL_ZH.get(text.lower(), text)
    return text


def text_area_text(key, default_text):
    """Localized `text` value for a TextArea key (overlay wins)."""
    overlay = _load_overlay()
    entry = overlay.get(key)
    if isinstance(entry, dict) and entry.get("text"):
        return entry["text"]
    if isinstance(entry, str):
        return entry
    if config.LANG == "zh":
        # fall back to the literal map so bare keys like "World.City" still
        # have a chance when the overlay has not been filled in yet
        return t(default_text)
    return default_text
