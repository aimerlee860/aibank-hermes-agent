"""
Mobile Bank Guard Plugin
========================

守护 mobile_bank 工具调用顺序，确保用户在调用需要特定参数的工具前，
已获取必要的信息（如账户列表）。

Hook 生命周期：
1. pre_tool_call — 检查参数是否有效，无效则阻断并给出提示
2. post_tool_call — 缓存 account_list 结果，记录执行日志
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# 会话级别的账户信息缓存
_session_accounts: Dict[str, list] = {}

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
    if not value:
        return False
    if value in _KNOWN_ACCOUNTS:
        return True
    for name in _KNOWN_ACCOUNTS.values():
        if value in name:
            return True
    if value in _KNOWN_TYPES:
        return True
    return False


def _get_session_accounts(session_id: str) -> list:
    return _session_accounts.get(session_id, [])


def _update_session_accounts(session_id: str, accounts: list) -> None:
    _session_accounts[session_id] = accounts


def register(ctx):
    """插件注册入口 — 由 PluginManager 自动调用。"""
    ctx.register_hook("pre_tool_call", on_pre_tool_call)
    ctx.register_hook("post_tool_call", on_post_tool_call)
    logger.info("mobile_bank_guard 已注册: pre_tool_call, post_tool_call")


def on_pre_tool_call(
    tool_name: str,
    args: Optional[Dict[str, Any]] = None,
    task_id: str = "",
    session_id: str = "",
    tool_call_id: str = "",
    **kwargs,
) -> Optional[Dict[str, Any]]:
    """
    工具调用前检查。

    对于需要账户信息的工具，检查参数是否有效。
    如果参数无效，阻断调用并提示先获取账户列表。
    """
    if tool_name not in _TOOLS_REQUIRE_ACCOUNT_LIST:
        return None

    args = args or {}
    config = _TOOLS_REQUIRE_ACCOUNT_LIST[tool_name]
    param_name = config["param"]
    param_value = args.get(param_name, "")

    logger.debug(
        "pre_tool_call: tool=%s param=%s value=%s session=%s",
        tool_name, param_name, param_value, session_id[:20] if session_id else "N/A",
    )

    if _is_valid_account_param(param_value):
        logger.debug("参数 '%s' 有效，放行", param_value)
        return None

    session_accounts = _get_session_accounts(session_id)
    if session_accounts:
        available = [a.get("accountNo", "") for a in session_accounts if a.get("accountNo")]
        logger.info("阻断: 参数 '%s' 不匹配已知账户，可用: %s", param_value, available)
        return {
            "action": "block",
            "message": (
                f"账户参数 '{param_value}' 不匹配已知账户。\n"
                f"可用账户: {', '.join(available)}\n"
                f"请使用 accountNo 或完整的 accountName 作为参数。"
            ),
        }

    logger.info("阻断: 无缓存，提示先调用 account_list")
    return {
        "action": "block",
        "message": config["hint"],
    }


def on_post_tool_call(
    tool_name: str,
    args: Optional[Dict[str, Any]] = None,
    result: str = "",
    task_id: str = "",
    session_id: str = "",
    tool_call_id: str = "",
    **kwargs,
) -> None:
    """工具调用后处理 — 缓存 account_list 结果。"""
    if tool_name == "account_list":
        try:
            data = json.loads(result)
            if data.get("success") and data.get("accounts"):
                _update_session_accounts(session_id, data["accounts"])
                account_nos = [a.get("accountNo", "") for a in data["accounts"]]
                logger.info("已缓存 %d 个账户: %s", len(data["accounts"]), account_nos)
        except Exception as e:
            logger.warning("解析 account_list 结果失败: %s", e)
