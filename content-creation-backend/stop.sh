#!/bin/bash

# 内容创作后端服务停止脚本
# 使用方法: ./stop.sh

echo "🛑 停止内容创作后端服务..."

# 设置脚本遇到错误时退出
set -e

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 停止正在运行的服务
echo -e "${YELLOW}🔍 查找正在运行的服务...${NC}"

# 方法1: 通过PID文件停止
if [ -f ".server_pid" ]; then
    SERVER_PID=$(cat .server_pid)
    if kill -0 $SERVER_PID 2>/dev/null; then
        echo -e "${YELLOW}📋 从PID文件找到进程: $SERVER_PID${NC}"
        kill $SERVER_PID 2>/dev/null || true
        sleep 2
        if kill -0 $SERVER_PID 2>/dev/null; then
            kill -9 $SERVER_PID 2>/dev/null || true
            echo -e "${GREEN}✅ 强制停止服务 (PID: $SERVER_PID)${NC}"
        else
            echo -e "${GREEN}✅ 正常停止服务 (PID: $SERVER_PID)${NC}"
        fi
    else
        echo -e "${YELLOW}ℹ️  PID文件中的进程不存在${NC}"
    fi
    rm -f .server_pid
fi

# 方法2: 通过进程名查找并停止
UVICORN_PIDS=$(pgrep -f "uvicorn.*src.main:app" || true)
if [ -n "$UVICORN_PIDS" ]; then
    echo -e "${YELLOW}🔍 找到 uvicorn 进程: $UVICORN_PIDS${NC}"
    kill $UVICORN_PIDS 2>/dev/null || true
    sleep 2

    # 检查是否还有进程在运行
    REMAINING_PIDS=$(pgrep -f "uvicorn.*src.main:app" || true)
    if [ -n "$REMAINING_PIDS" ]; then
        echo -e "${YELLOW}⚠️  强制停止剩余进程: $REMAINING_PIDS${NC}"
        kill -9 $REMAINING_PIDS 2>/dev/null || true
        echo -e "${GREEN}✅ 强制停止完成${NC}"
    else
        echo -e "${GREEN}✅ 正常停止完成${NC}"
    fi
fi

# 方法3: 通过端口查找并停止
PORT_PIDS=$(lsof -ti:8000 2>/dev/null || true)
if [ -n "$PORT_PIDS" ]; then
    echo -e "${YELLOW}🔍 找到占用端口8000的进程: $PORT_PIDS${NC}"
    kill $PORT_PIDS 2>/dev/null || true
    sleep 2

    REMAINING_PORT_PIDS=$(lsof -ti:8000 2>/dev/null || true)
    if [ -n "$REMAINING_PORT_PIDS" ]; then
        echo -e "${YELLOW}⚠️  强制停止端口进程: $REMAINING_PORT_PIDS${NC}"
        kill -9 $REMAINING_PORT_PIDS 2>/dev/null || true
    fi
fi

# 检查是否还有服务在运行
sleep 1
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}❌ 端口 8000 仍被占用${NC}"
    echo -e "${YELLOW}请手动检查并停止占用端口的进程:${NC}"
    lsof -i :8000
else
    echo -e "${GREEN}✅ 服务已完全停止${NC}"
fi

echo -e "${GREEN}🎉 停止操作完成！${NC}"
