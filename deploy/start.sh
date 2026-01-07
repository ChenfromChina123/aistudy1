#!/bin/bash
# 进入项目目录 (根据服务器实际路径修改)
cd /www/project/aistudy1/py

echo "正在检查并清理旧进程..."

# 1. 通过端口号 5001 查找并杀死进程
PORT_PID=$(lsof -t -i:5001)
if [ -n "$PORT_PID" ]; then
    echo "发现端口 5001 已被占用 (PID: $PORT_PID)，正在停止..."
    kill -9 $PORT_PID
    sleep 1
fi

# 2. 通过脚本名称进一步确保清理干净 (防止端口释放延迟)
SCRIPT_PID=$(ps -ef | grep 'python3 run.py' | grep -v grep | awk '{print $2}')
if [ -n "$SCRIPT_PID" ]; then
    echo "发现正在运行的脚本进程 (PID: $SCRIPT_PID)，正在停止..."
    kill -9 $SCRIPT_PID
    sleep 1
fi

# 使用 nohup 后台运行应用，并将日志重定向到 server.log
echo "正在启动 AI 研究项目..."
nohup python3 run.py > ../server.log 2>&1 &

echo "项目已在后台启动，PID: $!"
echo "提示：可以使用 'tail -f ../server.log' 查看实时运行日志"
