import time
from core.recalibrate import recalibrate
from core import i18n

from core.core import (
    req_ocr,
    req_text,
    tap_on_text,
    req_temp_match,
    tap_on_template,
    tap_on_templates_batch
)
from cmd_program.screen_action import(
    tap_screen,
    swipe_screen,
    input_text
)


def _read_march_queue():
    """Read the world march queue counter (e.g. "2/5").

    Newer game builds replaced the counter with per-slot indicators, so this
    returns None when the counter is absent — callers then fall back to
    dispatch-until-fail flow instead of guessing.
    """
    time.sleep(0.5)
    try:
        data = req_text('World.MarchQueue')[0][0].split('/')
        occupied = int(data[0])
        total = int(data[1])
        return occupied, total - occupied
    except Exception as e:
        print(f"March queue counter not available - {e}")
        return None


def wait_till_return(lowest_time=14400):
    recalling = recall_current_gathering(lowest_time=lowest_time)
    while(recalling):
        time.sleep(0.5)
        return_times = req_text(
                [
                "World.FirstMarchTime",
                "World.SecondMarchTime",
                "World.ThirdMarchTime",
                "World.FourthMarchTime",
                "World.FifthMarchTime"
            ]
        )
        times = []
        for i, return_time in enumerate(return_times):
            try:
                return_time = return_time[0].split(':')
                return_time = [int(t) for t in return_time]
                return_time = return_time[0]*3600 + return_time[1]*60 + return_time[2]
                times.append(return_time)
            except Exception as e:
                print(f"Couldn't read the time properly - {e}")

        if len(times) <= 1:
            break

        waiting_time = max(times) if len(times)>0 else 0
        if waiting_time > 600:
            recalling = recall_current_gathering(lowest_time=lowest_time)
            continue
        elif waiting_time == 0:
            recalling = False
            break
        print(f"Waiting for {waiting_time} seconds for the troops to return home...")
        time.sleep(waiting_time)


def _search_and_gather(node, level, search_box):
    """Search one resource type at one level and press Gather.

    Returns True when the Gather button was found (a march was started),
    False when the level/node yielded no Gather button.
    """
    found = tap_on_text(node, rois=search_box, wait=2)
    if found is None:
        swipe_screen(92.59, 78.05, 0, 78.05)
        tap_on_text(node, rois=search_box, wait=2)

    time.sleep(0.5)
    try:
        current_level = req_text("World.Search.ItemLevel")[0][0]
        if current_level != str(level):
            tap_screen(84.26, 86.22)
            time.sleep(1)
            input_text(str(level))
    except Exception:
        print("Level reading Error, Continuing without reading the level...")

    if not tap_on_text("World.Search.Search", wait=2):
        print("Search button not found")
        return False
    return bool(tap_on_text("World.Search.Gather", wait=5))


def gather(remove_hero=False, equalize=True, lowest_time=14400,
           level=8, min_level=5):
    """Dispatch all free march queues to gather resources.

    level/min_level: target resource level; when no Gather button shows up
    for a node, the search level is lowered one step (down to min_level)
    before moving on to the next resource type.
    """
    print("Started Gathering...")
    search_box = [[0, 78.86, 100, 80.49]]
    gathering_nodes = ["meat", "wood", "coal", "iron", "coal", "iron"]
    city_text = i18n.t("city").lower()

    time.sleep(0.5)
    title = req_text("World.City")
    try:
        title = title[0][0].lower()
    except Exception as e:
        print(f"Reading Error - {e}")
    if title != city_text:
        recalibrate()
        tap_on_text("Home.World", wait=2)

    wait_till_return(lowest_time=lowest_time)

    queue = _read_march_queue()
    unknown_queue = queue is None
    if unknown_queue:
        # New UI without an "x/5" counter: rely on dispatch outcomes instead.
        print("March queue counter not available, using dispatch-until-fail flow.")
        occupied_march, remaining_march = 0, 99
    else:
        occupied_march, remaining_march = queue
    i = 0
    fail_streak = 0

    while remaining_march > 0 and occupied_march < 5:
        title = tap_on_text("World.City", tap=False)
        if not title:
            tap_screen(50.93, 50.41)
            time.sleep(0.5)
        if not unknown_queue:
            print(f"Remaining march queue: {remaining_march} ----- Occupied March: {occupied_march}")
        status = tap_on_template("World.Search", wait=2, threshold=0.6)
        if not status:
            print("Seach Icon not found, Exiting the task...")
            return

        gathered = False
        node_level = level
        # try the node at the target level, then step the level down
        while node_level >= min_level:
            if _search_and_gather(gathering_nodes[i], node_level, search_box):
                gathered = True
                break
            print(f"No level {node_level} {gathering_nodes[i]} found, lowering the level...")
            node_level -= 1
            time.sleep(0.5)

        if not gathered:
            fail_streak += 1
            print(f"No gatherable {gathering_nodes[i]} down to level {min_level} (fail streak {fail_streak})")
            if fail_streak >= len(gathering_nodes):
                print("No gatherable nodes for any resource, ending the gathering task.")
                break
            i = (i + 1) % 5
            continue
        fail_streak = 0

        if remove_hero:
            tap_on_template("World.Deploy.RemoveHero", threshold=0.6, rois=[[27.78, 20.33, 37.04, 26.42]], wait=2)  # removing hero
        if equalize:
            tap_on_text("World.Deploy.Equalize", wait=2)
        deployed = tap_on_text("World.Deploy.Deploy", wait=2, sleep=0.5)
        if not deployed:
            # Deploy button missing usually means no free march queue left.
            print("Deploy button not found — treating as no free march queue, ending task.")
            break

        i = (i + 1) % 5

        if not unknown_queue:
            queue = _read_march_queue()
            if queue is None:
                print("Lost the march queue counter after deploy, ending task.")
                break
            occupied_march, remaining_march = queue

    time.sleep(0.5)
    text = req_text("World.City")
    try:
        text = text[0][0]
        if text.lower() != city_text:
            tap_screen(50.93, 50)
    except Exception as e:
        print("The search tab may still opened, Trying to recover...")
    print("Completed the gathering task, Returning to homepage...")
    recalibrate()



def recall_current_gathering(lowest_time=14400):
    time.sleep(0.5)
    title = req_text("World.City")
    recalling = False
    try:
        title = title[0][0].lower()
    except Exception as e:
        print(f"Reading Error - {e}")
    if title != i18n.t("city").lower():
        recalibrate()
        tap_on_text("Home.World", sleep=2)

    time.sleep(0.5)
    march_time = req_text("World.FirstMarchTime")
    try:
        march_time = march_time[0][0].split(':')
        march_time = [int(t) for t in march_time]
        march_time = march_time[0]*3600 + march_time[1]*60 + march_time[2]
    except Exception as e:
        print(f"Couldn't read the time properly - {e}")
        march_time = None

    if march_time is None:
        # No readable march timer means no march is out — nothing to recall.
        return False

    if march_time < lowest_time:
        found = True
        recalling = True
        while found:
            found = tap_on_template("World.Recall", threshold = 0.95, wait=2, sleep=0.5)
            tap_on_text("World.Recall.Confirm", wait=2, sleep=1)

    return recalling
