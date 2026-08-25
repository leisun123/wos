"""CN gathering: state-machine loop.

Every iteration screenshots, classifies the screen state, and acts:
  promo popup / exit dialog / plot detail / player-city detail ->
  close; mine detail -> deploy chain then search-next; deploy panel ->
  finish deploy; world map -> tap march slot to jump to the active mine.
"""
import sys, time, subprocess
import cv2

sys.path.insert(0, "/Users/sunl/.zcode/workspace/default/wos-audit/wos")
from core.core import req_ocr
from cmd_program.screen_action import tap_screen, take_screenshot

MAX_DEPLOYS = 6
MAX_ROUNDS = 60


def snap():
    img = take_screenshot()
    cv2.imwrite("/tmp/_sm.png", img)
    return req_ocr(img_path="/tmp/_sm.png") or []


def t_of(res):
    return " ".join(i["text"] for i in res)


def tap_item(item):
    x1, y1, x2, y2 = item["box"]
    tap_screen((x1 + x2) // 2, (y1 + y2) // 2)


def fx(res, word):
    return next((i for i in res if i["text"].strip() == word), None)


def fc(res, word):
    return next((i for i in res if word in i["text"]), None)


def back():
    subprocess.run(["adb", "shell", "input", "keyevent", "4"], capture_output=True)
    time.sleep(1.6)
    res = snap()
    if "确认退出" in t_of(res):
        c = fx(res, "取消")
        if c:
            tap_item(c)
            time.sleep(1.2)
    return res


def classify(res):
    t = t_of(res)
    if "确认退出" in t:
        return "exit_dialog"
    if "储量" in t and fx(res, "采集"):
        return "mine_detail"
    if any(k in t for k in ("快速选择", "平均配置")):
        return "deploy_panel"
    if any(k in t for k in ("建造", "迁城", "占领", "所属联盟")):
        return "plot_detail"
    if "战斗力" in t or "城镇援军" in t:
        return "city_detail"
    # full-screen promo covers the top resource bar -> no 统帅 visible
    if "统帅" not in t and any(k in t for k in ("万象杂货", "免费领取", "储值有礼", "跳过")):
        return "promo"
    if "统帅" in t:
        return "world"
    return "unknown"


def deploy_chain():
    """Deploy panel is open: quick-select, equalize, deploy."""
    res = snap()
    for word in ("快速选择", "平均配置"):
        it = fx(res, word)
        if it:
            tap_item(it)
            time.sleep(1.6)
            res = snap()
    deps = [i for i in res if "出征" in i["text"]]
    if not deps:
        print("    出征按钮缺失")
        return False
    tap_item(max(deps, key=lambda i: i["box"][3]))
    time.sleep(4)
    return "行军" in t_of(snap())


def main():
    deploys = 0
    for rnd in range(MAX_ROUNDS):
        if deploys >= MAX_DEPLOYS:
            print("达到最大派遣数")
            break
        res = snap()
        state = classify(res)
        t = t_of(res)
        print(f"[{rnd}] {state}: {t[:70]}")

        if state == "mine_detail":
            lvl = fc(res, "等级")
            rsv = [i["text"] for i in res if "," in i["text"]]
            print(f"    矿: {lvl['text'] if lvl else '?'} 储量: {rsv[:2]}")
            tap_item(fx(res, "采集"))
            time.sleep(2.5)
            if deploy_chain():
                deploys += 1
                print(f"    === 派遣 {deploys} 成功 ===")
                time.sleep(1.5)
                # after deploy, reopen a mine detail and search next full
                res2 = snap()
                if classify(res2) == "mine_detail":
                    chk = fc(res2, "仅搜索")
                    if chk:
                        x1, y1, x2, y2 = chk["box"]
                        tap_screen(x1 - 60, (y1 + y2) // 2)
                        time.sleep(1.0)
                        res2 = snap()
                    go = fx(res2, "搜索")
                    if go:
                        tap_item(go)
                        time.sleep(3.5)
                        print("    已搜索下一个满矿")
            continue

        if state == "deploy_panel":
            if deploy_chain():
                deploys += 1
                print(f"    === 派遣 {deploys} 成功(恢复面板) ===")
            continue

        if state in ("plot_detail", "city_detail"):
            back()
            continue

        if state == "promo":
            # close via X at top-right of the promo panel, fallback back-key
            tap_screen(1010, 640)
            time.sleep(1.5)
            res2 = snap()
            if classify(res2) == "promo":
                back()
            continue

        if state == "exit_dialog":
            c = fx(res, "取消")
            if c:
                tap_item(c)
                time.sleep(1.2)
            continue

        if state == "world":
            # busy march slot's 查看 button is a fixed screen element
            # (green, small text OCR can't read) at ~(165, 278)
            tap_screen(165, 278)
            time.sleep(3)
            continue

        # unknown -> back key and retry
        back()
        time.sleep(0.5)

    print(f"结束：共派遣 {deploys} 次")


if __name__ == "__main__":
    main()
