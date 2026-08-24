# ❄️ WOS Bot（无尽冬日 / Whiteout Survival 自动化）

[![CI](https://github.com/leisun123/wos/actions/workflows/ci.yml/badge.svg)](https://github.com/leisun123/wos/actions/workflows/ci.yml)

Fork 自 [AminulIslamSifat/wos](https://github.com/AminulIslamSifat/wos)，MIT 协议。

Python + PaddleOCR（本地 FastAPI 服务）+ OpenCV 模板匹配 + ADB 实现《无尽冬日》日常自动化。
本 fork 的改造重点：**任意分辨率、中文版适配框架、采集稳定化（等级降级）、任务级容错与安全退出**。

> ⚠️ 免责声明：使用自动化工具可能违反游戏 ToS，封号风险自负，仅供学习研究。

---

## 一、运行前需要准备什么

### 1. 硬件 / 环境

| 项目 | 要求 |
|---|---|
| 电脑 | macOS / Linux / Windows（高速截图模式仅 Linux，其余平台自动用 ADB 截图，慢但可用） |
| Python | **3.12+**（必须，3.10/3.11 会语法报错） |
| 包管理 | [uv](https://docs.astral.sh/uv/)（推荐）或 pip |
| ADB | Android Platform Tools，`adb` 在 PATH 中 |
| 设备 | Android 真机（开启 USB 调试）或模拟器；**分辨率不再受限**（启动时自动 `wm size` 检测） |

### 2. 安装依赖

```bash
git clone https://github.com/leisun123/wos.git
cd wos
uv venv --python 3.12
uv sync            # 含 dev 组：uv sync --dev
```

### 3. 配置账号

```bash
cp db/account.json.example db/account.json
# 编辑 db/account.json：email / priority / player id+name
```

### 4. 环境变量（按需）

| 变量 | 默认 | 说明 |
|---|---|---|
| `WOS_ADB_SERIAL` | 自动选第一台 | 指定 adb 设备序列号（多设备/无线 adb `ip:port` 时设置） |
| `WOS_LANG` | `en` | 游戏客户端语言 `en` / `zh`（中文版设 `zh`） |
| `WOS_OCR_LANG` | 跟随 `WOS_LANG` | PaddleOCR 模型语言（`ch`/`en`） |
| `WOS_PACKAGE` | 国际服包名 | **国服必须改**：用 `adb shell pm list packages` 查实际包名 |
| `WOS_RESOLUTION` | 自动检测 | 强制分辨率，如 `1080x2460`（一般不用设） |
| `WOS_TASK_TIMEOUT` | `1800` | 单任务超时秒数 |
| `WOS_CAPTURE_TOOL` | `adb` | OCR 服务截图方式 `adb` / `scrcpy`（Linux） |
| `OCR_RAM_CAP_GB` | `3.0` | OCR 服务内存上限（仅 Linux） |

### 5. 运行（两个终端）

```bash
# 终端 1：OCR 服务（PaddleOCR + 模板匹配）
uv run core/ocr.py

# 终端 2：主程序（交互式任务菜单）
uv run Main/main.py
```

菜单里回车跑全部默认任务，或输入 `18`（World Gather）只跑采集。

### 6. 测试（无需设备）

```bash
uv run pytest tests/               # 全部
uv run pytest -m "not slow" -q     # 只跑轻量测试（CI 每次跑的也是这个）
```

**云上测试（GitHub Actions，public 仓库免费）**：

- `CI` workflow：push / PR / 手动触发，跑语法检查 + 离线单测（约 1-2 分钟）
- `Nightly` workflow：每天北京时间 03:30（或手动触发），额外跑**截图回放测试**——
  把真机截图放进 `tests/fixtures/screenshots/`，配好 `tests/fixtures/expectations.json`
  （格式见 `tests/test_screenshot_replay.py` 顶部注释），即可在云端验证
  「这张图 OCR 能否认出『城市』/『采集』」，改 i18n 映射不用插手机。
  没放截图时该测试零成本跳过。

---

## 二、中文版（国服）适配状态

已搭好框架，但需要真机采样后才能跑稳：

1. `WOS_LANG=zh` 启用（OCR 自动切中文模型，界面词自动走中文映射）。
2. `references/TextArea.zh.json`：中文文本覆盖层——**text 值需按真机截图核对**，box 坐标沿用英文版百分比。
3. `core/i18n.py` 的 `LITERAL_ZH`：字面量映射（采集/搜索/出征/肉木煤铁…），同样需真机核对。
4. 国服包名：设置 `WOS_PACKAGE`（`adb shell pm list packages | grep -i wos` 等确认）。
5. 含英文文字的模板图（`references/icon/`）如匹配不到，需在中文版截图替换。

## 三、本 fork 主要改造

- **消除 import 副作用**：无设备也能 import/测试；设备检测、配置加载、游戏启动全部延迟到运行时。
- **任意分辨率**：启动时 `adb shell wm size` 实测分辨率，百分比坐标按真机换算；修复 int/float 百分比误判 bug 与 2460/2456 双基准、魔法偏移。
- **采集稳定化**：`gather(level=8, min_level=5)` 支持无矿降级搜索；行军队列 OCR 读取失败时保守中止（不再猜数字继续点）。
- **任务级容错**：单任务异常/超时只跳过该任务；主循环崩溃自动重启游戏并退避重试；游戏进程检测。
- **安全退出**：`recalibrate()` 遇未知页面截图存 `logs/`、限制盲点点击次数后安全退出，不乱点。
- **多设备**：`WOS_ADB_SERIAL` 指定序列号，所有 adb 命令统一带 `-s`。
- **bug 修复**：`train_marksman` NameError、VIP `title.lower` 永真比较、像素坐标残留等。

## 四、项目结构

```
Main/            入口 + 任务菜单（任务级容错/超时）
core/ocr.py      FastAPI OCR/模板服务（语言可配 WOS_OCR_LANG）
core/core.py     视觉客户端（OCR/模板 HTTP 调用 + 点击）
core/config.py   集中配置（环境变量）
core/i18n.py     中英文本映射
core/recalibrate.py 页面恢复（截图存证 + 盲点上限）
cmd_program/     ADB 点击/滑动/截图/游戏启动
usecases/        gather / alliance / mail / training 等 17 个任务
references/      TextArea JSON（百分比 ROI）+ icon 模板 + TextArea.zh.json
tests/           离线单元测试（无需设备）
```

## 五、License

MIT（见 [LICENSE](LICENSE)）。上游：AminulIslamSifat/wos。
