#!/bin/bash
# 启动 AIBank Hermes Web Chat

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HERMES_VENV="$PROJECT_ROOT/hermes/venv"

echo -e "${GREEN}=== AIBank Hermes Web Chat ===${NC}"
echo ""

# 检查 hermes venv
if [ ! -d "$HERMES_VENV" ]; then
    echo -e "${RED}错误: hermes venv 不存在${NC}"
    echo "请先运行 ./install.sh 安装 hermes"
    exit 1
fi

# 检查 frontend 是否安装依赖
if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
    echo -e "${YELLOW}安装 frontend 依赖...${NC}"
    cd "$SCRIPT_DIR/frontend"
    npm install
fi

# 启动后端
echo -e "${YELLOW}[1/2] 启动后端 (端口 18080)...${NC}"
cd "$SCRIPT_DIR/backend"
source "$HERMES_VENV/bin/activate"

# 检查并安装 backend 依赖
pip install -q fastapi uvicorn websockets python-dotenv 2>/dev/null || true

# 启动 uvicorn
uvicorn main:app --host 127.0.0.1 --port 18080 &
BACKEND_PID=$!
echo -e "${GREEN}✓${NC} 后端已启动 (PID: $BACKEND_PID)"

# 等待后端启动
sleep 2

# 启动前端
echo -e "${YELLOW}[2/2] 启动前端 (端口 5173)...${NC}"
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}✓${NC} 前端已启动 (PID: $FRONTEND_PID)"

echo ""
echo -e "${GREEN}=== 服务已启动 ===${NC}"
echo ""
echo "  后端 API:  http://127.0.0.1:18080"
echo "  前端界面:  http://localhost:5173"
echo ""
echo "按 Ctrl+C 停止服务"

# 等待进程
trap "echo ''; echo '停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait $BACKEND_PID $FRONTEND_PID