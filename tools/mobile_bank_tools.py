#!/usr/bin/env python3
"""
Mobile Bank Tools - 适配层
从 tools/mocks.py 提取所有 _mock 函数，注册为 Hermes 工具
"""

import inspect
import logging
from typing import get_type_hints, Optional

from tools.registry import registry
import tools.mocks as mocks

logger = logging.getLogger(__name__)

# ── Schema 生成器 ──────────────────────────────────────────────────

TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}

def _get_json_type(python_type) -> str:
    """Python 类型 → JSON schema type"""
    # 处理 Optional[...] 等复杂类型
    origin = getattr(python_type, "__origin__", None)
    if origin is not None:
        # Union 类型（如 Optional[str]），取第一个非 None 的类型
        args = getattr(python_type, "__args__", ())
        for arg in args:
            if arg is not type(None):
                return TYPE_MAP.get(arg, "string")
    return TYPE_MAP.get(python_type, "string")


def _generate_schema(func) -> dict:
    """从函数签名生成 OpenAI tool schema"""
    sig = inspect.signature(func)
    hints = get_type_hints(func)
    doc = inspect.getdoc(func) or ""

    # 描述取 docstring 第一段（去除空行）
    lines = [l.strip() for l in doc.split("\n") if l.strip()]
    description = lines[0] if lines else func.__name__

    properties = {}
    required = []

    for name, param in sig.parameters.items():
        if name == "self":
            continue

        param_type = hints.get(name, str)

        # 从 docstring 提取参数描述（简单匹配）
        param_desc = f"参数 {name}"
        for line in lines:
            if name in line and (":" in line or "，" in line or "接受" in line):
                param_desc = line
                break

        properties[name] = {
            "type": _get_json_type(param_type),
            "description": param_desc,
        }

        if param.default is inspect.Parameter.empty:
            required.append(name)

    return {
        "name": func.__name__.replace("_mock", ""),
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        }
    }


def _make_handler(func):
    """包装 handler：args dict → 函数参数"""
    def handler(args: dict, **kwargs) -> str:
        # 过滤掉 None 值，避免传入不需要的参数
        filtered_args = {k: v for k, v in args.items() if v is not None}
        return func(**filtered_args)
    return handler


# ── 批量注册 ───────────────────────────────────────────────────────

def _check_mobile_bank_available() -> bool:
    """检查 mobile_bank 工具是否可用"""
    # 数据文件存在即可用
    from pathlib import Path
    data_file = Path.home() / ".hermes" / "data" / "mobile_bank" / "accountData.json"
    return data_file.exists()


MOCK_FUNCTIONS = [
    name for name in dir(mocks)
    if name.endswith("_mock") and callable(getattr(mocks, name))
]

_registered_count = 0
for func_name in MOCK_FUNCTIONS:
    func = getattr(mocks, func_name)
    tool_name = func_name.replace("_mock", "")

    try:
        schema = _generate_schema(func)

        registry.register(
            name=tool_name,
            toolset="mobile_bank",
            schema=schema,
            handler=_make_handler(func),
            check_fn=_check_mobile_bank_available,
            emoji="📱",
        )
        _registered_count += 1
    except Exception as e:
        logger.warning("注册工具 %s 失败: %s", tool_name, e)

logger.info("[mobile_bank_tools] 已注册 %d 个工具", _registered_count)

# AST 发现标记：顶级 registry.register() 调用，让 discover_builtin_tools() 能识别此模块
# 使用 check_fn=lambda: False 确保标记工具永不出现在实际工具列表中
registry.register(
    name="_mobile_bank_ast_marker",
    toolset="mobile_bank",
    schema={"name": "_mobile_bank_ast_marker", "description": "AST discovery marker", "parameters": {"type": "object", "properties": {}}},
    handler=lambda args: "marker",
    check_fn=lambda: False,
)