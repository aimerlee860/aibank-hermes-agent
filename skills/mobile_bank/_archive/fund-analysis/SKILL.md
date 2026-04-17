---
name: fund-analysis
category: wealth
description: 协调多个专业分析师完成基金市场全面分析
allowed-tools:
  - market_timing_query
  - global_indices_query
  - sector_data_query
  - sector_funds_query
  - gold_price_query
  - financial_news_query
  - fund_nav_query
  - fund_list
  - stock_data_query
  - zhihu_hot_query
  - social_search_query
agents:
  - agents/market-analyst.md
  - agents/sector-expert.md
  - agents/risk-manager.md
  - agents/fund-picker.md
  - agents/report-writer.md
---

# 全面基金分析

## 执行流程

### 阶段1：并行分析（可同时执行）

**市场分析师**  详细分析请参阅 agents/market-analyst.md
- 分析市场趋势、技术形态、关键价位
- 输入：市场指数数据
- 输出：趋势分析报告

- **Multi-step processes**: See references/workflows.md for sequential workflows and conditional logic
- **Specific output formats or quality standards**: See references/output-patterns.md for templ

**板块专家**  详细分析请参阅 agents/sector-expert.md
- 分析板块轮动、资金流向、热点识别
- 输入：板块涨跌幅数据
- 输出：板块分析报告

**风险经理**  详细分析请参阅 agents/risk-manager.md
- 评估市场风险、波动率、相关性
- 输入：历史波动率数据
- 输出：风险评估报告

### 阶段2：基金选择（依赖阶段1）

**基金挑选员** 详细分析请参阅 agents/fund-picker.md
- 基于阶段1结果筛选基金
- 输入：阶段1所有报告
- 输出：基金推荐列表

### 阶段3：报告生成（依赖阶段2）

**报告撰写员**  详细分析请参阅 agents/report-writer.md
- 整合所有结果生成最终报告
- 输入：所有前序阶段输出
- 输出：完整分析报告

## 数据流

```
输入数据
    │
    ├──────┬──────┬──────┐
    │      │      │      │
    ▼      ▼      ▼      │
┌────────┐ ┌────────┐ ┌────────┐
│市场分析师│ │板块专家 │ │风险经理│
└────┬───┘ └────┬───┘ └────┬───┘
     │          │          │
     └────┬─────┴─────┬────┘
          │           │
          ▼           │
    ┌────────────┐    │
    │ 基金挑选员  │◄───┘
    └─────┬──────┘
          │
          ▼
    ┌────────────┐
    │ 报告撰写员  │
    └─────┬──────┘
          │
          ▼
    最终报告
```

## 输出要求

最终报告必须包含：
- 执行摘要
- 市场趋势分析
- 板块轮动分析
- 风险评估
- 基金推荐
- 风险提示
- 详细数据附录
