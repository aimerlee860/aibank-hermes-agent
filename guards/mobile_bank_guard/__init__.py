"""
Mobile Bank Guard Plugin
========================

守护 mobile_bank 工具调用顺序，确保用户在调用需要特定参数的工具前，
已获取必要的信息（如账户列表）。

主要功能：
1. pre_tool_call 钩子：检查 balance_query 参数是否有效，无效则阻断并提示
2. post_tool_call 钩子：记录工具调用日志
"""

import json
import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

# WebSocket 日志发送器（全局，由 agent wrapper 设置）
_ws_log_sender: Optional[Callable[[Dict], None]] = None
_current_session_id: str = ""

def set_ws_sender(sender: Optional[Callable[[Dict], None]], session_id: str = ""):
    """设置 WebSocket 日志发送器（由 agent wrapper 在初始化时调用）"""
    global _ws_log_sender, _current_session_id
    _ws_log_sender = sender
    _current_session_id = session_id

def _send_log(msg: str):
    """实时发送日志到 WebSocket 和终端"""
    # 发送到 WebSocket（实时）
    if _ws_log_sender:
        try:
            _ws_log_sender({
                "type": "debug_log",
                "message": msg,
                "source": "guard",  # 标识来源为 guard
                "session_id": _current_session_id
            })
        except Exception as e:
            logger.debug(f"Failed to send log via WebSocket: {e}")

    # 打印到终端（开发调试）
    print(f"\n🛡️ [guard] {msg}")

# 会话级别的账户信息缓存
_session_accounts: Dict[str, list] = {}

# 模块加载时的初始化日志（帮助诊断缓存问题）
print("\n🛡️ [mobile_bank_guard] 🔧 模块重新加载，缓存已清空")

# 需要先调用 account_list 的工具及其参数要求
_TOOLS_REQUIRE_ACCOUNT_LIST = {
    "balance_query": {
        "param": "account_type",
        "hint": "请先调用 account_list 查询可用账户，然后使用 accountNo（如0113）或 accountName 查询余额",
    },
    "credit_card_bill": {
        "param": "card_suffix",
        "hint": "请先调用 account_list 查询信用卡列表，然后使用 accountNo（如0567）查询账单",
    },
}

# 已知的账户后缀和名称（从 accountData.json 提取）
_KNOWN_ACCOUNTS = {
    "0112": "个人活期账户",
    "0113": "个人活期账户（主账户）",
    "0114": "低余额账户（测试余额不足场景）",
    "0115": "个人定期账户",
    "0567": "工银信用卡账户（标准）",
    "0568": "工银信用卡账户（接近额度上限）",
}

# 已知的账户类型别名
_KNOWN_TYPES = {
    "活期储蓄账户",
    "定期储蓄账户",
    "信用账户",
    "储蓄卡",
    "储蓄账户",
    "活期",
    "定期",
    "信用卡",
}


def _is_valid_account_param(value: str) -> bool:
    """检查账户参数是否有效（已知后缀、名称或类型）"""
    if not value:
        return False

    # 检查是否是已知后缀
    if value in _KNOWN_ACCOUNTS:
        return True

    # 检查是否是已知账户名称的一部分
    for name in _KNOWN_ACCOUNTS.values():
        if value in name:
            return True

    # 检查是否是已知类型
    if value in _KNOWN_TYPES:
        return True

    return False


def _get_session_accounts(session_id: str) -> list:
    """获取会话缓存中的账户列表"""
    return _session_accounts.get(session_id, [])


def _update_session_accounts(session_id: str, accounts: list) -> None:
    """更新会话缓存中的账户列表"""
    _session_accounts[session_id] = accounts


def register(ctx):
    """插件注册入口"""
    ctx.register_hook("pre_tool_call", on_pre_tool_call)
    ctx.register_hook("post_tool_call", on_post_tool_call)
    _send_log("✅ 插件已注册，钩子: pre_tool_call, post_tool_call")
    logger.info("[mobile_bank_guard] 插件已注册")


def on_pre_tool_call(
    tool_name: str,
    args: Optional[Dict[str, Any]],
    task_id: str = "",
    session_id: str = "",
    tool_call_id: str = "",
) -> Optional[Dict[str, Any]]:
    """
    工具调用前检查

    对于需要账户信息的工具，检查参数是否有效。
    如果参数无效，阻断调用并提示先获取账户列表。
    """
    _send_log(f"📞 pre_tool_call 触发: tool={tool_name}, args={args}, session={session_id[:20] if session_id else 'N/A'}")

    if tool_name not in _TOOLS_REQUIRE_ACCOUNT_LIST:
        _send_log(f"   ➡️ 工具 {tool_name} 不在守护列表，放行")
        return None

    args = args or {}
    config = _TOOLS_REQUIRE_ACCOUNT_LIST[tool_name]
    param_name = config["param"]
    param_value = args.get(param_name, "")

    _send_log(f"   🔍 检查参数: {param_name}={param_value}")

    # 检查参数是否有效
    if _is_valid_account_param(param_value):
        _send_log(f"   ✅ 参数 '{param_value}' 有效（已知账户/类型），放行")
        return None  # 参数有效，允许调用

    _send_log(f"   ❌ 参数 '{param_value}' 无效")

    # 检查会话是否已获取过账户列表
    session_accounts = _get_session_accounts(session_id)
    _send_log(f"   📦 会话缓存: {len(session_accounts)} 个账户")

    if session_accounts:
        # 已有账户列表，但参数不匹配已知账户
        # 提供更精确的提示
        available = [a.get("accountNo", "") for a in session_accounts if a.get("accountNo")]
        _send_log(f"   🚫 阻断！可用账户: {available}")
        return {
            "action": "block",
            "message": (
                f"账户参数 '{param_value}' 不匹配已知账户。\n"
                f"可用账户: {', '.join(available)}\n"
                f"请使用 accountNo 或完整的 accountName 作为参数。"
            ),
        }

    # 既无有效参数，也无账户列表缓存 → 阻断并提示
    _send_log(f"   🚫 阻断！无缓存，提示先调用 account_list")
    return {
        "action": "block",
        "message": config["hint"],
    }


def on_post_tool_call(
    tool_name: str,
    args: Optional[Dict[str, Any]],
    result: str,
    task_id: str = "",
    session_id: str = "",
    tool_call_id: str = "",
) -> None:
    """
    工具调用后处理

    1. 如果是 account_list 调用，缓存账户列表
    2. 记录执行日志
    """
    args = args or {}

    _send_log(f"📞 post_tool_call: tool={tool_name} completed")

    # 缓存 account_list 结果
    if tool_name == "account_list":
        try:
            data = json.loads(result)
            if data.get("success") and data.get("accounts"):
                _update_session_accounts(session_id, data["accounts"])
                account_nos = [a.get("accountNo", "") for a in data["accounts"]]
                _send_log(f"   📦 已缓存 {len(data['accounts'])} 个账户: {account_nos}")
        except Exception as e:
            _send_log(f"   ⚠️ 解析 account_list 结果失败: {e}")

    # 显示执行结果摘要
    result_preview = result[:100] if len(result) > 100 else result
    _send_log(f"   📤 结果: {result_preview}...")