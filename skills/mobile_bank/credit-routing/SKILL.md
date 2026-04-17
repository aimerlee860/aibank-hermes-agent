---
name: credit-routing
category: routing
version: 1.0.0
status: production
description: 信用卡域路由决策指南。当用户请求涉及信用卡账单、还款、分期、额度等场景时，帮助 main-agent 选择最优 wf_* 工作流，避免重复调用原子工具。
workflows:
  - wf_credit_card_repay
  - wf_credit_card_bill_analysis
  - wf_credit_limit_temp_raise
  - wf_bill_installment_plan
  - wf_cash_advance
  - wf_credit_card_full_service
---

# 信用卡域路由决策指南

## wf_* 选择矩阵

| 用户意图 | 正确路由 | 禁止 |
|---------|---------|------|
| 查单期账单 | task(credit-agent) → credit_card_bill | — |
| 多期账单分析 | wf_credit_card_bill_analysis（自动并行查多期+额度） | 循环调 credit_card_bill |
| 还信用卡 | wf_credit_card_repay（参数全可选，自动识别卡号和金额） | — |
| 分析账单+制定还款计划 | wf_credit_card_bill_analysis → wf_credit_card_repay（复用前者数据） | 两个 wf 都查账单 |
| 账单分期 | wf_bill_installment_plan | — |
| 临时提额 | wf_credit_limit_temp_raise | — |
| 信用卡综合查询 | wf_credit_card_full_service（账单+额度并行） | 分别查 bill + limit |

## 效率规则

1. 同一张卡的账单数据只查一次，跨 wf_* 复用结果
2. wf_credit_card_bill_analysis 内部已并行查询多期账单，不要在外层再包循环
3. wf_credit_card_repay 所有参数均可选——"帮我还信用卡"直接调用即可，工作流自动识别卡号和全额账单金额
