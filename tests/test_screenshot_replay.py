"""Screenshot replay tests (marked slow — run by the Nightly workflow).

Purpose: verify OCR / text expectations against real device screenshots
without needing a phone connected. Runs the OCR stack in-process on
static images (img_path), so no ADB device is required.

How to add cases:
  1. Save screenshots (ideally ~1080x2460; other sizes are resized) into
     tests/fixtures/screenshots/, e.g. home_zh.png, world_search_zh.png
  2. Create tests/fixtures/expectations.json:

     {
       "home_zh.png":        {"lang": "zh", "contains": ["城市"]},
       "world_search_zh.png": {"lang": "zh", "contains": ["采集"]}
     }

Until both files exist these tests collect zero cases and cost nothing.
"""
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
SCREENSHOTS = FIXTURES / "screenshots"
EXPECTATIONS = FIXTURES / "expectations.json"

pytestmark = pytest.mark.slow


def _cases():
    if not EXPECTATIONS.exists():
        return []
    try:
        manifest = json.loads(EXPECTATIONS.read_text(encoding="utf-8"))
    except Exception as e:
        pytest.fail(f"Invalid {EXPECTATIONS}: {e}")
    return [
        (name, entry)
        for name, entry in sorted(manifest.items())
        if isinstance(entry, dict) and (SCREENSHOTS / name).exists()
    ]


@pytest.fixture(scope="module")
def ocr_client():
    cases = _cases()
    if not cases:
        pytest.skip("no screenshot fixtures/expectations yet")

    langs = {entry.get("lang", "en") for _, entry in cases}
    if len(langs) > 1:
        pytest.skip("mixed-language fixtures not supported in a single run")

    # config.OCR_LANG was resolved at import time — patch before the engine
    # is built (init_services reads it when constructing PaddleOCR).
    from core import config
    config.OCR_LANG = "ch" if langs.pop() == "zh" else "en"

    from fastapi.testclient import TestClient
    import core.ocr as ocr_server

    ocr_server.init_services()
    yield TestClient(ocr_server.app)


@pytest.mark.parametrize("name,entry", _cases(), ids=[n for n, _ in _cases()])
def test_screenshot_text(ocr_client, name, entry):
    payload = {"img_path": str(SCREENSHOTS / name)}
    resp = ocr_client.post("/ocr", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("success") is True, data.get("error")

    texts = " ".join(item["text"] for item in data["results"] or [])
    for expected in entry.get("contains", []):
        assert expected in texts, (
            f"{expected!r} not found in OCR output of {name}. OCR saw: {texts!r}"
        )
