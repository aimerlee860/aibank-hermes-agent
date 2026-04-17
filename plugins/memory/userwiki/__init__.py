"""UserProfileWikiProvider - 本地用户画像 Wiki Memory Provider.

从 Hermes 对话历史构建结构化用户画像，按交互类型组织。
替代 Honcho 的本地方案，与 session_search 配合使用。

核心功能：
- 会话结束时注入 raw session
- 异步更新 wiki（编译层）
- 新会话开始时 prefetch 返回策略建议

数据流：
  state.db → raw/sessions.jsonl → wiki/types/*.md → prefetch策略建议
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agent.memory_provider import MemoryProvider
from tools.registry import tool_error

# fcntl is Unix-only; on Windows use msvcrt for file locking
msvcrt = None
try:
    import fcntl
except ImportError:
    fcntl = None
    try:
        import msvcrt
    except ImportError:
        pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 文件锁 helper（跨平台）
# ---------------------------------------------------------------------------

def _file_lock(fd):
    """获取文件锁（跨平台）。"""
    if fcntl is None and msvcrt is None:
        return
    if fcntl:
        fcntl.flock(fd, fcntl.LOCK_EX)
    elif msvcrt:
        fd.seek(0)
        msvcrt.locking(fd.fileno(), msvcrt.LK_LOCK, 1)


def _file_unlock(fd):
    """释放文件锁（跨平台）。"""
    if fcntl is None and msvcrt is None:
        return
    if fcntl:
        fcntl.flock(fd, fcntl.LOCK_UN)
    elif msvcrt:
        try:
            fd.seek(0)
            msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
        except (OSError, IOError):
            pass


# ---------------------------------------------------------------------------
# 配置常量
# ---------------------------------------------------------------------------

INTERACTION_TYPES_REFERENCE = [
    "debugging", "architecture", "implementation", "learning",
    "review", "deployment", "refactoring", "documentation",
    "testing", "other",
]

TRIGGER_CONFIG = {
    "pending_min": 5,
    "pending_max": 20,
    "periodic_days": 7,
    "new_type": True,
}

RELEVANCE_THRESHOLD = 0.4  # 降低阈值，更容易匹配
LOW_SCORE_THRESHOLD = 0.3

MAX_CASES = {
    "success": 10,
    "fail": 5,
}

PAIN_MIN_COUNT = 2


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

CLASSIFY_PROMPT = """
给用户消息生成一个交互类型标签。

标签规则：
- 2-3个词，下划线连接
- 描述用户意图/目的，不限领域
- 示例：debugging, account_balance, travel_booking, learning_concept

消息：{message}
只返回标签，不要解释。
"""

CANDIDATE_PROMPT = """
分析用户消息，列出可能相关的交互类型（最多3个）。

考虑用户可能的意图：
- 直接解决问题？
- 学习了解？
- 排查故障？
- 其他？

用户消息：{message}

返回 JSON 数组：["type1", "type2", "type3"]
按可能性排序。只返回数组，不要解释。
"""

EXTRACT_META_PROMPT = """
分析本次会话，提取用户画像信息。

会话内容：
{messages_summary}

返回 JSON 格式：
{
  "type": "交互类型",
  "topic": "主题简述(<=50字)",
  "outcome": "resolved/abandoned/ongoing",
  "satisfaction": "positive/negative/neutral/unknown",
  "prefs": [{"key": "偏好名", "strength": 0.0-1.0}],
  "pain": ["痛点ID"],
  "success": "成功模式简述(如有)",
  "fail": "失败模式简述(如有)",
  "feedback": ["用户反馈词"],
  "summary": "会话摘要(<=200字)"
}

偏好key选项：
- direct_solution: 直接给方案
- detailed_explanation: 详细解释
- skip_basics: 跳过基础概念
- code_first: 代码优先
- multiple_options: 给多个选项
- trade_off_analysis: trade-off分析
- step_by_step: 步骤引导
- quick_fix: 快速修复优先
- thorough_analysis: 深入分析

痛点识别规则：
- 用户反复抱怨某个问题（出现"又"、"老是"、"怎么老"等）
- 用户忘记某个配置/步骤
- 用户对某个流程表示困惑
痛点命名：简短描述性ID，如 ssh_port, login_step, transfer_flow

只返回 JSON，不要解释。
"""


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

WIKI_RECALL_SCHEMA = {
    "name": "wiki_recall",
    "description": (
        "查询用户画像 Wiki，获取基于历史交互的回复策略建议。\n\n"
        "使用时机：\n"
        "- 用户发起新问题时，了解该类型问题的历史用户偏好\n"
        "- 决定回复风格、详细程度时\n\n"
        "返回内容：\n"
        "- 推荐的回复策略\n"
        "- 应避免的策略\n"
        "- 相关痛点提醒\n\n"
        "如果需要查找具体历史对话细节，使用 session_search 工具。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "当前用户问题或问题描述"
            },
            "type": {
                "type": "string",
                "description": "(可选) 明确指定交互类型"
            }
        },
        "required": ["query"]
    }
}

WIKI_PAGE_SCHEMA = {
    "name": "wiki_page",
    "description": "读取 Wiki 中特定页面的完整内容。",
    "parameters": {
        "type": "object",
        "properties": {
            "page": {
                "type": "string",
                "description": "页面路径，如 'debugging' 或 'patterns/recurring_pain_points'"
            }
        },
        "required": ["page"]
    }
}

WIKI_STATUS_SCHEMA = {
    "name": "wiki_status",
    "description": "查看 Wiki 当前状态。",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}


# ---------------------------------------------------------------------------
# UserProfileWikiProvider
# ---------------------------------------------------------------------------

class UserProfileWikiProvider(MemoryProvider):
    """本地用户画像 Wiki Provider。

    从对话历史构建结构化用户画像，按交互类型组织。
    新会话开始时返回策略建议。
    """

    def __init__(self):
        self._raw_dir: Optional[Path] = None
        self._wiki_dir: Optional[Path] = None
        self._state: Dict = {}
        self._session_id: str = ""

    @property
    def name(self) -> str:
        return "userwiki"

    def is_available(self) -> bool:
        """Wiki provider 始终可用（本地，无外部依赖）。"""
        return True

    def get_config_schema(self) -> List[Dict[str, Any]]:
        """Wiki 配置项（可选调整）。"""
        return [
            {"key": "trigger_pending_min", "description": "触发更新的最小待处理数", "default": "5"},
            {"key": "trigger_periodic_days", "description": "周期性更新天数", "default": "7"},
        ]

    def initialize(self, session_id: str, **kwargs) -> None:
        """初始化 Wiki 目录结构。"""
        from hermes_constants import get_hermes_home
        hermes_home = kwargs.get("hermes_home") or str(get_hermes_home())

        self._raw_dir = Path(hermes_home) / "profile" / "raw"
        self._wiki_dir = Path(hermes_home) / "profile" / "wiki"
        self._session_id = session_id

        # 创建目录
        self._raw_dir.mkdir(parents=True, exist_ok=True)
        self._wiki_dir.mkdir(parents=True, exist_ok=True)
        (self._wiki_dir / "types").mkdir(exist_ok=True)
        (self._wiki_dir / "patterns").mkdir(exist_ok=True)

        # 初始化 wiki 结构（如果不存在）
        if not (self._wiki_dir / "state.json").exists():
            self._init_wiki_structure()

        # 加载状态
        self._state = self._read_state()

        # 检查是否有待执行的更新
        if self._state.get("update_pending"):
            try:
                self._execute_update()
                self._state["update_pending"] = False
                self._write_state(self._state)
            except Exception as e:
                logger.warning("Wiki update failed: %s", e)

    def _init_wiki_structure(self) -> None:
        """初始化 Wiki 目录结构和基础文件。"""
        initial_state = {
            "version": 1,
            "last_update": None,
            "total_sessions": 0,
            "processed_sessions": 0,
            "pending_ids": [],
            "type_counts": {},
            "pain_point_counts": {},
            "update_pending": False,
        }
        self._write_state(initial_state)

        # 创建 index.md
        index_content = "# User Profile Wiki Index\n\n> 初始化中，暂无数据\n"
        (self._wiki_dir / "index.md").write_text(index_content)

        # 创建空痛点页面
        pain_content = "# 反复出现的痛点\n\n> 暂无数据\n"
        (self._wiki_dir / "patterns" / "recurring_pain_points.md").write_text(pain_content)

        logger.info("Wiki structure initialized")

    # -- 文件操作（带锁） -----------------------------------------------

    def _read_state(self) -> Dict:
        """读取 state.json。"""
        path = self._wiki_dir / "state.json"
        if not path.exists():
            return {}
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_state(self, state: Dict) -> None:
        """写入 state.json（带锁）。"""
        path = self._wiki_dir / "state.json"
        with open(path, "w") as f:
            _file_lock(f)
            json.dump(state, f, ensure_ascii=False, indent=2)
            f.flush()
            _file_unlock(f)

    def _append_raw_session(self, meta: Dict) -> None:
        """追加到 sessions.jsonl（带锁）。"""
        path = self._raw_dir / "sessions.jsonl"
        with open(path, "a") as f:
            _file_lock(f)
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")
            f.flush()
            _file_unlock(f)

    def _add_pending_id(self, session_id: str) -> None:
        """添加 pending ID 到 state（带锁）。"""
        path = self._wiki_dir / "state.json"
        with open(path, "r+") as f:
            _file_lock(f)
            state = json.load(f)
            if session_id not in state.get("pending_ids", []):
                state.setdefault("pending_ids", []).append(session_id)
            state["total_sessions"] = state.get("total_sessions", 0) + 1
            f.seek(0)
            json.dump(state, f, ensure_ascii=False, indent=2)
            f.truncate()
            _file_unlock(f)

    def _read_raw_sessions(self) -> List[Dict]:
        """读取所有 raw sessions。"""
        path = self._raw_dir / "sessions.jsonl"
        if not path.exists():
            return []
        sessions = []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        sessions.append(json.loads(line))
                    except Exception:
                        pass
        return sessions

    def _read_sessions_by_ids(self, ids: List[str]) -> List[Dict]:
        """按 ID 读取 sessions。"""
        all_sessions = self._read_raw_sessions()
        return [s for s in all_sessions if s.get("id") in ids]

    # -- Provider 接口 -----------------------------------------------

    def system_prompt_block(self) -> str:
        """返回 Wiki 状态提示。"""
        if not self._has_any_type_page():
            return ""

        stats = self._get_stats()
        total = stats.get("total_sessions", 0)
        types_count = len(stats.get("type_counts", {}))

        if total == 0:
            return ""

        return f"[UserWiki] {total}次历史会话，已识别{types_count}种交互类型画像"

    def prefetch(self, query: str, **kwargs) -> str:
        """新会话开始时返回策略建议。"""
        if not self._has_any_type_page():
            return ""

        # 生成候选类型
        candidates = self._get_candidate_types(query)

        # 过滤有效候选
        valid = [t for t in candidates if self._type_page_exists(t)]
        if not valid:
            return ""

        # 计算相关性分数
        scored = [(t, self._compute_relevance(query, t)) for t in valid]

        # 筛选高于阈值
        high = [(t, s) for t, s in scored if s >= RELEVANCE_THRESHOLD]
        if not high:
            return ""

        # 合并策略
        high.sort(key=lambda x: -x[1])
        top_types = [t for t, _ in high[:3]]
        return self._merge_strategies(top_types)

    def on_session_end(self, messages: List[Dict[str, Any]], **kwargs) -> None:
        """会话结束时注入 raw session。"""
        if not messages:
            return

        try:
            # 提取元数据
            meta = self._extract_session_meta(messages)

            # 补充自动字段
            meta["id"] = kwargs.get("session_id") or self._session_id or self._gen_id()
            meta["ts"] = datetime.utcnow().isoformat() + "Z"
            meta["turns"] = len([m for m in messages if m.get("role") == "user"])

            # 追加到 raw
            self._append_raw_session(meta)

            # 添加 pending
            self._add_pending_id(meta["id"])

            # 检查触发条件
            if self._should_trigger_update():
                self._state = self._read_state()
                self._state["update_pending"] = True
                self._write_state(self._state)

        except Exception as e:
            logger.warning("Session meta extraction failed: %s", e)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [WIKI_RECALL_SCHEMA, WIKI_PAGE_SCHEMA, WIKI_STATUS_SCHEMA]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        if tool_name == "wiki_recall":
            return self._handle_wiki_recall(args)
        elif tool_name == "wiki_page":
            return self._handle_wiki_page(args)
        elif tool_name == "wiki_status":
            return self._handle_wiki_status(args)
        return tool_error(f"Unknown wiki tool: {tool_name}")

    def sync_turn(self, user_content: str, assistant_content: str, **kwargs) -> None:
        """Wiki 不做实时 sync，只在 session_end 时处理。"""
        pass

    def shutdown(self) -> None:
        """清理。"""
        self._state = {}

    # -- 类型分类与查询 -----------------------------------------------

    def _classify_type(self, message: str) -> str:
        """使用 LLM 分类交互类型。"""
        try:
            from agent.auxiliary_client import call_llm
            response = call_llm(
                task="flush_memories",  # 使用通用任务配置
                messages=[{"role": "user", "content": CLASSIFY_PROMPT.format(message=message)}],
                max_tokens=20,
            )
            if response and hasattr(response, "choices") and response.choices:
                result = response.choices[0].message.content
                if result:
                    # 清理结果，提取标签
                    label = result.strip().split()[0] if result.strip() else "other"
                    return label.lower().replace(" ", "_").replace("-", "_")
        except Exception as e:
            logger.debug("LLM classify failed: %s", e)
        return "other"

    def _get_candidate_types(self, query: str) -> List[str]:
        """生成候选类型列表。"""
        # 首先尝试 LLM 分类
        primary_type = self._classify_type(query)

        # 获取已存在的类型作为候选补充
        existing_types = self._get_existing_types()

        candidates = [primary_type]

        # 如果已存在类型中有相似的，也加入候选
        for ext_type in existing_types:
            if ext_type != primary_type and self._is_type_related(query, ext_type):
                candidates.append(ext_type)

        return candidates[:3]

    def _is_type_related(self, query: str, type_name: str) -> bool:
        """检查 query 是否与某类型相关（简单关键词匹配）。"""
        type_keywords = {
            "debugging": ["error", "bug", "不工作", "报错", "失败", "timeout", "exception"],
            "architecture": ["设计", "架构", "方案", "选型", "structure", "design"],
            "implementation": ["实现", "编写", "开发", "添加", "创建", "build", "implement"],
            "learning": ["解释", "是什么", "怎么工作", "理解", "学习", "explain", "learn"],
            "review": ["审查", "检查", "优化", "改进", "review", "optimize"],
            "deployment": ["部署", "配置", "环境", "安装", "deploy", "config"],
            "testing": ["测试", "test", "unit", "pytest"],
        }

        keywords = type_keywords.get(type_name, [])
        query_lower = query.lower()
        return any(kw in query_lower for kw in keywords)

    def _type_page_exists(self, type_name: str) -> bool:
        """检查类型页面是否存在。"""
        return (self._wiki_dir / "types" / f"{type_name}.md").exists()

    def _has_any_type_page(self) -> bool:
        """检查是否有任何类型页面。"""
        types_dir = self._wiki_dir / "types"
        if not types_dir.exists():
            return False
        return any(f.suffix == ".md" for f in types_dir.iterdir() if f.is_file())

    def _get_existing_types(self) -> List[str]:
        """获取已存在的类型列表。"""
        types_dir = self._wiki_dir / "types"
        if not types_dir.exists():
            return []
        types = []
        for f in types_dir.iterdir():
            if f.is_file() and f.suffix == ".md":
                types.append(f.stem)
        return types

    def _compute_relevance(self, query: str, type_name: str) -> float:
        """计算 query 与类型的相关性分数。"""
        data = self._parse_type_page(type_name)

        score = 0.0

        # 因素1：关键词匹配
        topic_keywords = self._extract_keywords(query)
        # 从成功案例的 topic 和类型名称中提取关键词
        page_topics = [case.get("topic", "") for case in data.get("success_cases", [])]
        # 如果没有成功案例，从 raw sessions 获取 topic 信息
        if not page_topics:
            # 从 state 的 type_counts 确认该类型存在
            # 并从 raw sessions 中获取相关 topic
            all_sessions = self._read_raw_sessions()
            for s in all_sessions:
                if s.get("type") == type_name:
                    page_topics.append(s.get("topic", ""))
        keyword_match = self._keyword_overlap_score(topic_keywords, page_topics)
        score += keyword_match * 0.4

        # 因素2：痛点关联
        pain_match = self._check_pain_match(query, data.get("pain_refs", []))
        score += pain_match * 0.3

        # 因素3：会话数权重（可信度）
        session_weight = min(data.get("session_count", 0) / 10, 1.0)
        score += session_weight * 0.2

        # 因素4：成功率
        success_weight = data.get("success_rate", 50) / 100
        score += success_weight * 0.1

        return score

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（支持中英文混合）。"""
        # 移除标点
        text = re.sub(r'[^\w\u4e00-\u9fff]', ' ', text.lower())
        words = []
        for part in text.split():
            # 分离中文和英文
            english_parts = re.findall(r'[a-z0-9]+', part)
            chinese_parts = re.findall(r'[\u4e00-\u9fff]+', part)
            # 英文词（过滤短词）
            for w in english_parts:
                if len(w) > 2:
                    words.append(w)
            # 中文词（保留）
            for w in chinese_parts:
                words.append(w)
        return words

    def _keyword_overlap_score(self, query_keywords: List[str], topics: List[str]) -> float:
        """计算关键词重叠分数。"""
        if not query_keywords or not topics:
            return 0.0

        topic_words = set()
        for topic in topics:
            topic_words.update(self._extract_keywords(topic))

        overlap = set(query_keywords) & topic_words
        return len(overlap) / max(len(query_keywords), 1)

    def _check_pain_match(self, query: str, pain_refs: List[str]) -> float:
        """检查 query 是否涉及痛点。"""
        if not pain_refs:
            return 0.0

        pain_info = self._get_pain_points_info()
        query_lower = query.lower()

        for pain_id in pain_refs:
            info = pain_info.get(pain_id, {})
            problem = info.get("problem", "")
            if problem and any(w in query_lower for w in self._extract_keywords(problem)):
                return 1.0

        return 0.0

    # -- 页面解析与合并 -----------------------------------------------

    def _parse_type_page(self, type_name: str) -> Dict:
        """解析类型页面为结构化数据（容错处理）。"""
        path = self._wiki_dir / "types" / f"{type_name}.md"

        result = {
            "session_count": 0,
            "success_rate": 50,
            "prefs": {},
            "success_cases": [],
            "fail_cases": [],
            "pain_refs": [],
        }

        if not path.exists():
            return result

        try:
            content = path.read_text()
        except Exception:
            return result

        # 解析 header
        match = re.search(r'> 会话: (\d+)', content)
        if match:
            result["session_count"] = int(match.group(1))

        match = re.search(r'成功率: (\d+)%', content)
        if match:
            result["success_rate"] = int(match.group(1))

        # 解析偏好
        prefs_section = self._extract_section(content, "## 观察偏好")
        for line in prefs_section.split("\n"):
            m = re.match(r'(\w+):\s*([\d.]+)', line)
            if m:
                result["prefs"][m.group(1)] = float(m.group(2))

        # 解析成功案例
        success_section = self._extract_section(content, "## 成功案例")
        for block in re.split(r'### ', success_section):
            if not block.strip():
                continue
            lines = block.strip().split("\n")
            if lines:
                header = lines[0]
                date_match = re.match(r'(\d{4}-\d{2}-\d{2})', header)
                case = {
                    "date": date_match.group(1) if date_match else "",
                    "topic": header.split(maxsplit=1)[-1] if len(header.split()) > 1 else "",
                    "strategy": "",
                }
                for line in lines[1:]:
                    if line.startswith("策略:"):
                        case["strategy"] = line.replace("策略:", "").strip()
                if case["date"]:
                    result["success_cases"].append(case)

        # 解析痛点
        pain_section = self._extract_section(content, "## 痛点关联")
        for line in pain_section.split("\n"):
            m = re.match(r'(\w+)', line.strip())
            if m and m.group(1) not in ["##", "痛点", "关联"]:
                result["pain_refs"].append(m.group(1))

        return result

    def _extract_section(self, content: str, header: str) -> str:
        """提取 markdown section 内容。"""
        try:
            start = content.index(header)
            next_pos = content.find("\n## ", start + len(header))
            if next_pos == -1:
                return content[start:]
            return content[start:next_pos]
        except ValueError:
            return ""

    def _merge_strategies(self, types: List[str]) -> str:
        """合并多个类型的策略建议。"""
        if not types:
            return ""

        if len(types) == 1:
            return self._build_single_strategy(types[0])

        # 多类型：提取共性
        lines = ["[用户画像 - 多场景相关]", ""]
        lines.append(f"相关类型: {', '.join(types)}")
        lines.append("")

        # 收集跨类型共性偏好
        all_prefs = defaultdict(float)
        pref_counts = defaultdict(int)

        for type_name in types:
            data = self._parse_type_page(type_name)
            for key, strength in data.get("prefs", {}).items():
                all_prefs[key] += strength
                pref_counts[key] += 1

        # 平均偏好（出现次数 >= 类型数一半）
        common_prefs = {}
        for k in all_prefs:
            if pref_counts[k] >= len(types) * 0.5:
                common_prefs[k] = all_prefs[k] / pref_counts[k]

        if common_prefs:
            lines.append("## 跨场景共性")
            for key, strength in sorted(common_prefs.items(), key=lambda x: -x[1]):
                if strength > 0.6:
                    lines.append(f"- {self._pref_to_text(key)}")
            lines.append("")

        # 各类型建议
        for type_name in types:
            data = self._parse_type_page(type_name)
            lines.append(f"## {type_name}")
            lines.append(f"(会话: {data.get('session_count', 0)}次)")
            if data.get("success_cases"):
                recent = data["success_cases"][-1]
                lines.append(f"最近成功: {recent.get('strategy', '')}")
            lines.append("")

        return "\n".join(lines)

    def _build_single_strategy(self, type_name: str) -> str:
        """构建单类型策略建议。"""
        data = self._parse_type_page(type_name)

        lines = [f"[用户画像 - {type_name}]", ""]

        # 统计
        lines.append(f"历史会话: {data.get('session_count', 0)}次，成功率{data.get('success_rate', 50)}%")
        lines.append("")

        # 推荐策略
        prefs = data.get("prefs", {})
        lines.append("## 推荐策略")
        if prefs.get("direct_solution", 0) > 0.6:
            lines.append("- 直接给出方案/假设")
        if prefs.get("code_first", 0) > 0.6:
            lines.append("- 代码优先")
        if prefs.get("skip_basics", 0) > 0.5:
            lines.append("- 跳过基础概念")
        if prefs.get("multiple_options", 0) > 0.5:
            lines.append("- 给多个可能原因")
        if not prefs:
            lines.append("- 无明确偏好记录")
        lines.append("")

        # 应避免
        lines.append("## 应避免")
        if prefs.get("direct_solution", 0) > 0.7:
            lines.append("- 不要先问大量问题")
        if prefs.get("skip_basics", 0) > 0.5:
            lines.append("- 不要解释基础概念")
        else:
            lines.append("- 无明确避免项")
        lines.append("")

        # 痛点提醒
        if data.get("pain_refs"):
            lines.append("## 相关痛点")
            for pain_id in data["pain_refs"][:3]:
                count = self._state.get("pain_point_counts", {}).get(pain_id, 0)
                lines.append(f"- {pain_id} ({count}次)")
            lines.append("")

        return "\n".join(lines)

    def _pref_to_text(self, key: str) -> str:
        """偏好 key 转文字。"""
        mapping = {
            "direct_solution": "直接给方案",
            "skip_basics": "跳过基础解释",
            "code_first": "代码优先",
            "detailed_explanation": "详细解释",
            "multiple_options": "给多个选项",
            "step_by_step": "步骤引导",
        }
        return mapping.get(key, key)

    # -- 会话元数据提取 -----------------------------------------------

    def _extract_session_meta(self, messages: List[Dict]) -> Dict:
        """从会话提取元数据（LLM + 规则）。"""
        # 准备会话摘要
        summary = self._summarize_messages(messages)

        # 尝试 LLM 提取
        try:
            from agent.auxiliary_client import call_llm
            response = call_llm(
                task="flush_memories",
                messages=[{"role": "user", "content": EXTRACT_META_PROMPT.format(messages_summary=summary)}],
                max_tokens=500,
            )
            if response and hasattr(response, "choices") and response.choices:
                result = response.choices[0].message.content
                if result:
                    # 解析 JSON
                    result = result.strip()
                    # 移除可能的 markdown 代码块标记
                    if result.startswith("```"):
                        result = re.sub(r'^```\w*\n?', '', result)
                        result = re.sub(r'\n?```$', '', result)
                    if result.startswith("{"):
                        meta = json.loads(result)
                        # 验证必要字段
                        if "type" in meta and "topic" in meta:
                            return meta
        except Exception as e:
            logger.debug("LLM meta extraction failed: %s", e)

        # Fallback：规则提取
        return self._rule_extract_meta(messages, summary)

    def _summarize_messages(self, messages: List[Dict]) -> str:
        """生成会话摘要。"""
        parts = []
        for m in messages[:20]:  # 最多20条
            role = m.get("role", "")
            content = m.get("content", "")
            if isinstance(content, str):
                content = content[:200]  # 截断
            parts.append(f"{role}: {content}")

        return "\n".join(parts)

    def _rule_extract_meta(self, messages: List[Dict], summary: str) -> Dict:
        """规则提取元数据（fallback）。"""
        meta = {
            "type": "other",
            "topic": "",
            "outcome": "unknown",
            "satisfaction": "unknown",
            "prefs": [],
            "pain": [],
            "success": None,
            "fail": None,
            "feedback": [],
            "summary": summary[:200],
        }

        # 类型推断（关键词）
        summary_lower = summary.lower()
        if any(kw in summary_lower for kw in ["error", "报错", "bug", "失败", "不工作"]):
            meta["type"] = "debugging"
        elif any(kw in summary_lower for kw in ["设计", "架构", "方案", "选型"]):
            meta["type"] = "architecture"
        elif any(kw in summary_lower for kw in ["实现", "编写", "开发", "添加功能"]):
            meta["type"] = "implementation"
        elif any(kw in summary_lower for kw in ["解释", "是什么", "怎么工作"]):
            meta["type"] = "learning"

        # 反馈词提取
        feedback_words = ["thanks", "谢谢", "好的", "搞定", "work", "worked", "great", "棒"]
        for w in feedback_words:
            if w in summary_lower:
                meta["feedback"].append(w)
                meta["satisfaction"] = "positive"

        # 痛点提取
        pain_patterns = [
            (r"又忘了", "forget_config"),
            (r"老是", "recurring_issue"),
            (r"怎么老", "recurring_issue"),
        ]
        for pattern, pain_id in pain_patterns:
            if re.search(pattern, summary_lower):
                meta["pain"].append(pain_id)

        # 主题提取（第一条用户消息）
        for m in messages:
            if m.get("role") == "user":
                content = m.get("content", "")
                if isinstance(content, str):
                    meta["topic"] = content[:50]
                break

        return meta

    def _gen_id(self) -> str:
        """生成唯一 ID。"""
        import random
        import string
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"sess_{datetime.utcnow().strftime('%Y%m%d')}_{suffix}"

    # -- Wiki 更新 -----------------------------------------------

    def _should_trigger_update(self) -> Tuple[bool, str]:
        """检查是否应触发更新。"""
        state = self._read_state()
        pending_count = len(state.get("pending_ids", []))

        # 强制触发：积压过多
        if pending_count >= TRIGGER_CONFIG["pending_max"]:
            return True, "backlog_overflow"

        # 新类型检测
        pending_sessions = self._read_sessions_by_ids(state.get("pending_ids", []))
        existing_types = set(state.get("type_counts", {}).keys())
        new_types = {s.get("type", "other") for s in pending_sessions} - existing_types
        if new_types:
            return True, "new_type"

        # 后台触发：达到最小阈值
        if pending_count >= TRIGGER_CONFIG["pending_min"]:
            return True, "threshold"

        # 周期性
        last_update = state.get("last_update")
        if last_update:
            try:
                last_dt = datetime.fromisoformat(last_update.replace("Z", ""))
                if (datetime.utcnow() - last_dt).days >= TRIGGER_CONFIG["periodic_days"]:
                    return True, "periodic"
            except Exception:
                pass

        return False, ""

    def _execute_update(self) -> None:
        """执行 Wiki 更新。"""
        state = self._read_state()
        pending_ids = state.get("pending_ids", [])

        if not pending_ids:
            return

        pending_sessions = self._read_sessions_by_ids(pending_ids)

        # 按 type 分组
        by_type = defaultdict(list)
        for s in pending_sessions:
            by_type[s.get("type", "other")].append(s)

        # 更新各类型页面
        for type_name, sessions in by_type.items():
            self._update_type_page(type_name, sessions)

        # 更新痛点
        self._update_pain_points(pending_sessions)

        # 更新 index.md
        self._update_index()

        # 更新 state（重新读取以保留中间更新）
        state = self._read_state()
        state["pending_ids"] = []
        state["processed_sessions"] = state.get("processed_sessions", 0) + len(pending_sessions)
        state["last_update"] = datetime.utcnow().isoformat() + "Z"
        state["update_pending"] = False
        self._write_state(state)

        logger.info("Wiki updated: %d sessions processed", len(pending_sessions))

    def _update_type_page(self, type_name: str, new_sessions: List[Dict]) -> None:
        """更新类型页面。"""
        page_path = self._wiki_dir / "types" / f"{type_name}.md"

        # 如果不存在，创建新页面
        if not page_path.exists():
            self._create_type_page(type_name)

        # 解析现有数据
        existing = self._parse_type_page(type_name)

        # 合并新数据
        merged = self._merge_type_data(existing, new_sessions)

        # 写回
        self._write_type_page(page_path, merged)

        # 更新 type_counts
        self._state = self._read_state()
        self._state.setdefault("type_counts", {})[type_name] = merged["session_count"]
        self._write_state(self._state)

    def _create_type_page(self, type_name: str) -> None:
        """创建新类型页面。"""
        page_path = self._wiki_dir / "types" / f"{type_name}.md"

        template = f"""# {type_name}

> 会话: 0 | 成功率: 50% | 最近: N/A

## 策略建议

### 推荐
- 无历史数据

### 避免
- 无历史数据

## 详细程度

默认: 待观察

## 成功案例

> 暂无数据

## 失败案例

> 暂无数据

## 观察偏好

> 暂无数据

## 痛点关联

> 暂无数据
"""
        page_path.write_text(template)

    def _merge_type_data(self, existing: Dict, new_sessions: List[Dict]) -> Dict:
        """合并新会话数据。"""
        merged = existing.copy()

        # 更新计数
        merged["session_count"] += len(new_sessions)

        # 更新成功率
        resolved = sum(1 for s in new_sessions if s.get("outcome") == "resolved")
        new_rate = resolved / len(new_sessions) if new_sessions else 0
        old_count = existing["session_count"] - len(new_sessions)
        if old_count > 0 and merged["session_count"] > 0:
            merged["success_rate"] = int(
                (existing["success_rate"] * old_count + new_rate * 100 * len(new_sessions))
                / merged["session_count"]
            )

        # 合并偏好
        for s in new_sessions:
            for pref in s.get("prefs", []):
                key = pref.get("key")
                strength = pref.get("strength", 0.5)
                if key:
                    if key in merged["prefs"]:
                        old_s = merged["prefs"][key]
                        merged["prefs"][key] = (old_s * old_count + strength * len(new_sessions)) / max(merged["session_count"], 1)
                    else:
                        merged["prefs"][key] = strength

        # 添加成功案例
        for s in new_sessions:
            if s.get("success"):
                merged["success_cases"].append({
                    "date": s.get("ts", "")[:10],
                    "topic": s.get("topic", ""),
                    "strategy": s.get("success", ""),
                    "reaction": s.get("feedback", [""])[0] if s.get("feedback") else "",
                })

        # 添加失败案例
        for s in new_sessions:
            if s.get("fail"):
                merged["fail_cases"].append({
                    "date": s.get("ts", "")[:10],
                    "topic": s.get("topic", ""),
                    "strategy": s.get("fail", ""),
                    "lesson": "",
                })

        # 合并痛点引用
        for s in new_sessions:
            for pain_id in s.get("pain", []):
                if pain_id not in merged["pain_refs"]:
                    merged["pain_refs"].append(pain_id)

        # 截断案例
        merged["success_cases"] = merged["success_cases"][-MAX_CASES["success"]:]
        merged["fail_cases"] = merged["fail_cases"][-MAX_CASES["fail"]:]

        return merged

    def _write_type_page(self, path: Path, data: Dict) -> None:
        """写入类型页面。"""
        lines = []

        # Header
        recent_date = ""
        if data["success_cases"]:
            recent_date = data["success_cases"][-1].get("date", "")
        lines.append(f"# {path.stem}")
        lines.append("")
        lines.append(f"> 会话: {data['session_count']} | 成功率: {data['success_rate']}% | 最近: {recent_date}")
        lines.append("")

        # 策略建议
        lines.append("## 策略建议")
        lines.append("")
        lines.append("### 推荐")
        prefs = data.get("prefs", {})
        if prefs.get("direct_solution", 0) > 0.6:
            lines.append("- 直接给方案，少问问题")
        if prefs.get("code_first", 0) > 0.6:
            lines.append("- 代码优先")
        if prefs.get("skip_basics", 0) > 0.5:
            lines.append("- 跳过基础概念")
        if prefs.get("multiple_options", 0) > 0.5:
            lines.append("- 给多个选项")
        if not any(prefs.get(k, 0) > 0.5 for k in ["direct_solution", "code_first", "skip_basics", "multiple_options"]):
            lines.append("- 无强偏好")
        lines.append("")
        lines.append("### 避免")
        if prefs.get("direct_solution", 0) > 0.7:
            lines.append("- 不要先问大量问题")
        if prefs.get("skip_basics", 0) > 0.5:
            lines.append("- 不要解释基础概念")
        else:
            lines.append("- 无明确避免项")
        lines.append("")

        # 详细程度
        lines.append("## 详细程度")
        lines.append("")
        default_level = "简洁" if prefs.get("direct_solution", 0) > 0.6 else "中等"
        lines.append(f"默认: {default_level}")
        lines.append("")

        # 成功案例
        lines.append("## 成功案例")
        lines.append("")
        for case in data["success_cases"]:
            lines.append(f"### {case['date']} {case['topic']}")
            lines.append(f"策略: {case['strategy']}")
            if case.get("reaction"):
                lines.append(f"反应: {case['reaction']}")
            lines.append("")

        # 失败案例
        if data["fail_cases"]:
            lines.append("## 失败案例")
            lines.append("")
            for case in data["fail_cases"]:
                lines.append(f"### {case['date']} {case['topic']}")
                lines.append(f"问题: {case['strategy']}")
                lines.append("教训: 待补充")
                lines.append("")

        # 观察偏好
        lines.append("## 观察偏好")
        lines.append("")
        for key, strength in sorted(prefs.items(), key=lambda x: -x[1]):
            level = "strong" if strength > 0.7 else "moderate" if strength > 0.5 else "weak"
            lines.append(f"{key}: {strength:.1f} ({level})")
        lines.append("")

        # 痛点关联
        lines.append("## 痛点关联")
        lines.append("")
        if data["pain_refs"]:
            pain_counts = self._state.get("pain_point_counts", {})
            for pain_id in data["pain_refs"]:
                count = pain_counts.get(pain_id, 0)
                lines.append(f"{pain_id} ({count}次)")
        else:
            lines.append("> 无关联痛点")
        lines.append("")

        path.write_text("\n".join(lines))

    def _update_pain_points(self, sessions: List[Dict]) -> None:
        """更新痛点统计和页面。"""
        pain_counts = defaultdict(int)
        pain_sessions = defaultdict(list)

        for s in sessions:
            for pain_id in s.get("pain", []):
                pain_counts[pain_id] += 1
                pain_sessions[pain_id].append(s.get("id", ""))

        # 更新 state
        self._state = self._read_state()
        existing_counts = self._state.get("pain_point_counts", {})
        for pain_id, count in pain_counts.items():
            existing_counts[pain_id] = existing_counts.get(pain_id, 0) + count
        self._state["pain_point_counts"] = existing_counts
        self._write_state(self._state)

        # 更新页面（只保留高频）
        self._write_pain_points_page(existing_counts)

    def _write_pain_points_page(self, pain_counts: Dict) -> None:
        """写入痛点页面。"""
        path = self._wiki_dir / "patterns" / "recurring_pain_points.md"

        lines = ["# 反复出现的痛点", ""]
        lines.append("> 只记录出现 >= 2 次的痛点")
        lines.append("")
        lines.append("---")
        lines.append("")

        for pain_id, count in sorted(pain_counts.items(), key=lambda x: -x[1]):
            if count >= PAIN_MIN_COUNT:
                lines.append(f"## {pain_id}")
                lines.append("")
                lines.append(f"次数: {count}")
                lines.append("")
                lines.append("---")
                lines.append("")

        if not any(c >= PAIN_MIN_COUNT for c in pain_counts.values()):
            lines.append("> 暂无高频痛点")

        path.write_text("\n".join(lines))

    def _get_pain_points_info(self) -> Dict:
        """读取痛点信息。"""
        path = self._wiki_dir / "patterns" / "recurring_pain_points.md"
        if not path.exists():
            return {}

        try:
            content = path.read_text()
        except Exception:
            return {}

        info = {}
        for block in re.split(r'## ', content):
            if not block.strip():
                continue
            lines = block.strip().split("\n")
            if lines:
                pain_id = lines[0].strip()
                count = 0
                for line in lines:
                    m = re.match(r'次数: (\d+)', line)
                    if m:
                        count = int(m.group(1))
                info[pain_id] = {"count": count}

        return info

    def _update_index(self) -> None:
        """更新 index.md。"""
        state = self._read_state()

        lines = ["# User Profile Wiki Index", ""]
        lines.append(f"> 最后更新: {state.get('last_update', 'N/A')}")
        lines.append(f"> 已处理会话: {state.get('processed_sessions', 0)}")
        lines.append(f"> Wiki 版本: {state.get('version', 1)}")
        lines.append("")

        # 交互类型表格
        lines.append("## 交互类型档案")
        lines.append("")
        lines.append("| 类型 | 会话数 |")
        lines.append("|-----|-------|")

        type_counts = state.get("type_counts", {})
        for type_name, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| [{type_name}](types/{type_name}.md) | {count} |")
        lines.append("")

        # 痛点摘要
        pain_counts = state.get("pain_point_counts", {})
        high_pains = [(k, v) for k, v in pain_counts.items() if v >= PAIN_MIN_COUNT]
        if high_pains:
            lines.append("## 已识别痛点")
            lines.append("")
            for pain_id, count in sorted(high_pains, key=lambda x: -x[1]):
                lines.append(f"- {pain_id} ({count}次)")
            lines.append("")

        (self._wiki_dir / "index.md").write_text("\n".join(lines))

    def _get_stats(self) -> Dict:
        """获取统计信息。"""
        return self._read_state()

    # -- Tool handlers -----------------------------------------------

    def _handle_wiki_recall(self, args: Dict) -> str:
        """处理 wiki_recall 工具。"""
        query = args.get("query", "")
        type_override = args.get("type")

        if type_override and self._type_page_exists(type_override):
            return json.dumps({
                "success": True,
                "type": type_override,
                "strategy": self._build_single_strategy(type_override),
            })

        result = self.prefetch(query)
        if not result:
            return json.dumps({"success": True, "strategy": ""})

        return json.dumps({"success": True, "strategy": result})

    def _handle_wiki_page(self, args: Dict) -> str:
        """处理 wiki_page 工具。"""
        page = args.get("page", "")

        if "/" not in page:
            page_path = self._wiki_dir / "types" / f"{page}.md"
        else:
            page_path = self._wiki_dir / page.replace("/", "/") + ".md"

        if not page_path.exists():
            return json.dumps({"success": False, "error": f"页面不存在: {page}"})

        try:
            content = page_path.read_text()
            return json.dumps({"success": True, "page": page, "content": content})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _handle_wiki_status(self, args: Dict) -> str:
        """处理 wiki_status 工具。"""
        state = self._read_state()

        return json.dumps({
            "success": True,
            "version": state.get("version", 0),
            "last_update": state.get("last_update"),
            "total_sessions": state.get("total_sessions", 0),
            "processed_sessions": state.get("processed_sessions", 0),
            "pending": len(state.get("pending_ids", [])),
            "types": list(state.get("type_counts", {}).keys()),
            "pain_points": list(state.get("pain_point_counts", {}).keys()),
        })


# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------

def register(ctx) -> None:
    """注册 Wiki Provider。"""
    provider = UserProfileWikiProvider()
    ctx.register_memory_provider(provider)