# 国服（中文版）适配调试记录

日期：2026-08-24
环境：macOS M3 Pro / AVD 模拟器 1080×2400 / 国服 com.gof.china 1.15.6（渠道包）

> 本文档记录在真实国服客户端上校准的结论与未完成事项，供下一轮调试直接续接。

## 一、环境结论（已搭建完成）

| 项 | 值 |
|---|---|
| SDK | `~/Library/Android/sdk`（brew cask android-commandlinetools + emulator + platform-tools + system-images;android-34;google_apis;arm64-v8a） |
| AVD | `wos`（手工构建 `~/.android/avd/wos.avd`；1080×2400@440dpi，RAM 4GB，data 16G） |
| 国服包名 | `com.gof.china`（启动组件 `com.unity3d.player.DDUnityLaunchActivity`，**不是**国际服的 MyMainPlayerActivity） |
| APK | 用户手动下载的渠道包 1.15.6/135（MD5 `4f4faa7ad1310a57b7289c9d65db9a9e`；TapTap 官方包 MD5 为 `ed02bc59...`，二者不同属正常渠道差异） |
| 本地 env | 仓库 `.wos.env`（gitignored）：`WOS_ADB_SERIAL=emulator-5554`、`WOS_LANG=zh`、`WOS_OCR_PORT=8100`（8000 被本机其他进程占用）、`WOS_PACKAGE=com.gof.china/...DDUnityLaunchActivity` |
| 脚本 | `scripts/start-emulator.sh` / `run-ocr.sh` / `run-bot.sh`（自动 source .wos.env） |

AVD 备注：`avdmanager create avd` 报 "Package path is not valid" 识别不了已装镜像（brew cask 路径问题），手工写 `wos.ini + wos.avd/config.ini` 即可，注意必须含 `abi.type=arm64-v8a` 和 `hw.cpu.arch=arm64`，否则 QEMU 报 "CPU Architecture 'arm' is not supported"。

## 二、代码修复（本次已完成）

1. **脚本方式运行的循环 import**：`python core/ocr.py` 时 sys.path[0]=core/ 目录，`core/core.py` 文件遮蔽 `core` 包 → 两处入口改为 `sys.path.insert(0, 项目根)`。
2. **PaddleOCR 语言代码**：中文是 `ch` 不是 `zh`，`core/config.py` 已做映射（`WOS_LANG=zh → OCR_LANG=ch`）。
3. **OCR 服务端口可配置**：`WOS_OCR_PORT`（默认 8000），`core/core.py` 与 `core/ocr.py` 同步读取。
4. **`/template` 不带 threshold 崩溃**：`match_template` 里 None 比较 → 默认 0.8。
5. **系统代理劫持 localhost 请求**：Clash(7890)/SOOCKS 环境变量会让 requests 对 127.0.0.1 的请求超时 → `core/core.py` 改用 `requests.Session(trust_env=False)`。curl 探测也要 `--noproxy '*'`。
6. **gather.py 重构（适配新版 UI）**：
   - 行军队列计数读不到时不再中止，走 **dispatch-until-fail** 流程（`unknown_queue` 分支）；
   - 「出征」按钮点不到 ⇒ 视为无空闲队伍，结束任务；
   - 连续 `len(gathering_nodes)` 次找不到可采资源 ⇒ 结束任务；
   - `recall_current_gathering`：march_time 读不到（None）= 没有队伍在外，**不再触发召回**（上游 bug）。

## 三、中文校准结论（关键资产）

### 已验证可用

- **PaddleOCR 中文识别质量很好**：主城全屏 27 条文本全对（统帅8/资源数/温度/大熔炉/升级/能量值…）。
- **页面切换词**（同一按钮位置，主城与世界地图互切，box 沿用英文版百分比坐标有效）：
  - 主城 → 世界地图按钮：英文 "World" ⇒ 国服「**野外**」（右下，约 [933,2341]）
  - 世界地图 → 主城按钮：英文 "City" ⇒ 国服「**城镇**」（右下，同位置）
  - 已写入 `references/text_area.zh.json` 和 `core/i18n.py` 的 LITERAL_ZH。
- **世界地图底导航**：探险/英雄/背包/商店/联盟/城镇（y≈2340）。

### 已确认的 UI 变化（与上游英文版布局不同）

1. **行军队列**：上游是 "x/5" 计数（`World.MarchQueue`），国服 1.15.6 改为**槽位列表**（世界地图左上面板，约 x60-460、y250-600）：忙槽=头像+查看/倒计时，空闲槽=蓝色「空闲」按钮，未解锁槽=灰蓝。⇒ 计数 OCR 不可行，已改 dispatch-until-fail。
2. **左下角金色放大镜**（约 (97,1795)，上游 `World.Search` 模板 0.93 高分命中同一位置）在国服打开的是「**野兽狩猎面板**」（等级/搜索/自动狩猎），**不是资源搜索**。上游的 `World.Search` 语义在国服已变。
3. 之前一次误匹配：threshold=0.6 无 ROI 全屏搜索会点错（点到地图杂斑）。**模板点击必须配 ROI**（`references/icon/template_config.json` 支持按名配 box/threshold）。

### 试过但不可行的方案（不要重试）

- 「空闲」按钮小字 OCR：PaddleOCR det 识别不出（score < 0.8），放大 3× 也不行。
- 「空闲」按钮颜色条带检测：面板展开状态不同背景色不同（一张整片蓝、一张几乎无蓝），不可靠。
- 纯蓝按钮做模板匹配：近纯色图到处高分（行军条也 1.0），误匹配。

## 四、未完成 / 下一轮续接点

1. **找到国服的资源搜索入口**（最关键阻塞）：候选=世界地图右侧竖排按钮列顶部的金色圆图标，修正后坐标 **(990, 810)**（1080×2400 下），上次已点但未来得及验证截图。若不是，做一次全图视觉扫描或查国服攻略确认"搜索资源"按钮位置。注意左侧竖排还有：野兽(冰霜古猿29)等入口。
2. 搜索面板打开后：校准资源名文案（肉/木/煤/铁）、等级输入框（`World.Search.ItemLevel` box [82.04,85.49,86.76,86.95] 百分比）、「搜索」「采集」按钮文案与位置。
3. 出征面板：校准「出征」「兵力均衡」(`World.Deploy.Equalize`)、RemoveHero 模板。
4. 跑通完整 `gather()` 并迭代。
5. OCR 服务偶发卡死（进程在但不响应，需要 `pkill -9` 重启；怀疑并发探测请求+截图锁死锁）——建议给服务加请求超时看护或用 scripts 重启。
6. 低级失误防御：直接 `python -c` 调试时忘 `source .wos.env` 会打到 8000 端口。建议把 `export WOS_OCR_PORT=8100` 写进 `~/.zshrc`，或统一用 `scripts/run-*.sh`。
7. `db/account.json` 还未配置（跑完整 bot 主流程前需填玩家 ID/名字）。

## 五、快速重启命令

```bash
# 模拟器
~/Library/Android/sdk/emulator/emulator -avd wos   # 或 scripts/start-emulator.sh
# OCR 服务（端口 8100）
cd wos && source .wos.env && OCR_CAPTURE_TOOL=adb nohup uv run core/ocr.py > /tmp/wos-ocr.log 2>&1 &
curl -s --noproxy '*' -X POST http://127.0.0.1:8100/ocr -H "Content-Type: application/json" -d '{"img_path":"/tmp/x.png"}'
# 单独测采集（绕过账号系统）
cd wos && source .wos.env && .venv/bin/python -c "from usecases.gather import gather; gather(level=4, min_level=1)"
```
