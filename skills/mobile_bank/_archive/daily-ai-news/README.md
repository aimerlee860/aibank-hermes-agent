# Daily AI News Skill

## 概述
Daily AI News技能是一个专业的AI新闻聚合器，用于收集、过滤、分类和总结来自多个权威来源的最新人工智能新闻。该技能按照信息收集→内容过滤→分类整理→输出格式化的四步流程执行，提供简洁的新闻简报并附带原始文章链接。

## 功能特点

### 1. 多源信息收集
- 从业界权威的AI新闻网站收集信息
- 支持英文和中文新闻源
- 包括技术媒体、研究博客、行业新闻等

### 2. 智能内容过滤
- 基于来源可信度的质量筛选
- 时效性检查（可配置时间范围）
- 相关性评分系统
- 自动排除低质量内容

### 3. 自动分类整理
- 7个主要分类：技术突破、产品发布、研究进展、行业应用、政策法规、投资融资、人物动态
- 基于关键词的智能分类
- 支持中英文混合内容

### 4. 结构化输出
- 生成JSON格式的结构化简报
- 支持Markdown格式的可读简报
- 包含统计信息和趋势分析
- 附带原始文章链接和来源信息

## 文件结构

```
daily-ai-news/
├── SKILL.md                    # 技能详细说明文档
├── scripts/
│   ├── ai_news_aggregator.py   # 主聚合器脚本
│   ├── config.json             # 配置文件（新闻源、关键词等）
│   └── test_aggregator.py      # 测试脚本
└── examples/
    ├── sample_news_data.json   # 示例新闻数据
    └── usage_example.md        # 使用示例
```

## 快速开始

### 基本使用

```python
import json
from ai_news_aggregator import AINewsAggregator

# 创建聚合器
aggregator = AINewsAggregator()

# 加载新闻数据
with open('news_data.json', 'r', encoding='utf-8') as f:
    news_data = json.load(f)

# 过滤新闻
filtered_news = aggregator.filter_news(news_data)

# 生成简报
briefing = aggregator.generate_briefing(filtered_news)

# 输出结果
print(f"简报标题: {briefing['title']}")
print(f"新闻数量: {briefing['statistics']['total_news']}")
```

### 命令行使用

```bash
# 处理新闻数据并生成简报
python ai_news_aggregator.py --input news_data.json --output briefing.json

# 自定义过滤参数
python ai_news_aggregator.py --input news_data.json --output briefing.json --max-age 3 --min-relevance 4
```

## 配置说明

### 新闻源配置
在 `config.json` 中可以配置：
- 主要新闻源（英文技术媒体）
- 研究博客（公司官方博客）
- 中文新闻源
- 搜索关键词
- 过滤参数

### 分类关键词
系统使用关键词匹配进行新闻分类，支持：
- 技术突破：breakthrough, innovation, algorithm, 突破, 创新
- 产品发布：launch, release, product, 发布, 推出
- 研究进展：paper, research, study, 论文, 研究
- 行业应用：application, use case, industry, 应用, 行业
- 政策法规：regulation, policy, law, 监管, 政策
- 投资融资：funding, investment, venture, 融资, 投资
- 人物动态：appoint, hire, join, 任命, 聘请

## 工作流程

### 步骤1：信息收集
1. 使用task工具委托子agent进行网络搜索
2. 并行搜索多个权威AI新闻网站
3. 收集新闻标题、摘要、链接、发布时间等信息

### 步骤2：内容过滤
1. 检查来源可信度
2. 验证时效性（默认最近7天）
3. 计算相关性评分
4. 排除低质量内容

### 步骤3：分类整理
1. 基于关键词进行自动分类
2. 按7个主要类别组织新闻
3. 提取关键要点

### 步骤4：输出格式化
1. 生成结构化简报
2. 添加统计信息
3. 分析趋势
4. 包含免责声明

## 输出格式

### JSON格式简报
```json
{
  "title": "AI新闻简报 2024-01-15",
  "date": "2024-01-15",
  "summary": "今日AI新闻主要集中在技术突破、产品发布等领域...",
  "categories": {
    "技术突破": [
      {
        "title": "新闻标题",
        "summary": "新闻摘要",
        "key_points": ["要点1", "要点2"],
        "source": "来源网站",
        "article_url": "原始链接",
        "pub_date": "发布时间"
      }
    ]
  },
  "statistics": {
    "total_news": 12,
    "by_category": {"技术突破": 3, "产品发布": 2},
    "sources": {"OpenAI Blog": 1, "TechCrunch": 2}
  },
  "trends": ["大语言模型是当前热点话题", "生成式AI加速应用"]
}
```

### Markdown格式简报
```markdown
# AI新闻简报 2024年1月15日

## 摘要概览
今日AI新闻主要集中在技术突破、产品发布、研究进展等领域...

## 技术突破
### OpenAI发布新一代多模态语言模型
- 摘要：OpenAI发布了最新的大型语言模型...
- 关键要点：
  1. 新一代多模态语言模型发布
  2. 视觉推理能力显著提升
- 来源：OpenAI Blog
- 链接：https://openai.com/blog/gpt-4-5
- 时间：2024-01-15

## 统计信息
- 总计新闻：12条
- 按类别分布：
  - 技术突破：3条
  - 产品发布：2条
```

## 测试验证

运行测试脚本验证功能：
```bash
python test_aggregator.py
```

测试内容包括：
1. 基本功能测试（分类、过滤、简报生成）
2. 示例数据测试
3. 边界条件测试

## 扩展开发

### 添加新的新闻源
1. 在 `config.json` 的 `news_sources` 部分添加新源
2. 配置名称、URL、类型、语言和可信度等级

### 自定义分类关键词
1. 修改 `ai_news_aggregator.py` 中的关键词列表
2. 添加新的分类类别和对应关键词

### 集成网络爬取
1. 实现网络爬取功能获取实时新闻
2. 使用WebSearch工具进行网络搜索
3. 添加HTML解析和内容提取

## 注意事项

1. **免责声明**：所有输出必须包含免责声明，明确说明信息来源仅供参考
2. **时效性**：明确标注新闻的时间范围和数据时效性
3. **版权尊重**：必须提供原始链接，尊重内容版权
4. **质量保证**：定期评估和更新新闻源列表
5. **用户定制**：支持用户自定义新闻源、关键词和时间范围

## 性能优化建议

1. **并行处理**：对于多个新闻源，使用并行任务同时搜索
2. **缓存机制**：实现缓存减少重复请求
3. **增量更新**：只获取最新的新闻内容
4. **错误处理**：完善的错误处理和重试机制

## 许可证

本技能遵循开源协议，可用于个人和商业项目。