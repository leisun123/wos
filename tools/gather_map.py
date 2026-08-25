"""Map-scan gathering loop for the CN client (furnace < search unlock).

Loop: screenshot -> detect mine icons (dark core + light-blue ring) ->
tap -> classify popup (mine detail vs empty plot) -> deploy chain
(quick-select / equalize / deploy) -> repeat until no free queue.
"""
import sys, time
import cv2
import numpy as np

sys.path.insert(0, "/Users/sunl/.zcode/workspace/default/wos-audit/wos")
from core.core import req_ocr
from cmd_program.screen_action import tap_screen, take_screenshot, swipe_screen

MAX_ROUNDS = 20          # dispatch attempts
MAX_MISS = 8             # consecutive plot-misses before giving up
# long drags, 3 in the same direction before rotating (escape empty areas)
SWIPE_STEPS = [(800, 1500, 250, 900)] * 3 + [(280, 1500, 830, 900)] * 3 + \
              [(540, 1800, 540, 700)] * 3 + [(540, 700, 540, 1800)] * 3


def detect_mines(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h_, s_, v_ = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    dark = ((v_ < 150) | ((s_ > 90) & (v_ < 200))).astype(np.uint8) * 255
    dark[:430, :] = 0; dark[2180:, :] = 0; dark[:, 930:] = 0; dark[:, :40] = 0
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, _, stats, centroids = cv2.connectedComponentsWithStats(dark, 8)
    H, W = dark.shape
    pts = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if not (20 <= w <= 80 and 20 <= h <= 80 and 0.5 <= w / max(h, 1) <= 2.0):
            continue
        cx, cy = int(centroids[i][0]), int(centroids[i][1])
        ok = 0
        for ang in range(0, 360, 45):
            a = np.deg2rad(ang)
            px = int(cx + 30 * np.cos(a)); py = int(cy + 30 * np.sin(a))
            if 0 <= px < W and 0 <= py < H:
                ph, ps, pv = hsv[py, px]
                if 105 <= ph <= 125 and 8 <= ps <= 110 and pv > 218:
                    ok += 1
        if ok >= 6:
            pts.append((cx, cy))
    uniq = []
    for p in sorted(pts):
        if not uniq or (p[0] - uniq[-1][0]) ** 2 + (p[1] - uniq[-1][1]) ** 2 > 60 ** 2:
            uniq.append(p)
    return uniq


def ocr_texts(img=None):
    path = "/tmp/_gather_loop.png"
    cv2.imwrite(path, img if img is not None else take_screenshot())
    res = req_ocr(img_path=path) or []
    return res


def close_popup():
    """Close whatever popup is open via the BACK key (safe: game only exits
    from the base screen, and we detect+cancel the exit dialog)."""
    import subprocess
    subprocess.run(["adb", "shell", "input", "keyevent", "4"], capture_output=True)
    time.sleep(1.5)
    res = ocr_texts()
    texts = " ".join(i["text"] for i in res)
    if "确认退出" in texts:
        cancel = next((i for i in res if "取消" in i["text"]), None)
        if cancel:
            x1, y1, x2, y2 = cancel["box"]
            tap_screen((x1 + x2) // 2, (y1 + y2) // 2)
            time.sleep(1.5)


def popup_open(res):
    texts = " ".join(i["text"] for i in res)
    return any(k in texts for k in ("所属联盟", "建造", "迁城", "占领", "等级", "奖励"))


def try_deploy():
    """From a target detail popup, run the deploy chain. True if a march left."""
    res = ocr_texts()
    texts = {i["text"] for i in res}
    if not any(k in texts for k in ("出征", "采集")):
        print("    详情无 出征/采集 按钮:", list(texts)[:8])
        return False
    # press 出征 / 采集 on the detail popup
    btn = next((i for i in res if "出征" in i["text"] or "采集" in i["text"]), None)
    if not btn:
        return False
    x1, y1, x2, y2 = btn["box"]
    tap_screen((x1 + x2) // 2, (y1 + y2) // 2)
    time.sleep(2.5)

    # deploy panel: quick-select -> equalize -> deploy
    for label in ("快速选择", "平均配置"):
        res2 = ocr_texts()
        b = next((i for i in res2 if label in i["text"]), None)
        if b:
            x1, y1, x2, y2 = b["box"]
            tap_screen((x1 + x2) // 2, (y1 + y2) // 2)
            time.sleep(1.8)

    res3 = ocr_texts()
    dep = [i for i in res3 if "出征" in i["text"]]
    if not dep:
        print("    出征面板未打开")
        return False
    # the big deploy button is the bottom-right one (max y)
    b = max(dep, key=lambda i: i["box"][3])
    x1, y1, x2, y2 = b["box"]
    tap_screen((x1 + x2) // 2, (y1 + y2) // 2)
    time.sleep(3.5)

    after = ocr_texts()
    at = " ".join(i["text"] for i in after)
    deployed = "快速选择" not in at  # panel closed
    print("    派遣后状态:", "已派遣" if deployed else "面板仍在", "|", at[:60])
    return deployed


def main():
    deployed_count = 0
    miss_streak = 0
    swipe_i = 0
    tried = set()

    for rnd in range(MAX_ROUNDS):
        img = take_screenshot()
        # make sure no leftover popup covers the map
        if popup_open(ocr_texts(img)):
            print("    检测到残留弹窗，先关闭")
            close_popup()
            img = take_screenshot()
        mines = [m for m in detect_mines(img)
                 if not any((m[0]-t[0])**2 + (m[1]-t[1])**2 < 120**2 for t in tried)]
        print(f"[{rnd}] 视野矿点: {mines}")

        if not mines:
            print("    无矿，拖动换视野")
            swipe_screen(*SWIPE_STEPS[swipe_i % len(SWIPE_STEPS)], duration=400)
            swipe_i += 1
            time.sleep(2.2)
            continue

        x, y = mines[0]
        tried.add((x, y))
        tap_screen(x, y)
        time.sleep(2.8)

        res = ocr_texts()
        texts = " ".join(i["text"] for i in res)
        if "荒原" in texts or "建造" in texts:
            print(f"    ({x},{y}) 点中地块(荒原)，关闭重试")
            close_popup()
            miss_streak += 1
            if miss_streak >= MAX_MISS:
                print("连续 miss 过多，结束")
                break
            continue
        miss_streak = 0

        print(f"    ({x},{y}) 弹出目标详情: {texts[:60]}")
        if try_deploy():
            deployed_count += 1
            print(f"    === 第 {deployed_count} 次派遣成功 ===")
        else:
            close_popup()

    print(f"完成：共派遣 {deployed_count} 次")


if __name__ == "__main__":
    main()
