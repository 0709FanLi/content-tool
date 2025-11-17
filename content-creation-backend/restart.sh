#!/bin/bash

# 内容创作后端服务重启脚本
# 使用方法: ./restart.sh

echo "🚀 重启内容创作后端服务..."

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

# 检查Python是否可用
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python 未找到，请确保已安装 Python 3.8+${NC}"
    exit 1
fi

# 检查虚拟环境（如果存在）
if [ -d "venv" ]; then
    echo -e "${YELLOW}📦 激活虚拟环境...${NC}"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${YELLOW}📦 激活虚拟环境...${NC}"
    source .venv/bin/activate
fi

# 停止正在运行的服务
echo -e "${YELLOW}🛑 停止现有服务...${NC}"

# 查找并停止 uvicorn 进程
UVICORN_PIDS=$(pgrep -f "uvicorn.*src.main:app" || true)
if [ -n "$UVICORN_PIDS" ]; then
    echo "找到 uvicorn 进程: $UVICORN_PIDS"
    kill $UVICORN_PIDS 2>/dev/null || true
    sleep 2

    # 强制杀死未正常停止的进程
    kill -9 $UVICORN_PIDS 2>/dev/null || true
    echo -e "${GREEN}✅ 已停止现有服务${NC}"
else
    echo -e "${YELLOW}ℹ️  未找到正在运行的服务${NC}"
fi

# 等待端口释放
echo -e "${YELLOW}⏳ 等待端口释放...${NC}"
sleep 3

# 检查端口是否被占用
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}❌ 端口 8000 仍被占用${NC}"
    echo -e "${YELLOW}请手动检查并停止占用端口的进程${NC}"
    exit 1
fi

# 设置环境变量
export PYTHONPATH="$SCRIPT_DIR/src:$PYTHONPATH"

# 默认环境变量（可以被 .env 文件覆盖）
export DEBUG="${DEBUG:-true}"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./test.db}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
# JWT_SECRET_KEY 在生产环境必须设置，开发环境会使用默认值并给出警告
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-}"
export ALLOWED_HOSTS_STR="${ALLOWED_HOSTS_STR:-localhost,127.0.0.1}"

# 启动服务
echo -e "${GREEN}🚀 启动服务...${NC}"
echo -e "${YELLOW}服务地址: http://localhost:8000${NC}"
echo -e "${YELLOW}API文档: http://localhost:8000/docs${NC}"
echo -e "${YELLOW}健康检查: http://localhost:8000/health${NC}"

# 在后台启动服务
python -c "
from src.main import app
import uvicorn
import os

print('🎯 启动内容创作后端服务')
print(f'📊 调试模式: {os.getenv(\"DEBUG\", \"false\")}')
print(f'🗄️  数据库: {os.getenv(\"DATABASE_URL\", \"未设置\")[:50]}...')

uvicorn.run(
    app,
    host='0.0.0.0',
    port=8000,
    log_level='info',
    reload=os.getenv('DEBUG', 'false').lower() == 'true'
)
" &

# 获取后台进程ID
SERVER_PID=$!

# 等待服务启动
echo -e "${YELLOW}⏳ 等待服务启动...${NC}"
sleep 5

# 检查服务是否成功启动
if kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${GREEN}✅ 服务启动成功!${NC}"
    echo -e "${GREEN}📋 服务信息:${NC}"
    echo -e "   PID: $SERVER_PID"
    echo -e "   URL: http://localhost:8000"
    echo -e "   Docs: http://localhost:8000/docs"
    echo -e "   Health: http://localhost:8000/health"

    # 保存PID到文件（可选）
    echo $SERVER_PID > .server_pid
    echo -e "${YELLOW}💡 PID 已保存到 .server_pid 文件${NC}"
else
    echo -e "${RED}❌ 服务启动失败${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 重启完成！${NC}"
