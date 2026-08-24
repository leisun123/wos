"""Offline unit tests — no device / OCR server required."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import config, i18n  # noqa: E402
from cmd_program import screen_action as sa  # noqa: E402
from core import coord_utils as cu  # noqa: E402


def _fake_size(w, h):
    sa._screen_size = (w, h)
    yield
    sa._screen_size = None


def test_percent_conversion_int_and_float(monkeypatch):
    """int 0..100 and float 0..100 must both be treated as percentages."""
    monkeypatch.setattr(sa, "_screen_size", (1080, 2460), raising=False)
    assert sa._convert_if_percentage(50, 1080) == 540        # int percent (old bug)
    assert sa._convert_if_percentage(50.93, 1080) == 550      # float percent
    assert sa._convert_if_percentage(540, 1080) == 540        # pixel passthrough
    assert sa._convert_if_percentage(1200, 2460) == 1200      # pixel passthrough


def test_percent_conversion_other_resolution(monkeypatch):
    monkeypatch.setattr(sa, "_screen_size", (720, 1280), raising=False)
    assert sa._convert_if_percentage(50, 720) == 360
    assert sa._convert_if_percentage(50, 1280) == 640


def test_coord_utils_live_resolution(monkeypatch):
    monkeypatch.setattr(sa, "_screen_size", (1440, 3200), raising=False)
    assert cu.percent_to_pixel(50, 25) == (720, 800)
    assert cu.percent_to_pixel(50, 25, screen_width=1000, screen_height=500) == (500, 125)
    assert cu.box_percent_to_pixel([0, 0, 50, 50]) == [0, 0, 720, 1600]


def test_pixel_clamped(monkeypatch):
    monkeypatch.setattr(sa, "_screen_size", (1080, 2460), raising=False)
    assert sa._convert_if_percentage(9999, 1080) == 1080


def test_i18n_passthrough_en(monkeypatch):
    monkeypatch.setattr(config, "LANG", "en")
    assert i18n.t("city") == "city"


def test_i18n_zh_literals(monkeypatch):
    monkeypatch.setattr(config, "LANG", "zh")
    assert i18n.t("city") == "城市"
    assert i18n.t("Gather") in ("Gather", "采集")


def test_import_all_modules():
    """The whole package must import without a connected device."""
    import Main.task_menu  # noqa: F401
    import Main.main  # noqa: F401
    import core.core  # noqa: F401
    import core.recalibrate  # noqa: F401
    import usecases.gather  # noqa: F401
    import usecases.alliance  # noqa: F401
    import usecases.training_troops  # noqa: F401
