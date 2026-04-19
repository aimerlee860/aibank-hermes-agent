"""
Service Database for Web Chat Backend.

独立的数据库存储 service 服务所需的数据，包括：
- Web 会话管理（session 列表、标题等）
- 执行日志（agent/guard 运行过程）
- 工具调用详情（完整参数和结果）
- 服务配置和会话偏好

与 hermes 的 state.db 同级，位于 ~/.hermes/service.db
"""

import sqlite3
import json
import threading
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# 默认数据库路径：与 hermes state.db 同级
DEFAULT_DB_PATH = Path.home() / ".hermes" / "service.db"

# 数据库 Schema
SCHEMA_SQL = """
-- Web 会话表：管理 web chat 的会话列表
CREATE TABLE IF NOT EXISTS web_sessions (
    id TEXT PRIMARY KEY,              -- session_id (web-xxx-xxx)
    title TEXT,                       -- 会话标题（自动生成或用户设置）
    message_count INTEGER DEFAULT 0,  -- 消息数量
    started_at REAL NOT NULL,         -- 创建时间
    updated_at REAL,                  -- 最后更新时间
    source TEXT DEFAULT 'web',        -- 来源标识
    platform TEXT DEFAULT 'web',      -- 平台
    created_at REAL DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_web_sessions_started ON web_sessions(started_at DESC);

-- 执行日志表：存储 agent/guard 的运行日志
CREATE TABLE IF NOT EXISTS execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_seq INTEGER NOT NULL DEFAULT 0,
    timestamp REAL NOT NULL,
    log_type TEXT NOT NULL,      -- 'debug' | 'tool_start' | 'tool_complete' | 'status'
    source TEXT DEFAULT 'agent', -- 'agent' | 'guard'
    content TEXT NOT NULL,       -- 日志内容（文本）
    metadata TEXT,               -- JSON 扩展字段（如 tool_args, tool_result）
    created_at REAL DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_execution_logs_session ON execution_logs(session_id, timestamp);

-- 工具调用详情表：存储完整的工具调用信息
CREATE TABLE IF NOT EXISTS tool_call_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_seq INTEGER NOT NULL DEFAULT 0,
    tool_call_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    args TEXT,                   -- JSON: 工具参数
    result TEXT,                 -- 工具结果（完整，不截断）
    status TEXT DEFAULT 'pending', -- 'pending' | 'success' | 'error'
    started_at REAL,
    completed_at REAL,
    created_at REAL DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_tool_call_details_session ON tool_call_details(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_call_details_call_id ON tool_call_details(tool_call_id);

-- 服务配置表：存储 UI 配置、用户偏好等
CREATE TABLE IF NOT EXISTS service_config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at REAL DEFAULT (strftime('%s', 'now'))
);

-- 原始对话消息表：保存 user/assistant 消息
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_seq INTEGER NOT NULL DEFAULT 0,
    role TEXT NOT NULL,       -- 'user' | 'assistant'
    content TEXT NOT NULL,
    timestamp REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, timestamp);

-- 用户会话偏好表：每个 session 的 UI 状态
CREATE TABLE IF NOT EXISTS session_preferences (
    session_id TEXT PRIMARY KEY,
    show_debug_logs INTEGER DEFAULT 1,
    show_tool_calls INTEGER DEFAULT 1,
    theme TEXT DEFAULT 'dark',
    updated_at REAL DEFAULT (strftime('%s', 'now'))
);
"""


class ServiceDB:
    """
    Service 服务数据库管理类。

    线程安全，支持多进程并发访问（WAL 模式）。
    """

    _WRITE_MAX_RETRIES = 10
    _WRITE_RETRY_MIN_S = 0.010
    _WRITE_RETRY_MAX_S = 0.100

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=1.0,
            isolation_level=None,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        self._init_schema()

    def _init_schema(self):
        """初始化数据库 Schema。"""
        self._conn.executescript(SCHEMA_SQL)
        self._migrate_add_turn_seq()

    def _migrate_add_turn_seq(self):
        """为旧表添加 turn_seq 列（幂等）。"""
        for table in ("execution_logs", "tool_call_details"):
            try:
                self._conn.execute(f"ALTER TABLE {table} ADD COLUMN turn_seq INTEGER NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # 列已存在，忽略

    def _execute_write(self, fn):
        """执行写事务，带重试机制。"""
        import random
        for attempt in range(self._WRITE_MAX_RETRIES):
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                result = fn(self._conn)
                self._conn.execute("COMMIT")
                return result
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower():
                    self._conn.execute("ROLLBACK")
                    sleep_s = random.uniform(self._WRITE_RETRY_MIN_S, self._WRITE_RETRY_MAX_S)
                    time.sleep(sleep_s)
                    continue
                raise
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
        raise sqlite3.OperationalError("Database write lock timeout")

    # -------------------------------------------------------------------------
    # Web 会话管理
    # -------------------------------------------------------------------------

    def create_session(
        self,
        session_id: str,
        title: str = None,
        source: str = "web",
        platform: str = "web",
    ) -> str:
        """
        创建新会话。

        Args:
            session_id: 会话 ID
            title: 会话标题（可选）
            source: 来源标识
            platform: 平台标识

        Returns:
            session_id
        """
        started_at = time.time()

        def _do(conn):
            conn.execute(
                """INSERT OR IGNORE INTO web_sessions
                   (id, title, started_at, source, platform)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, title, started_at, source, platform),
            )
        self._execute_write(_do)
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个会话详情。

        Returns:
            会话信息，包含 {id, title, message_count, started_at, updated_at, source, platform}
        """
        with self._lock:
            cursor = self._conn.execute(
                """SELECT id, title, message_count, started_at, updated_at, source, platform
                   FROM web_sessions WHERE id = ?""",
                (session_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_sessions(self, limit: int = 50, include_empty: bool = False) -> List[Dict[str, Any]]:
        """
        获取会话列表（按创建时间倒序）。

        Args:
            limit: 最大返回数量
            include_empty: 是否包含空会话（message_count = 0）

        Returns:
            会话列表，每项包含 {id, title, message_count, started_at, updated_at, source, platform}
        """
        with self._lock:
            if include_empty:
                cursor = self._conn.execute(
                    """SELECT id, title, message_count, started_at, updated_at, source, platform
                       FROM web_sessions
                       ORDER BY started_at DESC
                       LIMIT ?""",
                    (limit,),
                )
            else:
                # 只返回有消息的会话
                cursor = self._conn.execute(
                    """SELECT id, title, message_count, started_at, updated_at, source, platform
                       FROM web_sessions
                       WHERE message_count > 0
                       ORDER BY started_at DESC
                       LIMIT ?""",
                    (limit,),
                )
            rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def update_session(
        self,
        session_id: str,
        title: str = None,
        message_count: int = None,
    ):
        """
        更新会话信息。

        Args:
            session_id: 会话 ID
            title: 新标题（可选）
            message_count: 新消息数量（可选）
        """
        updated_at = time.time()

        def _do(conn):
            if title is not None:
                conn.execute(
                    """UPDATE web_sessions SET title = ?, updated_at = ? WHERE id = ?""",
                    (title, updated_at, session_id),
                )
            if message_count is not None:
                conn.execute(
                    """UPDATE web_sessions SET message_count = ?, updated_at = ? WHERE id = ?""",
                    (message_count, updated_at, session_id),
                )
        self._execute_write(_do)

    def increment_message_count(self, session_id: str):
        """增加会话的消息数量。"""
        updated_at = time.time()

        def _do(conn):
            conn.execute(
                """UPDATE web_sessions
                   SET message_count = message_count + 1, updated_at = ?
                   WHERE id = ?""",
                (updated_at, session_id),
            )
        self._execute_write(_do)

    def delete_session(self, session_id: str):
        """
        删除会话及其所有关联数据。

        Args:
            session_id: 会话 ID
        """
        def _do(conn):
            conn.execute("DELETE FROM web_sessions WHERE id = ?", (session_id,))
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM execution_logs WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM tool_call_details WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM session_preferences WHERE session_id = ?", (session_id,))
        self._execute_write(_do)

    # -------------------------------------------------------------------------
    # 原始对话消息
    # -------------------------------------------------------------------------

    def save_chat_message(
        self,
        session_id: str,
        turn_seq: int,
        role: str,
        content: str,
    ) -> int:
        """保存一条原始对话消息（user 或 assistant）。"""
        timestamp = time.time()

        def _do(conn):
            cursor = conn.execute(
                """INSERT INTO chat_messages
                   (session_id, turn_seq, role, content, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, turn_seq, role, content, timestamp),
            )
            return cursor.lastrowid

        return self._execute_write(_do)

    def get_chat_messages(self, session_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        """获取会话的原始对话消息（按时间排序）。"""
        with self._lock:
            cursor = self._conn.execute(
                """SELECT id, turn_seq, role, content, timestamp
                   FROM chat_messages
                   WHERE session_id = ?
                   ORDER BY timestamp
                   LIMIT ?""",
                (session_id, limit),
            )
            rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def clear_chat_messages(self, session_id: str):
        """清空会话的原始对话消息。"""
        def _do(conn):
            conn.execute(
                "DELETE FROM chat_messages WHERE session_id = ?",
                (session_id,),
            )
        self._execute_write(_do)

    # -------------------------------------------------------------------------
    # 执行日志
    # -------------------------------------------------------------------------

    def append_log(
        self,
        session_id: str,
        log_type: str,
        content: str,
        source: str = "agent",
        metadata: Dict[str, Any] = None,
        turn_seq: int = 0,
    ) -> int:
        """
        添加执行日志。

        Args:
            session_id: 会话 ID
            log_type: 日志类型 ('debug' | 'tool_start' | 'tool_complete' | 'status')
            content: 日志内容
            source: 来源 ('agent' | 'guard')
            metadata: 扩展元数据（JSON）
            turn_seq: 轮次序号

        Returns:
            日志行 ID
        """
        timestamp = time.time()
        metadata_json = json.dumps(metadata) if metadata else None

        def _do(conn):
            cursor = conn.execute(
                """INSERT INTO execution_logs
                   (session_id, turn_seq, timestamp, log_type, source, content, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, turn_seq, timestamp, log_type, source, content, metadata_json),
            )
            return cursor.lastrowid

        return self._execute_write(_do)

    def get_logs(self, session_id: str, turn_seq: Optional[int] = None, limit: int = 200) -> List[Dict[str, Any]]:
        """
        获取会话的执行日志。

        Args:
            session_id: 会话 ID
            turn_seq: 轮次序号（None 表示全部）
            limit: 最大返回数量

        Returns:
            日志列表，每项包含 {id, timestamp, log_type, source, content, metadata}
        """
        with self._lock:
            if turn_seq is not None:
                cursor = self._conn.execute(
                    """SELECT id, turn_seq, timestamp, log_type, source, content, metadata
                       FROM execution_logs
                       WHERE session_id = ? AND turn_seq = ?
                       ORDER BY timestamp
                       LIMIT ?""",
                    (session_id, turn_seq, limit),
                )
            else:
                cursor = self._conn.execute(
                    """SELECT id, turn_seq, timestamp, log_type, source, content, metadata
                       FROM execution_logs
                       WHERE session_id = ?
                       ORDER BY timestamp
                       LIMIT ?""",
                    (session_id, limit),
                )
            rows = cursor.fetchall()

        result = []
        for row in rows:
            item = dict(row)
            if item.get("metadata"):
                try:
                    item["metadata"] = json.loads(item["metadata"])
                except json.JSONDecodeError:
                    pass
            result.append(item)
        return result

    def clear_logs(self, session_id: str):
        """清空会话的执行日志。"""
        def _do(conn):
            conn.execute(
                "DELETE FROM execution_logs WHERE session_id = ?",
                (session_id,),
            )
        self._execute_write(_do)

    # -------------------------------------------------------------------------
    # 工具调用详情
    # -------------------------------------------------------------------------

    def start_tool_call(
        self,
        session_id: str,
        tool_call_id: str,
        tool_name: str,
        args: Dict[str, Any] = None,
        turn_seq: int = 0,
    ) -> int:
        """
        记录工具调用开始。

        Args:
            session_id: 会话 ID
            tool_call_id: 工具调用 ID
            tool_name: 工具名称
            args: 工具参数
            turn_seq: 轮次序号

        Returns:
            行 ID
        """
        started_at = time.time()
        args_json = json.dumps(args) if args else None

        def _do(conn):
            cursor = conn.execute(
                """INSERT INTO tool_call_details
                   (session_id, turn_seq, tool_call_id, tool_name, args, started_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
                (session_id, turn_seq, tool_call_id, tool_name, args_json, started_at),
            )
            return cursor.lastrowid

        return self._execute_write(_do)

    def complete_tool_call(
        self,
        tool_call_id: str,
        result: str,
        status: str = "success",
    ):
        """
        更新工具调用完成状态。

        Args:
            tool_call_id: 工具调用 ID
            result: 工具结果（完整）
            status: 状态 ('success' | 'error')
        """
        completed_at = time.time()

        def _do(conn):
            conn.execute(
                """UPDATE tool_call_details
                   SET result = ?, status = ?, completed_at = ?
                   WHERE tool_call_id = ?""",
                (result, status, completed_at, tool_call_id),
            )
        self._execute_write(_do)

    def get_tool_calls(self, session_id: str, turn_seq: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取会话的工具调用详情。

        Args:
            session_id: 会话 ID
            turn_seq: 轮次序号（None 表示全部）

        Returns:
            工具调用列表，每项包含 {id, tool_call_id, tool_name, args, result, status, started_at, completed_at}
        """
        with self._lock:
            if turn_seq is not None:
                cursor = self._conn.execute(
                    """SELECT id, turn_seq, tool_call_id, tool_name, args, result, status, started_at, completed_at
                       FROM tool_call_details
                       WHERE session_id = ? AND turn_seq = ?
                       ORDER BY started_at""",
                    (session_id, turn_seq),
                )
            else:
                cursor = self._conn.execute(
                    """SELECT id, turn_seq, tool_call_id, tool_name, args, result, status, started_at, completed_at
                       FROM tool_call_details
                       WHERE session_id = ?
                       ORDER BY started_at""",
                    (session_id,),
                )
            rows = cursor.fetchall()

        result = []
        for row in rows:
            item = dict(row)
            if item.get("args"):
                try:
                    item["args"] = json.loads(item["args"])
                except json.JSONDecodeError:
                    pass
            result.append(item)
        return result

    def clear_tool_calls(self, session_id: str):
        """清空会话的工具调用详情。"""
        def _do(conn):
            conn.execute(
                "DELETE FROM tool_call_details WHERE session_id = ?",
                (session_id,),
            )
        self._execute_write(_do)

    # -------------------------------------------------------------------------
    # 配置管理
    # -------------------------------------------------------------------------

    def get_config(self, key: str) -> Optional[str]:
        """获取配置值。"""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT value FROM service_config WHERE key = ?",
                (key,),
            )
            row = cursor.fetchone()
            return row["value"] if row else None

    def set_config(self, key: str, value: str):
        """设置配置值。"""
        def _do(conn):
            conn.execute(
                """INSERT OR REPLACE INTO service_config (key, value, updated_at)
                   VALUES (?, ?, strftime('%s', 'now'))""",
                (key, value),
            )
        self._execute_write(_do)

    # -------------------------------------------------------------------------
    # 会话偏好
    # -------------------------------------------------------------------------

    def get_session_prefs(self, session_id: str) -> Dict[str, Any]:
        """获取会话偏好设置。"""
        with self._lock:
            cursor = self._conn.execute(
                """SELECT show_debug_logs, show_tool_calls, theme
                   FROM session_preferences WHERE session_id = ?""",
                (session_id,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {"show_debug_logs": 1, "show_tool_calls": 1, "theme": "dark"}

    def set_session_prefs(self, session_id: str, prefs: Dict[str, Any]):
        """设置会话偏好。"""
        def _do(conn):
            conn.execute(
                """INSERT OR REPLACE INTO session_preferences
                   (session_id, show_debug_logs, show_tool_calls, theme, updated_at)
                   VALUES (?, ?, ?, ?, strftime('%s', 'now'))""",
                (
                    session_id,
                    prefs.get("show_debug_logs", 1),
                    prefs.get("show_tool_calls", 1),
                    prefs.get("theme", "dark"),
                ),
            )
        self._execute_write(_do)

    # -------------------------------------------------------------------------
    # 清理
    # -------------------------------------------------------------------------

    def clear_session(self, session_id: str):
        """清空会话的日志和工具调用（保留会话记录）。"""
        self.clear_chat_messages(session_id)
        self.clear_logs(session_id)
        self.clear_tool_calls(session_id)

    def close(self):
        """关闭数据库连接。"""
        self._conn.close()