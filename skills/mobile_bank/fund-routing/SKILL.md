---
name: fund-routing
category: routing
version: 1.0.0
status: production
description: 基金/理财域路由决策指南。当用户请求涉及基金买卖、理财产品、资产配置、市场行情等场景时，帮助 main-agent 选择最优 wf_* 工作流，避免重复调用原子工具。
workflows:
  - wf_fund_buy_guided
  - wf_fund_redeem
  - wf_fund_switch
  - wf_wealth_product_buy
  - wf_wealth_product_redeem
  - wf_icbc_wealth_buy
  - wf_wealth_overview
  - wf_market_and_wealth_analysis
  - wf_financial_health_check
  - wf_fixed_deposit_open
  - wf_fixed_deposit_withdraw
  - wf_large_cd_open
  - wf_forex_buy_guided
  - wf_precious_metal_buy
  - wf_precious_metal_sell
---

# 基金/理财域路由决策指南

## wf_* 选择矩阵

| 用户意图 | 正确路由 | 禁止 |
|---------|---------|------|
| 买基金 | wf_fund_buy_guided（含列表+持仓+购买） | 分步调 fund_list → fund_buy |
| 赎回基金 | wf_fund_redeem（含持仓确认） | 直接调 fund_redeem |
| 基金转换 | wf_fund_switch | — |
| 财富总览 | wf_wealth_overview（理财+基金+定存并行） | 逐个调 holdings |
| 市场行情+持仓分析 | wf_market_and_wealth_analysis（5 工具并行） | 逐个调 indices/sectors/news |
| 财务健康检查 | wf_financial_health_check（余额+贷款+理财并行） | 分步查询 |
| 买理财产品 | wf_wealth_product_buy（含列表+持仓+购买） | — |
| 赎回理财产品 | wf_wealth_product_redeem | — |
| 资产配置建议 | wf_wealth_overview + wf_market_and_wealth_analysis（纯查询） | expand_intent |
| 定存开立/支取 | wf_fixed_deposit_open / wf_fixed_deposit_withdraw | — |
| 购汇 | wf_forex_buy_guided（含汇率查询） | 分步查汇率再购汇 |
| 贵金属买卖 | wf_precious_metal_buy / wf_precious_metal_sell（含行情） | 分步查行情再交易 |

## 效率规则

1. wf_* 内部已做 asyncio.gather 并行，不要在外层再包循环
2. 资产配置类请求属于单域分析，使用 wf_wealth_overview + wf_market_and_wealth_analysis 即可，不需要 expand_intent
3. financial_holdings 被 5 个 wf_* 共用，通过 wf_* 调用即可获取，不要单独调用
