#!/bin/bash

# 一键安装脚本 for aibank-hermes-agent
# 用法: ./install.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_DIR="${SCRIPT_DIR}/hermes"

echo ""
echo -e "${CYAN}=== Hermes Agent 一键安装脚本 ===${NC}"
echo ""

# 步骤 1: 初始化并更新子模块（包括嵌套子模块）
echo -e "${CYAN}[1/3]${NC} 初始化并更新子模块..."
cd "$SCRIPT_DIR"
git submodule update --init --recursive
echo -e "${GREEN}✓${NC} 子模块已就绪"

# 步骤 2: 复制自定义文件（增量添加，不覆盖）
echo -e "${CYAN}[2/3]${NC} 复制自定义文件（增量模式，已存在的跳过）..."

# 复制 tools 到 hermes/tools（跳过已存在的）
if [ -d "${SCRIPT_DIR}/tools" ]; then
    for item in "${SCRIPT_DIR}/tools"/*; do
        [ -e "$item" ] || continue
        item_name=$(basename "$item")
        dest="${HERMES_DIR}/tools/${item_name}"
        if [ -e "$dest" ]; then
            echo -e "  ${YELLOW}跳过${NC} tools/${item_name} (已存在)"
        else
            cp -r "$item" "$dest"
            echo -e "  ${GREEN}复制${NC} tools/${item_name}"
        fi
    done
fi

# 复制 plugins 到 ~/.hermes/plugins（hermes 标准插件目录）
mkdir -p ~/.hermes/plugins
if [ -d "${SCRIPT_DIR}/plugins" ]; then
    for item in "${SCRIPT_DIR}/plugins"/*; do
        [ -e "$item" ] || continue
        item_name=$(basename "$item")
        dest="${HOME}/.hermes/plugins/${item_name}"
        if [ -e "$dest" ]; then
            echo -e "  ${YELLOW}跳过${NC} plugins/${item_name} (已存在)"
        else
            cp -r "$item" "$dest"
            echo -e "  ${GREEN}复制${NC} plugins/${item_name} -> ~/.hermes/plugins/"
        fi
    done
fi

# 复制 skills 到 ~/.hermes/skills（跳过已存在的）
mkdir -p ~/.hermes/skills
if [ -d "${SCRIPT_DIR}/skills" ]; then
    for item in "${SCRIPT_DIR}/skills"/*; do
        [ -e "$item" ] || continue
        item_name=$(basename "$item")
        dest="${HOME}/.hermes/skills/${item_name}"
        if [ -e "$dest" ]; then
            echo -e "  ${YELLOW}跳过${NC} skills/${item_name} (已存在)"
        else
            cp -r "$item" "$dest"
            echo -e "  ${GREEN}复制${NC} skills/${item_name} -> ~/.hermes/skills/"
        fi
    done
fi

# 复制 data 到 ~/.hermes/data（跳过已存在的）
mkdir -p ~/.hermes/data
if [ -d "${SCRIPT_DIR}/data" ]; then
    for item in "${SCRIPT_DIR}/data"/*; do
        [ -e "$item" ] || continue
        item_name=$(basename "$item")
        dest="${HOME}/.hermes/data/${item_name}"
        if [ -e "$dest" ]; then
            echo -e "  ${YELLOW}跳过${NC} data/${item_name} (已存在)"
        else
            cp -r "$item" "$dest"
            echo -e "  ${GREEN}复制${NC} data/${item_name} -> ~/.hermes/data/"
        fi
    done
fi

echo -e "${GREEN}✓${NC} 自定义文件已就绪"

# 步骤 3: 调用 hermes 的 setup-hermes.sh
echo -e "${CYAN}[3/3]${NC} 运行 hermes 安装脚本..."
cd "$HERMES_DIR"

# 检查 setup-hermes.sh 是否存在
if [ ! -f "setup-hermes.sh" ]; then
    echo -e "${RED}✗${NC} setup-hermes.sh 不存在"
    exit 1
fi

# 如果 hermes 目录下已有 venv，提示用户
if [ -d "${HERMES_DIR}/venv" ]; then
    echo -e "${YELLOW}注意:${NC} hermes 目录下已存在 venv"
    echo "  setup-hermes.sh 会删除并重建 venv（这是 hermes 的默认行为）"
    read -p "  是否继续？[Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ -n $REPLY ]]; then
        echo -e "${YELLOW}跳过${NC} hermes 安装步骤"
        echo ""
        echo -e "${GREEN}=== 部分安装完成 ===${NC}"
        echo "  - 自定义文件已复制"
        echo "  - hermes venv 保留原有状态"
        exit 0
    fi
fi

# 执行 setup-hermes.sh
chmod +x setup-hermes.sh
./setup-hermes.sh

echo ""
echo -e "${GREEN}=== 安装完成! ===${NC}"