#!/bin/bash

echo "========================================"
echo "公共单词迁移工具"
echo "========================================"
echo

echo "正在启动迁移脚本..."
echo

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 运行Python脚本
python3 migrate_public_words.py

echo
echo "按回车键退出..."
read





