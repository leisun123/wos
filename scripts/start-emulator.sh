#!/usr/bin/env bash
# 启动（或复用已运行的）wos AVD 模拟器并等待开机完成
set -e
export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-$HOME/Library/Android/sdk}"
ADB="$ANDROID_SDK_ROOT/platform-tools/adb"

if "$ADB" devices | grep -q "emulator-5554.*device"; then
  echo "模拟器已在运行"
else
  nohup "$ANDROID_SDK_ROOT/emulator/emulator" -avd wos -netdelay none -netspeed full \
    > /tmp/wos-emulator.log 2>&1 &
  echo "模拟器启动中..."
fi

"$ADB" wait-for-device
"$ADB" shell 'while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 2; done'
echo "模拟器就绪: emulator-5554 ($("$ADB" shell wm size | tr -d '\r'))"
