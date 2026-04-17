#!/usr/bin/env python3
"""
测试AI新闻聚合器
"""

import json
import os
import sys
from datetime import datetime

# 添加脚本目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_news_aggregator import AINewsAggregator


def test_basic_functionality():
    """测试基本功能"""
    print("=== 测试AI新闻聚合器基本功能 ===")

    # 创建聚合器实例
    aggregator = AINewsAggregator()

    # 测试分类功能
    test_cases = [
        {
            "title": "OpenAI发布新一代语言模型突破",
            "content": "OpenAI发布了新的语言模型，在多项基准测试中取得突破性进展",
            "expected": "技术突破"
        },
        {
            "title": "Google推出AI芯片新产品",
            "content": "Google发布了新的AI芯片，性能大幅提升",
            "expected": "产品发布"
        },
        {
            "title": "DeepMind在Nature发表研究论文",
            "content": "DeepMind的研究团队在Nature期刊上发表了新的AI研究论文",
            "expected": "研究进展"
        },
        {
            "title": "AI在医疗诊断中的应用案例",
            "content": "医院成功应用AI系统进行疾病诊断",
            "expected": "行业应用"
        }
    ]

    print("\n1. 测试新闻分类功能：")
    for i, test_case in enumerate(test_cases, 1):
        category = aggregator.categorize_news(test_case["title"], test_case["content"])
        status = "✓" if category == test_case["expected"] else "✗"
        print(f"   {status} 测试{i}: '{test_case['title']}' → 分类: {category} (预期: {test_case['expected']})")

    # 测试过滤功能
    print("\n2. 测试新闻过滤功能：")

    # 创建测试数据
    test_news = [
        {
            "title": "重要AI突破新闻",
            "summary": "这是一条重要的AI突破性新闻",
            "source": "OpenAI Blog",
            "source_url": "openai.com",
            "url": "https://example.com",
            "pub_date": datetime.now().strftime('%Y-%m-%d')
        },
        {
            "title": "旧新闻测试",
            "summary": "这是一条旧的测试新闻",
            "source": "Test Source",
            "source_url": "test.com",
            "url": "https://example.com",
            "pub_date": "2023-01-01"  # 超过7天
        },
        {
            "title": "低相关性新闻",
            "summary": "这是一条与AI无关的新闻",
            "source": "Other Source",
            "source_url": "other.com",
            "url": "https://example.com",
            "pub_date": datetime.now().strftime('%Y-%m-%d')
        }
    ]

    filtered = aggregator.filter_news(test_news, min_relevance_score=3, max_age_days=7)
    print(f"   输入新闻数: {len(test_news)}")
    print(f"   过滤后新闻数: {len(filtered)}")
    print(f"   过滤掉的新闻: {len(test_news) - len(filtered)}")

    # 测试简报生成
    print("\n3. 测试简报生成功能：")
    if filtered:
        briefing = aggregator.generate_briefing(filtered)
        print(f"   简报标题: {briefing['title']}")
        print(f"   总体摘要: {briefing['summary']}")
        print(f"   统计信息: {briefing['statistics']}")

        # 检查分类
        print(f"   新闻分类: {briefing['statistics']['by_category']}")

        # 检查趋势分析
        if briefing['trends']:
            print(f"   趋势分析: {briefing['trends']}")
    else:
        print("   没有足够的新闻生成简报")

    return True

def test_with_sample_data():
    """使用示例数据测试"""
    print("\n=== 使用示例数据测试 ===")

    # 加载示例数据
    sample_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'sample_news_data.json')

    try:
        with open(sample_file, 'r', encoding='utf-8') as f:
            sample_data = json.load(f)

        print(f"加载示例数据: {len(sample_data)} 条新闻")

        # 创建聚合器
        aggregator = AINewsAggregator()

        # 过滤新闻
        filtered = aggregator.filter_news(sample_data)
        print(f"过滤后新闻数: {len(filtered)}")

        # 生成简报
        briefing = aggregator.generate_briefing(filtered)

        # 输出简报摘要
        print(f"\n简报标题: {briefing['title']}")
        print(f"总体摘要: {briefing['summary']}")

        # 输出分类统计
        print("\n分类统计:")
        for category, count in briefing['statistics']['by_category'].items():
            print(f"  {category}: {count} 条")

        # 输出来源统计
        print("\n来源统计:")
        for source, count in briefing['statistics']['sources'].items():
            print(f"  {source}: {count} 条")

        # 输出趋势
        print("\n趋势分析:")
        for trend in briefing['trends']:
            print(f"  • {trend}")

        # 保存简报到文件
        output_file = os.path.join(os.path.dirname(__file__), 'test_briefing.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(briefing, f, ensure_ascii=False, indent=2)

        print(f"\n简报已保存到: {output_file}")

        # 生成Markdown格式简报
        md_file = os.path.join(os.path.dirname(__file__), 'test_briefing.md')
        generate_markdown_briefing(briefing, md_file)

        return True

    except FileNotFoundError:
        print(f"错误: 找不到示例文件 {sample_file}")
        return False
    except json.JSONDecodeError:
        print("错误: 示例文件格式错误")
        return False

def generate_markdown_briefing(briefing: dict, output_file: str):
    """生成Markdown格式简报"""
    with open(output_file, 'w', encoding='utf-8') as f:
        # 标题
        f.write(f"# {briefing['title']}\n\n")

        # 摘要
        f.write("## 摘要概览\n")
        f.write(f"{briefing['summary']}\n\n")

        # 分类新闻
        for category, items in briefing['categories'].items():
            if items:
                f.write(f"## {category}\n")
                for item in items:
                    f.write(f"### {item['title']}\n")
                    f.write(f"- 摘要：{item['summary']}\n")

                    if item['key_points']:
                        f.write("- 关键要点：\n")
                        for point in item['key_points']:
                            f.write(f"  1. {point}\n")

                    f.write(f"- 来源：{item['source']}\n")
                    f.write(f"- 链接：{item['article_url']}\n")
                    if item['pub_date']:
                        f.write(f"- 时间：{item['pub_date']}\n")
                    f.write("\n")

        # 趋势分析
        if briefing['trends']:
            f.write("## 总结与趋势\n")
            for trend in briefing['trends']:
                f.write(f"- {trend}\n")
            f.write("\n")

        # 统计信息
        f.write("## 统计信息\n")
        f.write(f"- 总计新闻：{briefing['statistics']['total_news']}条\n")

        f.write("- 按类别分布：\n")
        for category, count in briefing['statistics']['by_category'].items():
            f.write(f"  - {category}：{count}条\n")

        f.write("- 来源分布：\n")
        for source, count in briefing['statistics']['sources'].items():
            f.write(f"  - {source}：{count}条\n")

        # 免责声明
        f.write("\n---\n")
        f.write("*免责声明：本简报基于公开网络信息聚合生成，信息来源包括多个权威AI新闻网站。内容仅供参考，不构成任何投资或决策建议。请通过原始链接核实具体信息。*\n")

    print(f"Markdown简报已保存到: {output_file}")

def main():
    """主测试函数"""
    print("开始测试Daily AI News技能...")

    # 测试基本功能
    if not test_basic_functionality():
        print("基本功能测试失败")
        return 1

    # 使用示例数据测试
    if not test_with_sample_data():
        print("示例数据测试失败")
        return 1

    print("\n=== 所有测试通过 ===")
    print("技能功能正常，可以投入使用。")

    return 0

if __name__ == "__main__":
    sys.exit(main())
