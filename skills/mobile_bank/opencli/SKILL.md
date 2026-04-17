---
name: opencli
category: wealth
version: 1.0.0
status: production
description: 社交平台舆情数据技能，提供知乎热榜、B站热门、知乎搜索，用于补充基金/股票分析的市场情绪维度
allowed-tools:
  - zhihu_hot_query
  - bilibili_hot_query
  - social_search_query
---

# 社交舆情数据

## 工具说明

| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `zhihu_hot_query` | 知乎热榜话题（最多10条） | limit（默认5） |
| `bilibili_hot_query` | B站热门视频（最多10条） | limit（默认5） |
| `social_search_query` | 知乎关键词搜索（最多10条） | platform=zhihu, query, limit（默认5） |

## 使用原则

- 默认 limit=5，避免过多内容撑大上下文
- `social_search_query` 当前仅支持 `platform=zhihu`
- 工具结果作为「市场情绪参考」，不作为决策依据
- 若工具返回空列表（`[]`），说明 opencli 当前不可用，直接跳过舆情分析，不影响主流程

## 适用场景

- 分析基金/股票时，补充「市场情绪」维度
- 识别当前热点话题与持仓基金的相关性
- 辅助判断板块资金流向的舆情背景
