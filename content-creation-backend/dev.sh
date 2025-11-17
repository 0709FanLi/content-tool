#!/bin/bash

# 内容创作后端开发环境管理脚本
# 使用方法:
#   ./dev.sh start    # 启动服务
#   ./dev.sh stop     # 停止服务
#   ./dev.sh restart  # 重启服务
#   ./dev.sh status   # 查看服务状态
#   ./dev.sh logs     # 查看服务日志（如果有）
#   ./dev.sh clean    # 清理临时文件

# 设置脚本遇到错误时退出
set -e

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 服务名称
SERVICE_NAME="内容创作后端"
PID_FILE=".server_pid"
LOG_FILE="server.log"

# 显示帮助信息
show_help() {
    echo -e "${BLUE}${SERVICE_NAME} 开发环境管理脚本${NC}"
    echo ""
    echo "使用方法:"
    echo "  $0 start    启动服务"
    echo "  $0 stop     停止服务"
    echo "  $0 restart  重启服务"
    echo "  $0 status   查看服务状态"
    echo "  $0 logs     查看服务日志"
    echo "  $0 clean    清理临时文件"
    echo "  $0 help     显示此帮助信息"
    echo ""
}

# 检查Python环境
check_python() {
    if ! command -v python &> /dev/null; then
        echo -e "${RED}❌ Python 未找到，请确保已安装 Python 3.8+${NC}"
        exit 1
    fi

    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}🐍 Python 版本: $PYTHON_VERSION${NC}"
}

# 检查虚拟环境
setup_venv() {
    if [ -d "venv" ]; then
        echo -e "${YELLOW}📦 激活虚拟环境 (venv)...${NC}"
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        echo -e "${YELLOW}📦 激活虚拟环境 (.venv)...${NC}"
        source .venv/bin/activate
    else
        echo -e "${YELLOW}⚠️  未找到虚拟环境，将使用系统Python${NC}"
    fi
}

# 检查服务状态
check_status() {
    local status="stopped"
    local pid=""

    # 检查PID文件
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            status="running"
        else
            rm -f "$PID_FILE"
        fi
    fi

    # 检查端口
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        if [ "$status" != "running" ]; then
            status="running (unknown pid)"
        fi
    fi

    echo -e "${BLUE}📊 服务状态: ${status}${NC}"
    if [ -n "$pid" ] && [ "$status" = "running" ]; then
        echo -e "${BLUE}   PID: $pid${NC}"
    fi
    echo -e "${BLUE}   端口: 8000${NC}"
    echo -e "${BLUE}   URL: http://localhost:8000${NC}"
}

# 启动服务
start_service() {
    echo -e "${GREEN}🚀 启动${SERVICE_NAME}...${NC}"

    check_python
    setup_venv

    # 检查是否已经在运行
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  服务似乎已经在运行${NC}"
        check_status
        exit 1
    fi

    # 设置环境变量
    export PYTHONPATH="$SCRIPT_DIR/src:$PYTHONPATH"
    export DEBUG="${DEBUG:-true}"
    export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./content_creation.db}"
    export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
    # JWT_SECRET_KEY 在生产环境必须设置，开发环境会使用默认值并给出警告
    export JWT_SECRET_KEY="${JWT_SECRET_KEY:-}"
    export ALLOWED_HOSTS_STR="${ALLOWED_HOSTS_STR:-localhost,127.0.0.1}"

    # 启动服务
    echo -e "${YELLOW}⏳ 启动中...${NC}"

    # 使用导入字符串以支持 reload 模式
    python -c "
import uvicorn
import os

print('🎯 启动${SERVICE_NAME}')
print(f'📊 调试模式: {os.getenv(\"DEBUG\", \"false\")}')
print(f'🗄️  数据库: {os.getenv(\"DATABASE_URL\", \"未设置\")[:50]}...')

uvicorn.run(
    'src.main:app',
    host='0.0.0.0',
    port=8000,
    log_level='info',
    reload=os.getenv('DEBUG', 'false').lower() == 'true'
)
" > "$LOG_FILE" 2>&1 &

    SERVER_PID=$!
    echo $SERVER_PID > "$PID_FILE"

    # 等待服务启动
    sleep 5

    if kill -0 $SERVER_PID 2>/dev/null; then
        echo -e "${GREEN}✅ 服务启动成功!${NC}"
        echo -e "${GREEN}📋 服务信息:${NC}"
        echo -e "   PID: $SERVER_PID"
        echo -e "   URL: http://localhost:8000"
        echo -e "   Docs: http://localhost:8000/docs"
        echo -e "   Health: http://localhost:8000/health"
        echo -e "   日志: $LOG_FILE"
    else
        echo -e "${RED}❌ 服务启动失败${NC}"
        if [ -f "$LOG_FILE" ]; then
            echo -e "${YELLOW}📄 查看日志: tail -f $LOG_FILE${NC}"
        fi
        exit 1
    fi
}

# 停止服务
stop_service() {
    echo -e "${YELLOW}🛑 停止${SERVICE_NAME}...${NC}"

    local stopped=false

    # 方法1: 通过PID文件停止
    if [ -f "$PID_FILE" ]; then
        local SERVER_PID=$(cat "$PID_FILE")
        if kill -0 $SERVER_PID 2>/dev/null; then
            echo -e "${YELLOW}📋 停止进程 (PID: $SERVER_PID)...${NC}"
            kill $SERVER_PID 2>/dev/null || true
            sleep 3
            if kill -0 $SERVER_PID 2>/dev/null; then
                kill -9 $SERVER_PID 2>/dev/null || true
                echo -e "${GREEN}✅ 强制停止完成${NC}"
            else
                echo -e "${GREEN}✅ 正常停止完成${NC}"
            fi
            stopped=true
        fi
        rm -f "$PID_FILE"
    fi

    # 方法2: 通过端口停止
    local PORT_PIDS=$(lsof -ti:8000 2>/dev/null || true)
    if [ -n "$PORT_PIDS" ]; then
        echo -e "${YELLOW}🔍 停止端口进程: $PORT_PIDS${NC}"
        kill $PORT_PIDS 2>/dev/null || true
        sleep 2
        local REMAINING_PORT_PIDS=$(lsof -ti:8000 2>/dev/null || true)
        if [ -n "$REMAINING_PORT_PIDS" ]; then
            kill -9 $REMAINING_PORT_PIDS 2>/dev/null || true
        fi
        stopped=true
    fi

    if [ "$stopped" = true ]; then
        echo -e "${GREEN}✅ 服务已停止${NC}"
    else
        echo -e "${YELLOW}ℹ️  未找到正在运行的服务${NC}"
    fi
}

# 查看日志
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo -e "${BLUE}📄 服务日志 (按 Ctrl+C 退出):${NC}"
        tail -f "$LOG_FILE"
    else
        echo -e "${YELLOW}⚠️  日志文件不存在: $LOG_FILE${NC}"
    fi
}

# 清理临时文件
clean_files() {
    echo -e "${YELLOW}🧹 清理临时文件...${NC}"

    # 删除PID文件
    if [ -f "$PID_FILE" ]; then
        rm -f "$PID_FILE"
        echo -e "${GREEN}✅ 删除 PID 文件${NC}"
    fi

    # 删除日志文件
    if [ -f "$LOG_FILE" ]; then
        rm -f "$LOG_FILE"
        echo -e "${GREEN}✅ 删除日志文件${NC}"
    fi

    # 清理Python缓存
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true

    echo -e "${GREEN}✅ 清理完成${NC}"
}

# 主逻辑
case "${1:-help}" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        stop_service
        sleep 2
        start_service
        ;;
    status)
        check_status
        ;;
    logs)
        show_logs
        ;;
    clean)
        clean_files
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}❌ 未知命令: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
