#!/bin/bash
# 清空 Hermes 所有历史数据，恢复到初始状态

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"

# 去除尾部斜杠
HERMES_HOME="${HERMES_HOME%/}"

# 安全校验：路径不能为空
if [[ -z "$HERMES_HOME" ]]; then
  echo "错误: HERMES_HOME 为空"
  exit 1
fi

# 安全校验：必须是绝对路径
if [[ "$HERMES_HOME" != /* ]]; then
  echo "错误: HERMES_HOME 必须是绝对路径 ($HERMES_HOME)"
  exit 1
fi

# 安全校验：路径不能是 / 或根级短路径
if [[ "$HERMES_HOME" == "/" || "${#HERMES_HOME}" -le 3 ]]; then
  echo "错误: HERMES_HOME 路径过短，拒绝执行 ($HERMES_HOME)"
  exit 1
fi

# 安全校验：必须是一个已存在的目录
if [[ ! -d "$HERMES_HOME" ]]; then
  echo "错误: HERMES_HOME 目录不存在 ($HERMES_HOME)"
  exit 1
fi

# 检查 Hermes 是否在运行（排除自身脚本进程）
hermes_pid=$(pgrep -f "hermes" | grep -vw "$$")
if [[ -n "$hermes_pid" ]]; then
  echo "警告: 检测到 Hermes 进程正在运行 (PID: $(echo $hermes_pid | tr '\n' ' '))!"
  echo "  运行中删除数据库可能导致数据损坏。"
  echo ""
  read -rp "是否继续？[y/N] " force
  if [[ "$force" != "y" && "$force" != "Y" ]]; then
    echo "已取消。请先停止 Hermes 后再执行。"
    exit 0
  fi
fi

echo "即将清理 Hermes 数据: $HERMES_HOME"
echo ""
echo "将删除以下内容："
echo "  - state.db (会话/消息数据库)"
echo "  - service.db (Web 聊天数据库)"
echo "  - sessions/ (会话 JSON 文件)"
echo "  - memories/ (AI 记忆文件)"
echo ""

# 确认提示（传入 -y 参数可跳过）
if [[ "$1" != "-y" ]]; then
  read -rp "确认删除？[y/N] " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "已取消。"
    exit 0
  fi
fi

# 1. 删除主会话数据库
deleted=false
for f in state.db state.db-wal state.db-shm; do
  if [[ -f "${HERMES_HOME:?}/$f" ]]; then
    rm -f "${HERMES_HOME:?}/$f"
    deleted=true
  fi
done
echo "[1/4] $([ "$deleted" = true ] && echo '已删除 state.db' || echo 'state.db 不存在，跳过')"

# 2. 删除 Web 聊天数据库
deleted=false
for f in service.db service.db-wal service.db-shm; do
  if [[ -f "${HERMES_HOME:?}/$f" ]]; then
    rm -f "${HERMES_HOME:?}/$f"
    deleted=true
  fi
done
echo "[2/4] $([ "$deleted" = true ] && echo '已删除 service.db' || echo 'service.db 不存在，跳过')"

# 3. 删除所有会话 JSON 文件
if [[ -d "${HERMES_HOME:?}/sessions" ]]; then
  rm -rf "${HERMES_HOME:?}/sessions/"
  echo "[3/4] 已删除 sessions/"
else
  echo "[3/4] sessions/ 不存在，跳过"
fi

# 4. 删除 AI 记忆文件
if [[ -d "${HERMES_HOME:?}/memories" ]]; then
  rm -rf "${HERMES_HOME:?}/memories/"
  echo "[4/4] 已删除 memories/"
else
  echo "[4/4] memories/ 不存在，跳过"
fi

echo ""
echo "清理完成，重启 Hermes 即可获得全新环境。"
