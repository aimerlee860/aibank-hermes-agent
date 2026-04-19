"""
AIBank Hermes Web Chat Backend.

FastAPI + WebSocket for real-time chat with Hermes Agent.
"""

import logging
import json
import asyncio
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sys

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
HERMES_PATH = PROJECT_ROOT / "hermes"
if str(HERMES_PATH) not in sys.path:
    sys.path.insert(0, str(HERMES_PATH))

from agent_wrapper import WebSocketAgentWrapper
from service_db import ServiceDB

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 应用
app = FastAPI(
    title="AIBank Hermes Web Chat",
    description="Web interface for Hermes Agent with real-time streaming",
    version="0.1.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:18080",
        "http://127.0.0.1:18080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket 连接管理
active_sessions: Dict[str, WebSocketAgentWrapper] = {}


@app.on_event("startup")
async def startup_event():
    """启动时检查 Hermes 配置。"""
    logger.info("Starting AIBank Hermes Web Chat Backend...")
    try:
        from hermes_constants import get_hermes_home
        hermes_home = get_hermes_home()
        logger.info(f"Hermes home: {hermes_home}")

        config_path = hermes_home / "config.yaml"
        env_path = hermes_home / ".env"

        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
        if not env_path.exists():
            logger.warning(f"Env file not found: {env_path}")

        # 初始化 ServiceDB
        service_db = ServiceDB()
        logger.info(f"ServiceDB initialized at: {service_db.db_path}")

    except Exception as e:
        logger.error(f"Startup check failed: {e}")


def _build_history_with_timeline(session_id: str, service_db: ServiceDB) -> List[Dict]:
    """
    从 ServiceDB 构建 history 消息列表（含 timeline）。

    批量查询日志和工具调用，按 turn_seq 关联到对应 assistant 消息。
    """
    messages = service_db.get_chat_messages(session_id)
    if not messages:
        return []

    # 批量查询所有日志和工具调用（2 次查询代替 2N 次）
    all_logs = service_db.get_logs(session_id)
    all_tool_calls = service_db.get_tool_calls(session_id)

    # 按 turn_seq 分组
    logs_by_turn: Dict[int, list] = {}
    for log in all_logs:
        turn = log.get("turn_seq", 0)
        logs_by_turn.setdefault(turn, []).append(log)

    tools_by_turn: Dict[int, list] = {}
    for tc in all_tool_calls:
        turn = tc.get("turn_seq", 0)
        tools_by_turn.setdefault(turn, []).append(tc)

    result = []
    for msg in messages:
        entry = {
            "role": msg["role"],
            "content": msg["content"],
            "timestamp": msg["timestamp"],
        }

        if msg["role"] == "assistant":
            turn = msg["turn_seq"]
            timeline = []

            for log in logs_by_turn.get(turn, []):
                if log.get("log_type") == "status":
                    continue
                timeline.append({
                    "type": "log",
                    "message": log.get("content", ""),
                    "source": log.get("source", "agent"),
                    "_ts": log.get("timestamp", 0),
                })

            for tc in tools_by_turn.get(turn, []):
                timeline.append({
                    "type": "tool",
                    "id": tc.get("tool_call_id", ""),
                    "name": tc.get("tool_name", ""),
                    "args": tc.get("args", {}),
                    "result": tc.get("result"),
                    "_ts": tc.get("started_at", 0),
                })

            timeline.sort(key=lambda x: x["_ts"])
            for t in timeline:
                t.pop("_ts", None)

            if timeline:
                entry["timeline"] = timeline

        result.append(entry)

    return result


@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket 聊天端点。

    接收消息并实时返回 Agent 响应（流式）。
    """
    await websocket.accept()
    logger.info(f"WebSocket connected: session={session_id}")

    # 创建会话记录（service.db）
    service_db = ServiceDB()
    service_db.create_session(session_id)

    # 发送连接确认
    try:
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "Connected to Hermes Agent"
        })
    except Exception as e:
        logger.warning(f"Failed to send connected message, client may have disconnected: {e}")
        return

    # 实时发送队列（用于从同步回调中发送消息）
    event_queue: asyncio.Queue = asyncio.Queue()

    def realtime_sender(event: dict):
        """实时发送事件到队列（同步回调可用）。"""
        event_queue.put_nowait(event)

    # 创建 Agent Wrapper（使用实时发送器）
    wrapper = WebSocketAgentWrapper(ws_sender=realtime_sender, session_id=session_id)
    active_sessions[session_id] = wrapper

    # 从 ServiceDB 加载历史消息
    try:
        formatted_messages = _build_history_with_timeline(session_id, service_db)
        if formatted_messages:
            await websocket.send_json({
                "type": "history",
                "messages": formatted_messages,
                "session_id": session_id
            })
            logger.info(f"Loaded {len(formatted_messages)} history messages for session={session_id}")
    except Exception as e:
        logger.warning(f"Failed to load history: {e}")

    # 实时发送队列中的消息（后台任务）
    async def send_events_from_queue():
        """从队列中取事件并发送。"""
        while True:
            try:
                event = await event_queue.get()
                await websocket.send_json(event)
                if event.get("type") == "complete":
                    logger.info(f"Sent complete event, stopping sender")
                    break  # 完成事件后停止发送
            except Exception as e:
                logger.error(f"Failed to send event: {e}")
                break

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()

            if data.get("type") == "message":
                content = data.get("content", "")
                logger.info(f"Received message: session={session_id}, content={content[:50]}...")

                # 如果是首次提问，设置会话标题
                session_info = service_db.get_session(session_id)
                if session_info and session_info.get("message_count", 0) == 0 and not session_info.get("title"):
                    # 截取标题（最多 50 字符）
                    title = content[:50] if len(content) > 50 else content
                    # 清理换行符等
                    title = title.replace("\n", " ").strip()
                    service_db.update_session(session_id, title=title)
                    logger.info(f"Set session title: {title}")

                # 清空队列
                while not event_queue.empty():
                    event_queue.get_nowait()

                # 发送开始事件
                await websocket.send_json({
                    "type": "start",
                    "session_id": session_id
                })

                # 同时运行：发送事件 + 处理消息
                send_task = asyncio.create_task(send_events_from_queue())
                chat_task = asyncio.create_task(wrapper.chat(content))

                # 等待两个任务完成
                await asyncio.gather(chat_task, send_task)

                # 更新消息数量（用户+助手 = 2）
                service_db.increment_message_count(session_id)
                service_db.increment_message_count(session_id)

            elif data.get("type") == "clear":
                wrapper.clear_history()
                # 同时清空 ServiceDB 数据
                service_db.clear_session(session_id)
                await websocket.send_json({
                    "type": "cleared",
                    "session_id": session_id
                })

            elif data.get("type") == "history":
                history = wrapper.get_history()
                await websocket.send_json({
                    "type": "history",
                    "messages": history,
                    "session_id": session_id
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session={session_id}")
        if session_id in active_sessions:
            del active_sessions[session_id]

    except Exception as e:
        logger.error(f"WebSocket error: session={session_id}, error={e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
                "session_id": session_id
            })
        except:
            pass


# REST API 端点

@app.get("/api/sessions")
async def list_sessions(limit: int = 50):
    """
    获取会话列表。

    从 ServiceDB 的 web_sessions 表读取。
    """
    try:
        service_db = ServiceDB()
        sessions = service_db.list_sessions(limit=limit)
        return {"sessions": sessions}

    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """
    获取单个会话详情（从 ServiceDB）。
    """
    try:
        service_db = ServiceDB()
        session = service_db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    删除会话及其所有数据。
    """
    try:
        service_db = ServiceDB()
        service_db.delete_session(session_id)
        return {"status": "deleted", "session_id": session_id}

    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, limit: int = 100):
    """
    获取会话消息历史（从 ServiceDB）。
    """
    try:
        service_db = ServiceDB()
        messages = _build_history_with_timeline(session_id, service_db)
        return {"messages": messages}

    except Exception as e:
        logger.error(f"Failed to get messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/logs")
async def get_session_logs(session_id: str, limit: int = 200):
    """
    获取会话执行日志（仅 ServiceDB）。
    """
    try:
        service_db = ServiceDB()
        logs = service_db.get_logs(session_id, limit=limit)
        tool_calls = service_db.get_tool_calls(session_id)
        return {"logs": logs, "tool_calls": tool_calls}

    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}/logs")
async def clear_session_logs(session_id: str):
    """
    清空会话执行日志。
    """
    try:
        service_db = ServiceDB()
        service_db.clear_session(session_id)
        return {"status": "cleared", "session_id": session_id}

    except Exception as e:
        logger.error(f"Failed to clear logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config")
async def get_config():
    """
    获取 Hermes 配置。
    """
    try:
        from hermes_constants import get_hermes_home
        from hermes_cli.config import load_config

        hermes_home = get_hermes_home()
        config_path = hermes_home / "config.yaml"

        if not config_path.exists():
            return {"config": {}, "path": str(config_path), "exists": False}

        config = load_config()
        # 隐藏敏感信息
        safe_config = config.copy()
        for key in ["api_key", "token", "secret"]:
            if key in safe_config:
                safe_config[key] = "***"

        return {"config": safe_config, "path": str(config_path), "exists": True}

    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """
    健康检查端点。
    """
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "version": "0.1.0"
    }


@app.get("/")
async def root():
    """
    根端点，返回 API 信息。
    """
    return {
        "name": "AIBank Hermes Web Chat",
        "version": "0.1.0",
        "websocket": "/ws/chat/{session_id}",
        "api": {
            "sessions": "/api/sessions",
            "config": "/api/config",
            "health": "/api/health",
            "logs": "/api/sessions/{session_id}/logs",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=18080)