#!/usr/bin/env python3
"""
技能的快速验证脚本 - 最小版本
"""

import os
import re
import sys
from pathlib import Path

import yaml


def validate_skill(skill_path):
    """技能的基本验证"""
    skill_path = Path(skill_path)

    # 检查SKILL.md是否存在
    skill_md = skill_path / 'SKILL.md'
    if not skill_md.exists():
        return False, "未找到SKILL.md"

    # 读取并验证前置元数据
    content = skill_md.read_text()
    if not content.startswith('---'):
        return False, "未找到YAML前置元数据"

    # 提取前置元数据
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return False, "前置元数据格式无效"

    frontmatter_text = match.group(1)

    # 解析YAML前置元数据
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        if not isinstance(frontmatter, dict):
            return False, "前置元数据必须是YAML字典"
    except yaml.YAMLError as e:
        return False, f"前置元数据中的YAML无效：{e}"

    # 定义允许的属性
    ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata'}

    # 检查意外属性（不包括metadata下的嵌套键）
    unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
    if unexpected_keys:
        return False, (
            f"SKILL.md前置元数据中的意外键：{', '.join(sorted(unexpected_keys))}。"
            f"允许的属性是：{', '.join(sorted(ALLOWED_PROPERTIES))}"
        )

    # 检查必需字段
    if 'name' not in frontmatter:
        return False, "前置元数据中缺少'name'"
    if 'description' not in frontmatter:
        return False, "前置元数据中缺少'description'"

    # 提取名称进行验证
    name = frontmatter.get('name', '')
    if not isinstance(name, str):
        return False, f"名称必须是字符串，得到{type(name).__name__}"
    name = name.strip()
    if name:
        # 检查命名约定（连字符大小写：仅小写字母和连字符）
        if not re.match(r'^[a-z0-9-]+$', name):
            return False, f"名称'{name}'应该是连字符大小写（仅小写字母、数字和连字符）"
        if name.startswith('-') or name.endswith('-') or '--' in name:
            return False, f"名称'{name}'不能以连字符开头/结尾或包含连续连字符"
        # 检查名称长度（根据规范最多64个字符）
        if len(name) > 64:
            return False, f"名称太长（{len(name)}个字符）。最大为64个字符。"

    # 提取并验证描述
    description = frontmatter.get('description', '')
    if not isinstance(description, str):
        return False, f"描述必须是字符串，得到{type(description).__name__}"
    description = description.strip()
    if description:
        # 检查尖括号
        if '<' in description or '>' in description:
            return False, "描述不能包含尖括号（<或>）"
        # 检查描述长度（根据规范最多1024个字符）
        if len(description) > 1024:
            return False, f"描述太长（{len(description)}个字符）。最大为1024个字符。"

    return True, "技能有效！"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法：python quick_validate.py <skill_directory>")
        sys.exit(1)

    valid, message = validate_skill(sys.argv[1])
    print(message)
    sys.exit(0 if valid else 1)
