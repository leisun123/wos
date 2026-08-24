#!/usr/bin/env bash
# 终端2：bot 主程序（自动加载 .wos.env）
set -e
cd "$(dirname "$0")/.."
[ -f .wos.env ] && source .wos.env
exec uv run bot/main.py
