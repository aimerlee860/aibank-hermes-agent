# 工具规格输出格式

## 标准工具规格模板

每个工具规格包含以下字段：

```
工具名：[snake_case 英文名，与功能直接对应]
工具类型：[查询 | 操作]
功能描述：[一句话说明，20字以内]
业务域：[对应 domain-taxonomy.md 中的域名称]
优先级：[P0 / P1 / P2 / P3]

参数列表：
  必填参数：
    - 参数名 (类型): 说明，枚举值用「/」分隔
  可选参数：
    - 参数名 (类型, 默认值): 说明

特殊标记：[risk_confirm / 不可撤销 / 金额门控，无则省略]
触发信息收集：[操作类工具必须列出，执行前需向用户确认的信息清单]
```

---

## 示例：查询工具

```
工具名：exchange_rate_query
工具类型：查询
功能描述：查询外汇实时汇率
业务域：外汇业务
优先级：P1

参数列表：
  必填参数：
    - currency_pair (str): 货币对，如 USD/CNY、EUR/CNY、JPY/CNY
  可选参数：
    - rate_type (str, "现汇"): 汇率类型，现汇 / 现钞 / 中间价
```

---

## 示例：操作工具（含风险确认）

```
工具名：precious_metal_buy
工具类型：操作
功能描述：买入贵金属
业务域：贵金属
优先级：P2

参数列表：
  必填参数：
    - from_account (str): 扣款账户
    - metal_type (str): 金属种类，黄金 / 白银 / 铂金
    - amount (float): 克重（单位：克，非人民币）
    - risk_confirm (bool): 用户风险确认标志
  可选参数：
    - price_type (str, "市价"): 价格类型，市价 / 限价

特殊标记：risk_confirm — 投资风险
触发信息收集：金属种类、克重、扣款账户、价格类型
```

---

## 示例：操作工具（不可撤销）

```
工具名：cross_border_transfer
工具类型：操作
功能描述：跨境汇款（SWIFT）
业务域：外汇业务
优先级：P1

参数列表：
  必填参数：
    - from_account (str): 转出账户
    - to_bank (str): 收款行 SWIFT Code
    - to_account (str): 收款账号
    - to_name (str): 收款人姓名
    - currency (str): 汇款币种，如 USD、EUR
    - amount (float): 汇款金额
    - country (str): 目的国家

特殊标记：不可撤销 — user_confirm 中必须加粗提示
触发信息收集：转出账户、收款行SWIFT Code、收款账号、收款人姓名、币种、金额、目的国
```

---

## 批量输出格式

分析完成后，按以下结构输出完整的工具规格清单：

```markdown
## 新增工具规格清单

### 查询工具（共 N 个）

#### [业务域名称]
| 工具名 | 功能 | 必填参数 | 可选参数 | 特殊标记 |
|--------|------|---------|---------|---------|
| `tool_name` | 功能描述 | param1, param2 | param3(默认值) | — |

### 操作工具（共 N 个）

#### [业务域名称]
| 工具名 | 功能 | 必填参数 | 特殊标记 | 需收集信息 |
|--------|------|---------|---------|----------|
| `tool_name` | 功能描述 | param1, param2 | risk_confirm | 信息1、信息2 |
```

---

## 命名规范

| 模式 | 示例 |
|------|------|
| 查询：`{资源}_query` 或 `{资源}_list` | `balance_query`, `fund_list` |
| 持仓查询：`{资源}_holdings` | `forex_holdings_query`, `fund_holdings` |
| 行情查询：`{资源}_quote` | `precious_metal_quote` |
| 开立/申购：`{资源}_open` 或 `{资源}_buy` | `large_cd_open`, `fund_buy` |
| 支取/赎回：`{资源}_withdraw` 或 `{资源}_redeem` | `notice_deposit_withdraw`, `fund_redeem` |
| 买卖操作：`{资源}_buy` / `{资源}_sell` | `bond_buy`, `bond_sell` |
| 添加/删除：`{资源}_add` / `{资源}_delete` | `payee_add`, `payee_delete` |
| 申请：`{资源}_apply` | `card_apply`, `consumer_loan_apply` |
| 取消/注销：`{资源}_cancel` | `card_cancel` |

---

## risk_confirm 使用规则

以下业务域的**买入/购买/申购**操作必须包含 `risk_confirm: bool` 参数：

- 贵金属（买入）
- 债券（购买）
- 保险（购买）
- 基金（申购、转换）
- 理财产品（购买）
- 外汇买卖

Mock 层实现规则：`risk_confirm=False` 时返回 `{"success": false, "risk_warning": "⚠️ 投资有风险..."}` 而非执行操作，强制 Agent 先展示风险提示。
