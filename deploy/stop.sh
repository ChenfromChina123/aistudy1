#!/bin/bash
echo "正在停止 AI 研究项目..."

# 1. 尝试通过端口号停止
PORT_PID=$(lsof -t -i:5001)
if [ -n "$PORT_PID" ]; then
    echo "正在停止占用端口 5001 的进程 (PID: $PORT_PID)..."
    kill -9 $PORT_PID
    echo "已停止。"
fi

# 2. 尝试通过脚本名停止
SCRIPT_PID=$(ps -ef | grep 'python3 run.py' | grep -v grep | awk '{print $2}')
if [ -n "$SCRIPT_PID" ]; then
    echo "正在停止脚本进程 (PID: $SCRIPT_PID)..."
    kill -9 $SCRIPT_PID
    echo "已停止。"
fi

if [ -z "$PORT_PID" ] && [ -z "$SCRIPT_PID" ]; then
    echo "未发现正在运行的 5001 端口或相关脚本进程。"
fi
