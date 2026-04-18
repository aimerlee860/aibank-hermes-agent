"""
WebSocket Agent Wrapper for Hermes Agent.

非侵入式包装 hermes/run_agent.py 的 AIAgent 类，
将回调函数映射为 WebSocket 事件，同时保存日志到 ServiceDB。
"""

import os
import sys
import json
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Callable, Dict, Any, List, Optional

# 添加 hermes 到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
HERMES_PATH = PROJECT_ROOT / "hermes"
if str(HERMES_PATH) not in sys.path:
    sys.path.insert(0, str(HERMES_PATH))

from service_db import ServiceDB

logger = logging.getLogger(__name__)


class WebSocketAgentWrapper:
    """
    包装 Hermes AIAgent，将流式输出和工具调用事件发送到 WebSocket，
    同时持久化到 ServiceDB 以支持历史会话加载。
    """

    def __init__(self, ws_sender: Callable[[Dict], None], session_id: Optional[str] = None):
        """
        初始化 Agent Wrapper。

        Args:
            ws_sender: 发送 WebSocket 事件的回调函数
            session_id: 会话 ID（可选，自动生成）
        """
        self.ws_sender = ws_sender
        self.session_id = session_id or str(uuid.uuid4())
        self.messages: List[Dict[str, Any]] = []
        self._agent = None
        self._initialized = False
        self._guard_handler = None
        self._service_db = ServiceDB()
        self._turn_seq = -1

    def _load_hermes_config(self) -> Dict[str, Any]:
        """加载 Hermes 配置（复用 hermes 的配置系统）。"""
        try:
            from hermes_constants import get_hermes_home
            from hermes_cli.config import load_config

            hermes_home = get_hermes_home()
            config_path = hermes_home / "config.yaml"

            if config_path.exists():
                config = load_config()
                logger.info(f"Loaded hermes config from {config_path}")
                return config
            else:
                logger.warning(f"Hermes config not found at {config_path}, using defaults")
                return {}
        except Exception as e:
            logger.error(f"Failed to load hermes config: {e}")
            return {}

    def _load_hermes_env(self) -> Dict[str, str]:
        """加载 Hermes 环境变量（API keys 等）。"""
        try:
            from hermes_constants import get_hermes_home
            from hermes_cli.env_loader import load_hermes_dotenv

            hermes_home = get_hermes_home()
            env_path = hermes_home / ".env"

            if env_path.exists():
                env_vars = {}
                load_hermes_dotenv(hermes_home=hermes_home)
                # 读取 hermes 支持的环境变量
                for key in [
                    "GLM_API_KEY", "GLM_BASE_URL",
                    "OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                    "OPENROUTER_BASE_URL", "OPENAI_BASE_URL"
                ]:
                    value = os.environ.get(key)
                    if value:
                        env_vars[key] = value
                logger.info(f"Loaded hermes env from {env_path}")
                return env_vars
            else:
                logger.warning(f"Hermes env not found at {env_path}")
                return {}
        except Exception as e:
            logger.error(f"Failed to load hermes env: {e}")
            return {}

    def _init_agent(self):
        """初始化 Hermes AIAgent（延迟初始化）。"""
        if self._initialized:
            return

        try:
            from run_agent import AIAgent
            from hermes_constants import OPENROUTER_BASE_URL
            from hermes_state import SessionDB

            # 设置 guard 的 ws_sender（hermes 已加载 plugins）
            self._setup_guard_ws_sender()

            config = self._load_hermes_config()
            env = self._load_hermes_env()

            # 确定 API key 和 base_url - hermes 支持的环境变量
            api_key = (
                env.get("GLM_API_KEY") or
                env.get("OPENROUTER_API_KEY") or
                env.get("OPENAI_API_KEY") or
                env.get("ANTHROPIC_API_KEY")
            )

            base_url = (
                env.get("GLM_BASE_URL") or
                env.get("OPENROUTER_BASE_URL") or
                env.get("OPENAI_BASE_URL") or
                OPENROUTER_BASE_URL
            )

            # 模型配置 - 支持 dict 格式 (新版 hermes) 和 string 格式
            model_config = config.get("model", {})
            if isinstance(model_config, dict):
                model = model_config.get("default", "glm-5")
                # 从配置中获取 base_url（如果有）
                config_base_url = model_config.get("base_url")
                if config_base_url:
                    base_url = config_base_url
            else:
                model = model_config or "glm-5"

            # max_iterations 从 agent.max_turns 获取
            agent_config = config.get("agent", {})
            max_iterations = agent_config.get("max_turns", config.get("max_iterations", 90))

            # 创建 Agent，配置回调 - 启用核心工具集 + mobile_bank
            self._agent = AIAgent(
                model=model,
                base_url=base_url,
                api_key=api_key,
                max_iterations=max_iterations,
                enabled_toolsets=["hermes-cli", "mobile_bank"],  # 核心工具 + 手机银行
                stream_delta_callback=self._on_text_delta,
                tool_start_callback=self._on_tool_start,
                tool_complete_callback=self._on_tool_complete,
                status_callback=self._on_status,
                session_id=self.session_id,
                session_db=SessionDB(),
                platform="web",
            )

            self._initialized = True
            logger.info(f"Initialized Hermes AIAgent with model={model}")

        except Exception as e:
            logger.error(f"Failed to initialize Hermes AIAgent: {e}")
            raise

    def _on_text_delta(self, delta: str):
        """文本流式输出回调。"""
        if delta:  # 只发送非空内容
            self.ws_sender({
                "type": "text_delta",
                "content": delta,
                "session_id": self.session_id
            })

    def _on_tool_start(self, tool_call_id: str, tool_name: str, tool_args: Dict[str, Any]):
        """工具开始执行回调。"""
        # 保存到 ServiceDB
        self._service_db.start_tool_call(
            session_id=self.session_id,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            args=tool_args,
            turn_seq=self._turn_seq,
        )

        # 发送日志（WebSocket）
        args_str = json.dumps(tool_args, ensure_ascii=False)
        self._send_debug_log(f"🔧 工具执行: {tool_name}({args_str})")

        # 发送 tool_start 事件（前端显示）
        self.ws_sender({
            "type": "tool_start",
            "name": tool_name,
            "args": tool_args,
            "tool_call_id": tool_call_id,
            "session_id": self.session_id
        })

    def _on_tool_complete(self, tool_call_id: str, tool_name: str, tool_args: Dict[str, Any], result: Any):
        """工具执行完成回调。"""
        result_str = str(result)

        # 保存到 ServiceDB（完整结果）
        self._service_db.complete_tool_call(
            tool_call_id=tool_call_id,
            result=result_str,
            status="success",
        )

        # 发送日志（WebSocket）
        result_preview = result_str[:100] + "..." if len(result_str) > 100 else result_str
        self._send_debug_log(f"✅ 工具完成: {tool_name} -> {result_preview}")

        # 发送 tool_complete 事件（前端显示，完整结果）
        self.ws_sender({
            "type": "tool_complete",
            "name": tool_name,
            "result": result_str,
            "tool_call_id": tool_call_id,
            "session_id": self.session_id
        })

    def _on_status(self, category: str, message: str):
        """状态更新回调。"""
        # 保存到 ServiceDB
        self._service_db.append_log(
            session_id=self.session_id,
            log_type="status",
            content=message,
            source="agent",
            metadata={"category": category},
            turn_seq=self._turn_seq,
        )

        # 只传递关键状态，忽略 lifecycle 等次要信息
        if category in ("thinking", "progress", "error"):
            self.ws_sender({
                "type": "status",
                "message": message,
                "category": category,
                "session_id": self.session_id
            })

    def _send_debug_log(self, message: str, source: str = "agent"):
        """发送调试日志到 WebSocket 和 ServiceDB。"""
        # 保存到 ServiceDB
        self._service_db.append_log(
            session_id=self.session_id,
            log_type="debug",
            content=message,
            source=source,
            turn_seq=self._turn_seq,
        )

        # 发送到 WebSocket
        self.ws_sender({
            "type": "debug_log",
            "message": message,
            "source": source,
            "session_id": self.session_id
        })

    def _setup_guard_ws_sender(self):
        """设置 guard 的 WebSocket 日志发送器。"""
        try:
            # hermes 加载 plugins 到 hermes_plugins namespace
            # 尝试从 hermes_plugins namespace 导入并设置 ws_sender
            try:
                from hermes_plugins.mobile_bank_guard import set_ws_sender
                # 使用包装后的发送器，同时保存到 ServiceDB
                set_ws_sender(self._guard_ws_sender_wrapper, self.session_id)
                logger.info("Guard ws_sender set via hermes_plugins namespace")
                return
            except ImportError:
                pass

            # 回退：动态导入 guards 目录的模块
            import importlib.util
            guard_path = PROJECT_ROOT / "guards" / "mobile_bank_guard" / "__init__.py"
            if guard_path.exists():
                spec = importlib.util.spec_from_file_location(
                    "mobile_bank_guard", guard_path
                )
                guard_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(guard_module)
                # 使用包装后的发送器，同时保存到 ServiceDB
                guard_module.set_ws_sender(self._guard_ws_sender_wrapper, self.session_id)
                # 同时注册到 hermes_plugins namespace
                sys.modules["hermes_plugins.mobile_bank_guard"] = guard_module
                logger.info("Guard ws_sender set via guards directory")
        except Exception as e:
            logger.warning(f"Failed to set guard ws_sender: {e}")

    def _guard_ws_sender_wrapper(self, event: Dict):
        """Guard 的 WebSocket 发送器包装，同时保存到 ServiceDB。"""
        # 如果是 debug_log 类型，保存到 ServiceDB
        if event.get("type") == "debug_log":
            self._service_db.append_log(
                session_id=self.session_id,
                log_type="debug",
                content=event.get("message", ""),
                source="guard",
                turn_seq=self._turn_seq,
            )
        # 发送到 WebSocket
        self.ws_sender(event)

    async def chat(self, message: str) -> Dict[str, Any]:
        """
        发送消息并获取响应。

        Args:
            message: 用户消息

        Returns:
            包含 final_response 和 messages 的字典
        """
        self._turn_seq += 1
        self._init_agent()

        # 发送开始处理日志
        self._send_debug_log(f"🚀 开始处理: {message[:50]}...")

        try:
            # 在后台线程运行 agent（避免阻塞 WebSocket）
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._agent.run_conversation(
                    user_message=message,
                    conversation_history=self.messages
                )
            )

            # 更新消息历史
            self.messages = result.get("messages", [])

            # 发送完成日志
            self._send_debug_log("🎉 处理完成")

            # 发送完成事件（包含响应）
            self.ws_sender({
                "type": "complete",
                "response": result.get("final_response", ""),
                "session_id": self.session_id
            })

            return result

        except Exception as e:
            logger.error(f"Chat error: {e}")
            self.ws_sender({
                "type": "error",
                "message": str(e),
                "session_id": self.session_id
            })
            # 发送完成事件以结束发送循环
            self.ws_sender({
                "type": "complete",
                "response": "",
                "session_id": self.session_id
            })
            raise

    def get_history(self) -> List[Dict[str, Any]]:
        """获取当前会话的消息历史。"""
        return self.messages

    def clear_history(self):
        """清空消息历史和 ServiceDB 日志。"""
        self.messages = []
        self._service_db.clear_session(self.session_id)