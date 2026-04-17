#!/usr/bin/env python3
"""
AI新闻聚合器脚本
用于收集、过滤和整理AI新闻
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List


class AINewsAggregator:
    """AI新闻聚合器类"""

    def __init__(self):
        self.categories = [
            "技术突破",
            "产品发布",
            "研究进展",
            "行业应用",
            "政策法规",
            "投资融资",
            "人物动态"
        ]

        # 权威AI新闻来源
        self.trusted_sources = [
            "mit.edu",
            "technologyreview.com",
            "wired.com",
            "techcrunch.com",
            "venturebeat.com",
            "theverge.com",
            "analyticsindiamag.com",
            "syncedreview.com",
            "ainews.com",
            "aitrends.com",
            "blog.google/ai",
            "openai.com/blog",
            "deepmind.com/blog",
            "microsoft.com/ai",
            "nvidia.com/blog"
        ]

    def categorize_news(self, title: str, content: str) -> str:
        """根据新闻标题和内容分类"""
        title_lower = title.lower()
        content_lower = content.lower()

        # 技术突破关键词
        tech_keywords = [
            "breakthrough", "innovation", "algorithm", "model", "architecture",
            "performance", "accuracy", "efficiency", "benchmark", "state-of-the-art",
            "突破", "创新", "算法", "模型", "架构", "性能", "准确率", "效率"
        ]

        # 产品发布关键词
        product_keywords = [
            "launch", "release", "announce", "product", "tool", "platform", "service",
            "beta", "version", "update", "feature",
            "发布", "推出", "宣布", "产品", "工具", "平台", "服务", "版本", "更新"
        ]

        # 研究进展关键词
        research_keywords = [
            "paper", "research", "study", "conference", "arxiv", "preprint",
            "academic", "scientific", "experiment", "finding",
            "论文", "研究", "学术", "会议", "实验", "发现"
        ]

        # 行业应用关键词
        application_keywords = [
            "application", "use case", "implementation", "deployment", "industry",
            "healthcare", "finance", "manufacturing", "retail", "education",
            "应用", "用例", "实施", "部署", "行业", "医疗", "金融", "制造", "零售", "教育"
        ]

        # 政策法规关键词
        policy_keywords = [
            "regulation", "policy", "law", "ethics", "governance", "compliance",
            "standard", "guideline", "framework",
            "监管", "政策", "法律", "伦理", "治理", "合规", "标准", "指南", "框架"
        ]

        # 投资融资关键词
        investment_keywords = [
            "funding", "investment", "venture", "capital", "series", "round",
            "acquisition", "merger", "startup", "valuation",
            "融资", "投资", "风投", "资本", "轮次", "收购", "合并", "初创", "估值"
        ]

        # 人物动态关键词
        people_keywords = [
            "appoint", "hire", "join", "leave", "founder", "CEO", "CTO",
            "researcher", "scientist", "expert",
            "任命", "聘请", "加入", "离开", "创始人", "首席执行官", "首席技术官", "研究员", "科学家", "专家"
        ]

        # 检查每个类别的关键词
        keyword_sets = [
            (tech_keywords, "技术突破"),
            (product_keywords, "产品发布"),
            (research_keywords, "研究进展"),
            (application_keywords, "行业应用"),
            (policy_keywords, "政策法规"),
            (investment_keywords, "投资融资"),
            (people_keywords, "人物动态")
        ]

        scores = {category: 0 for category in self.categories}

        for keywords, category in keyword_sets:
            for keyword in keywords:
                if keyword in title_lower or keyword in content_lower:
                    scores[category] += 1

        # 返回得分最高的类别
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        else:
            return "其他"

    def filter_news(self, news_items: List[Dict[str, Any]],
                   min_relevance_score: int = 3,
                   max_age_days: int = 7) -> List[Dict[str, Any]]:
        """过滤新闻项"""
        filtered_items = []

        for item in news_items:
            # 检查来源可信度
            source_trusted = any(source in item.get('source_url', '') for source in self.trusted_sources)

            # 检查时效性
            pub_date = item.get('pub_date', '')
            is_recent = self._check_recency(pub_date, max_age_days)

            # 检查相关性（简单评分）
            relevance_score = self._calculate_relevance_score(item)

            # 应用过滤条件
            if (source_trusted or relevance_score >= min_relevance_score) and is_recent:
                # 添加分类信息
                item['category'] = self.categorize_news(
                    item.get('title', ''),
                    item.get('summary', '')
                )
                filtered_items.append(item)

        return filtered_items

    def _check_recency(self, pub_date: str, max_age_days: int) -> bool:
        """检查新闻时效性"""
        if not pub_date:
            return True  # 如果没有日期信息，不过滤

        try:
            # 尝试解析日期
            date_formats = [
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%d %b %Y',
                '%B %d, %Y',
                '%Y-%m-%dT%H:%M:%S'
            ]

            pub_datetime = None
            for fmt in date_formats:
                try:
                    pub_datetime = datetime.strptime(pub_date[:19], fmt)
                    break
                except ValueError:
                    continue

            if pub_datetime:
                age = datetime.now() - pub_datetime
                return age.days <= max_age_days
            return True
        except:
            return True

    def _calculate_relevance_score(self, item: Dict[str, Any]) -> int:
        """计算新闻相关性评分"""
        score = 0

        title = item.get('title', '').lower()
        summary = item.get('summary', '').lower()

        # AI相关关键词
        ai_keywords = [
            "artificial intelligence", "ai", "machine learning", "ml",
            "deep learning", "neural network", "llm", "large language model",
            "generative ai", "computer vision", "nlp", "自然语言处理",
            "人工智能", "机器学习", "深度学习", "神经网络", "大语言模型"
        ]

        # 重要性关键词
        importance_keywords = [
            "breakthrough", "major", "significant", "important", "revolutionary",
            "game-changing", "transformative", "里程碑", "重大", "重要", "革命性"
        ]

        # 检查AI关键词
        for keyword in ai_keywords:
            if keyword in title or keyword in summary:
                score += 2

        # 检查重要性关键词
        for keyword in importance_keywords:
            if keyword in title or keyword in summary:
                score += 1

        return score

    def generate_briefing(self, news_items: List[Dict[str, Any]],
                         date: str = None) -> Dict[str, Any]:
        """生成新闻简报"""
        if not date:
            date = datetime.now().strftime('%Y年%m月%d日')

        # 按类别分组
        categorized_news = {category: [] for category in self.categories}
        categorized_news["其他"] = []

        for item in news_items:
            category = item.get('category', '其他')
            if category in categorized_news:
                categorized_news[category].append(item)
            else:
                categorized_news["其他"].append(item)

        # 生成简报结构
        briefing = {
            "title": f"AI新闻简报 {date}",
            "date": date,
            "summary": self._generate_overall_summary(news_items),
            "categories": {},
            "statistics": {
                "total_news": len(news_items),
                "by_category": {cat: len(items) for cat, items in categorized_news.items() if items},
                "sources": self._count_sources(news_items)
            },
            "trends": self._analyze_trends(news_items)
        }

        # 添加分类新闻
        for category, items in categorized_news.items():
            if items:
                briefing["categories"][category] = [
                    self._format_news_item(item) for item in items[:10]  # 每类最多10条
                ]

        return briefing

    def _generate_overall_summary(self, news_items: List[Dict[str, Any]]) -> str:
        """生成总体摘要"""
        if not news_items:
            return "今日未发现重要的AI新闻。"

        # 统计主要类别
        category_counts = {}
        for item in news_items:
            category = item.get('category', '其他')
            category_counts[category] = category_counts.get(category, 0) + 1

        # 找出最多的3个类别
        top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        summary_parts = []
        if top_categories:
            category_names = [cat for cat, _ in top_categories]
            summary_parts.append(f"今日AI新闻主要集中在{', '.join(category_names)}等领域。")

        # 检查是否有重大新闻
        major_news = [item for item in news_items if "breakthrough" in item.get('title', '').lower()
                     or "major" in item.get('title', '').lower()]

        if major_news:
            summary_parts.append(f"共发现{len(major_news)}条重要突破性新闻。")

        summary_parts.append(f"总计收集到{len(news_items)}条相关新闻。")

        return " ".join(summary_parts)

    def _format_news_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """格式化单个新闻项"""
        return {
            "title": item.get('title', ''),
            "summary": item.get('summary', ''),
            "key_points": self._extract_key_points(item),
            "source": item.get('source', ''),
            "source_url": item.get('source_url', ''),
            "article_url": item.get('url', ''),
            "pub_date": item.get('pub_date', ''),
            "category": item.get('category', '其他')
        }

    def _extract_key_points(self, item: Dict[str, Any]) -> List[str]:
        """提取关键要点"""
        # 这里可以添加更复杂的关键点提取逻辑
        # 目前返回简单的要点
        points = []

        title = item.get('title', '')
        summary = item.get('summary', '')

        # 简单的要点提取（实际应用中可以使用NLP技术）
        if "announce" in title.lower() or "发布" in title:
            points.append("新产品或服务发布")

        if "breakthrough" in title.lower() or "突破" in title:
            points.append("技术突破")

        if "research" in title.lower() or "研究" in title:
            points.append("研究进展")

        if len(points) < 3 and summary:
            # 从摘要中提取句子作为要点
            sentences = re.split(r'[.!?]+', summary)
            for sentence in sentences[:3]:
                if sentence.strip() and len(sentence.strip()) > 10:
                    points.append(sentence.strip())

        return points[:5]  # 最多5个要点

    def _count_sources(self, news_items: List[Dict[str, Any]]) -> Dict[str, int]:
        """统计新闻来源"""
        sources = {}
        for item in news_items:
            source = item.get('source', '未知')
            sources[source] = sources.get(source, 0) + 1
        return sources

    def _analyze_trends(self, news_items: List[Dict[str, Any]]) -> List[str]:
        """分析趋势"""
        trends = []

        # 分析热门话题
        all_text = " ".join([item.get('title', '') + " " + item.get('summary', '')
                           for item in news_items])

        # 简单的话题检测（实际应用中可以使用更复杂的技术）
        topics = {
            "大语言模型": ["llm", "large language model", "gpt", "大语言模型"],
            "生成式AI": ["generative ai", "genai", "生成式ai", "生成模型"],
            "多模态": ["multimodal", "多模态", "视觉语言"],
            "AI安全": ["ai safety", "alignment", "安全", "对齐"],
            "开源模型": ["open source", "开源", "hugging face"],
            "AI芯片": ["ai chip", "gpu", "npu", "芯片", "硬件"]
        }

        for topic, keywords in topics.items():
            count = sum(1 for keyword in keywords if keyword.lower() in all_text.lower())
            if count >= 3:  # 至少出现3次
                trends.append(f"{topic}是当前热点话题")

        if not trends:
            trends.append("今日新闻未显示明显的集中趋势")

        return trends

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AI新闻聚合器')
    parser.add_argument('--input', type=str, help='输入JSON文件路径')
    parser.add_argument('--output', type=str, default='ai_news_briefing.json',
                       help='输出JSON文件路径')
    parser.add_argument('--max-age', type=int, default=7,
                       help='最大新闻天数（默认7天）')
    parser.add_argument('--min-relevance', type=int, default=3,
                       help='最小相关性评分（默认3）')

    args = parser.parse_args()

    # 创建聚合器
    aggregator = AINewsAggregator()

    # 读取输入数据
    if args.input:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                news_data = json.load(f)
        except FileNotFoundError:
            print(f"错误：找不到输入文件 {args.input}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"错误：输入文件 {args.input} 不是有效的JSON格式")
            sys.exit(1)
    else:
        # 如果没有输入文件，使用示例数据
        print("警告：未提供输入文件，使用示例数据")
        news_data = [
            {
                "title": "OpenAI发布新一代语言模型",
                "summary": "OpenAI今日发布了其最新的大型语言模型，在多项基准测试中表现优异。",
                "source": "OpenAI Blog",
                "source_url": "openai.com",
                "url": "https://openai.com/blog/new-model",
                "pub_date": datetime.now().strftime('%Y-%m-%d')
            }
        ]

    # 过滤新闻
    filtered_news = aggregator.filter_news(
        news_data,
        min_relevance_score=args.min_relevance,
        max_age_days=args.max_age
    )

    # 生成简报
    briefing = aggregator.generate_briefing(filtered_news)

    # 输出结果
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(briefing, f, ensure_ascii=False, indent=2)

    print(f"简报已生成：{args.output}")
    print(f"处理新闻数：{len(news_data)} → 过滤后：{len(filtered_news)}")
    print(f"分类统计：{briefing['statistics']['by_category']}")

if __name__ == "__main__":
    main()
