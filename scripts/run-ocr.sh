#!/usr/bin/env bash
# 终端1：OCR 服务（自动加载 .wos.env）
set -e
cd "$(dirname "$0")/.."
[ -f .wos.env ] && source .wos.env
exec uv run core/ocr.py
