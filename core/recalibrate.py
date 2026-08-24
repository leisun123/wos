import os
import time
import cv2
from core.core import req_ocr, tap_on_template, tap_on_text, tap_on_templates_batch, req_text
from cmd_program.screen_action import tap_screen, take_screenshot
from core import config, i18n


def _save_unknown_screenshot(reason):
    """Persist a screenshot of an unrecognized screen for later analysis."""
    try:
        os.makedirs(config.LOGS_DIR, exist_ok=True)
        frame = take_screenshot()
        path = config.LOGS_DIR / f"unknown_{reason}_{int(time.time())}.png"
        cv2.imwrite(str(path), frame)
        print(f"Unknown screen saved: {path}")
    except Exception as e:
        print(f"Screenshot save failed: {e}")


def recalibrate(timeout=30):
    is_home = False
    blind_taps = 0
    start = time.time()

    # Percentage-based coordinates
    center_x_pct, center_y_pct = 50, 50  # Center of screen
    top_left_x_pct, top_left_y_pct = 6.48, 6.9  # Top-left area

    while(not is_home) and ((time.time()) - start) < timeout:
        found = False
        time.sleep(1)
        text = req_text("Home.World")

        try:
            text = text[0][0].lower()
        except Exception as e:
            print("Finding The Homepage...")

        if text == i18n.t("world").lower():
            is_home = True
        elif text == i18n.t("city").lower():
            tap_on_text("World.City", sleep=2)
            is_home = True

        if is_home:
            print("On homepage")
            time.sleep(1)
            break
        found = tap_on_templates_batch(
            [
                "Global.Back",
                "Global.Close",
                "FirstPurchase.Close",
                "Home.Store.Back"

            ],
            wait=1,
            parallel = True
        )

        # localized reconnect / dismiss prompts
        targets = {i18n.t(t).lower() for t in [
            "tap anywhere to continue",
            "tap to exit",
            "click to continue",
            "click anywhere to exit",
            "reconnect"
        ]}
        res = req_ocr()
        for item in res:
            if item["text"].lower() in targets:
                box = item["box"]
                coord = ((box[0]+box[2])//2, (box[1]+box[3])//2)
                tap_screen(coord)
                found = True

        if not found:
            time.sleep(1)
            text = req_text("Home.World")
            try:
                text = text[0][0]
            except Exception as e:
                print(f"Error... {e}")
            if text:
                found = True
                if text.lower() != i18n.t("city").lower() and text.lower() != i18n.t("world").lower():
                    tap_screen(center_x_pct, center_y_pct)
            else:
                found = False

        if found:
            start = time.time()
            blind_taps = 0
        else:
            # Unknown screen: cap speculative taps, keep evidence, exit safely.
            blind_taps += 1
            if blind_taps == 1:
                _save_unknown_screenshot("page")
            if blind_taps > config.RECALIBRATE_BLIND_TAP_LIMIT:
                _save_unknown_screenshot("giveup")
                raise RuntimeError(
                    "Unknown screen: blind-tap limit reached, stopping safely "
                    "(see logs/ for screenshots)"
                )
            tap_screen(top_left_x_pct, top_left_y_pct)
            time.sleep(1)


    time.sleep(1)
    if not is_home:
        _save_unknown_screenshot("timeout")
        raise RuntimeError("Homepage Not found, Runtime Error. Stopping the Bot...")
