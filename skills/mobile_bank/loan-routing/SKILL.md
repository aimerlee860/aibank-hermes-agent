---
name: loan-routing
category: routing
version: 1.0.0
status: production
description: 贷款域路由决策指南。当用户请求涉及贷款查询、房贷还款、消费贷申请等场景时，帮助 main-agent 选择最优 wf_* 工作流，避免重复调用原子工具。
workflows:
  - wf_loan_overview
  - wf_mortgage_repayment_plan
  - wf_consumer_loan_apply
  - wf_loan_repayment
---

# 贷款域路由决策指南

## wf_* 选择矩阵

| 用户意图 | 正确路由 | 禁止 |
|---------|---------|------|
| 查所有贷款 | wf_loan_overview（loan_query 已含全类型，并行查房贷+消费贷详情） | 分别调 consumer/mortgage/car_loan_query |
| 房贷提前还款 | wf_mortgage_repayment_plan | — |
| 申请消费贷 | wf_consumer_loan_apply（含现有贷款查询） | 直接调 consumer_loan_apply |
| 贷款还款 | wf_loan_repayment（含贷款信息确认） | 直接调 loan_repayment |
| 对比贷款利率 | task(credit-agent) 查 loan_query(全部) → 直接分析对比 | expand_intent |
| 分析贷款+提前还款 | wf_loan_overview 查询 → wf_mortgage_repayment_plan 执行 | expand_intent |

## 效率规则

1. loan_query(loan_type="全部") 一次返回所有贷款类型（房贷/车贷/消费贷/经营贷），不要额外调用 consumer_loan_query/car_loan_query 等专项查询
2. 贷款分析属于单域请求，不需要 expand_intent
3. wf_loan_overview 内部已并行查询三种贷款，不要在外层串行调用
