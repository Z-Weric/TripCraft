#!/bin/bash
# TripCraft 本地启动脚本
# 用法: ./start.sh

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=== TripCraft 启动 ==="

# 清理旧进程（防止端口冲突）
echo "[0/2] 清理旧进程..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null
sleep 1

# 启动后端
echo "[1/2] 启动后端 (port 8000)..."
cd "$PROJECT_DIR"
source .venv/bin/activate
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
echo "  后端 PID: $BACKEND_PID"

# 等待后端就绪
sleep 2

# 启动前端
echo "[2/2] 启动前端 (port 5173)..."
cd "$PROJECT_DIR/frontend"
npm run dev -- --port 5173 &
FRONTEND_PID=$!
echo "  前端 PID: $FRONTEND_PID"

echo ""
echo "=== 启动完成 ==="
echo "  后端 API:  http://localhost:8000/docs"
echo "  前端页面:  http://localhost:5173"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 捕获退出信号，清理子进程
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait