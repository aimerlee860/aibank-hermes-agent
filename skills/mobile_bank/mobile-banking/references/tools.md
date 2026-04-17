# 工具清单

## 主 Agent 可用工具（MAIN_AGENT_TOOLS）

包含以下所有查询类工具 + 操作类工具。

---

## 查询类工具（主 Agent / 子 Agent 均可用）

### 账户类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `account_list` | 查询名下所有账户 | `include_frozen`（是/否） |
| `balance_query` | 查询账户余额 | `account_type`（储蓄卡/工资卡等）, `currency`（默认CNY） |
| `transaction_history` | 查询交易明细 | `account_type`, `time_range`（最近7天/30天等）, `transaction_type`（可选）, `amount_min/max`（可选） |

### 信用卡类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `credit_card_bill` | 查询信用卡账单 | `card_suffix`（后四位）, `bill_type`, `bill_month`（可选） |
| `credit_limit_query` | 查询信用卡额度 | `card_suffix`, `limit_type`（默认全部） |

### 定期存款类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `fixed_deposit_query` | 查询定期存款 | `account_type`（默认全部） |

### 贷款类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `loan_query` | 查询贷款信息（综合） | `loan_type`（默认全部） |
| `consumer_loan_query` | 查询消费贷款 | `loan_account`（可选） |
| `mortgage_balance_query` | 查询房贷余额 | `mortgage_account`（可选） |
| `mortgage_repayment_plan` | 查询房贷还款计划 | `mortgage_account` |
| `business_loan_query` | 查询经营贷款 | `loan_account`（可选） |
| `car_loan_query` | 查询车贷 | `loan_account`（可选） |

### 理财类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `financial_product_list` | 查询可购买理财产品 | `product_type`（可选）, `risk_level`（可选）, `min_amount`（可选）, `term`（可选） |
| `financial_holdings` | 查询理财持仓 | `product_type`（默认全部）, `status`（默认持有中） |

### 积分 / 股票类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `points_query` | 查询积分 | `card_type`（默认信用卡） |
| `stock_data_query` | 查询股票历史数据 | `symbol`（6位代码）, `period`（daily/weekly/monthly）, `start_date/end_date`（可选） |

---

## 操作类工具（仅主 Agent 可用，执行前必须 user_confirm）

### 转账类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `internal_transfer` | 行内转账 | `from_account`, `to_account`, `amount`, `currency`（默认CNY）, `remark`（可选） |
| `interbank_transfer` | 跨行转账 | `from_account`, `to_bank`, `to_account`, `amount`, `currency`（默认CNY） |
| `mobile_transfer` | 手机号转账 | `from_account`, `to_mobile`, `amount` |

### 理财操作类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `financial_product_buy` | 购买理财产品 | `product_id`, `amount`, `account_type`（默认储蓄卡）, `risk_confirm`（默认False） |
| `financial_product_redeem` | 赎回理财产品 | `product_id`, `amount`（可选，全额赎回时不填）, `account_type` |

### 信用卡操作类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `credit_card_repay` | 信用卡还款 | `card_suffix`, `amount`, `account_type`（默认储蓄卡） |
| `credit_limit_adjust` | 临时额度调整 | `card_suffix`, `adjust_amount`, `valid_days`, `reason` |
| `bill_installment` | 账单分期 | `card_suffix`, `installment_amount`, `installment_periods` |

### 定期存款操作类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `fixed_deposit_open` | 开立定期存款 | `from_account`, `amount`, `term`, `interest_method`（默认到期取息）, `auto_renew`（默认否） |
| `fixed_deposit_withdraw` | 支取定期存款 | `deposit_id`, `withdraw_type`, `to_account`, `withdraw_amount`（可选） |

### 贷款操作类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `loan_repayment` | 贷款还款 | `loan_account`, `repayment_amount`, `from_account` |
| `consumer_loan_apply` | 申请消费贷款 | `loan_amount`, `loan_term`, `loan_purpose`, `from_account` |
| `mortgage_prepayment_appointment` | 房贷提前还款预约 | `mortgage_account`, `prepayment_amount`, `prepayment_date`, `from_account` |
| `business_loan_apply` | 申请经营贷款 | `loan_amount`, `loan_term`, `business_type`, `from_account` |
| `car_loan_apply` | 申请车贷 | `car_price`, `down_payment`, `loan_term`, `from_account` |

### 积分操作类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `points_exchange` | 积分兑换 | `points`, `exchange_item`, `from_account` |

### 生活服务类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `utility_payment` | 生活缴费（水电气等） | `payment_type`, `payment_region`, `payment_company`, `account_number`, `from_account` |
| `mobile_recharge` | 手机话费充值 | `mobile_number`, `recharge_amount`, `from_account` |
| `bus_card_recharge` | 公交卡充值 | `card_number`, `recharge_amount`, `from_account` |
| `metro_qr_code` | 地铁乘车码 | `city`, `from_account` |
| `taxi_booking` | 打车服务 | `departure`, `destination`, `booking_time`（可选） |
| `train_ticket_booking` | 火车票预订 | `departure_station`, `arrival_station`, `departure_date`, `seat_type`（默认二等座）, `passenger_count` |

### 购物消费类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `ecommerce_platform_connect` | 电商平台绑定 | `platform`, `account` |
| `coupon_receive` | 优惠券领取 | `coupon_type`, `coupon_amount`, `conditions` |
| `movie_ticket_booking` | 电影票预订 | `movie_name`, `cinema`, `show_time`, `seat_count`（默认2） |
| `food_delivery_order` | 外卖订单 | `restaurant`, `dishes`, `delivery_address` |

### 政务 / 医疗类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `social_security_query` | 社保查询 | `person_name`, `id_number` |
| `tax_payment` | 税务申报 | `tax_type`, `tax_amount`, `from_account` |
| `fine_payment` | 罚款缴纳 | `fine_type`, `fine_number`, `fine_amount`, `from_account` |
| `hospital_registration` | 医院挂号 | `hospital`, `department`, `doctor`（可选）, `registration_date` |
| `medical_consultation` | 在线问诊 | `symptoms`, `duration`, `medical_history`（可选） |
| `medical_insurance_payment` | 医保支付 | `hospital`, `medical_type`, `amount`, `from_account` |

### 账户安全类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `transaction_limit_set` | 设置交易限额 | `account`, `limit_type`, `limit_amount` |
| `quick_pay_manage` | 快捷支付管理 | `operation`, `from_account` |
| `password_change` | 密码修改 | `account`, `password_type` |
| `account_loss_report` | 账户挂失 | `account`, `loss_reason` |

### 外汇类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `exchange_rate_query` | 查询外汇汇率 | `currency_pair`（USD/CNY等）, `rate_type`（现汇/现钞/中间价） |
| `forex_holdings_query` | 外汇持仓查询 | `currency`（可选）, `account_type`（默认全部） |
| `forex_buy` | 个人购汇（人民币→外币） | `from_account`, `to_account`, `currency`, `amount` |
| `forex_settle` | 个人结汇（外币→人民币） | `from_account`, `to_account`, `currency`, `amount` |
| `forex_trade` | 外汇买卖（外币互换） | `from_account`, `from_currency`, `to_currency`, `amount` |
| `cross_border_transfer` | 跨境汇款 | `from_account`, `to_bank`, `to_account`, `to_name`, `currency`, `amount`, `country` |

### 贵金属类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `precious_metal_quote` | 贵金属行情查询 | `metal_type`（黄金/白银/铂金/全部）, `quote_type`（实时/历史） |
| `precious_metal_holdings` | 贵金属持仓查询 | `metal_type`（默认全部） |
| `precious_metal_buy` | 贵金属买入 | `from_account`, `metal_type`, `amount`（克）, `price_type`, `risk_confirm` |
| `precious_metal_sell` | 贵金属卖出 | `metal_type`, `amount`（克）, `to_account`, `price_type` |

### 债券类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `bond_list` | 可购债券产品查询 | `bond_type`（可选）, `term`（可选） |
| `bond_holdings` | 债券持仓查询 | `bond_type`（默认全部）, `status`（默认持有中） |
| `bond_buy` | 购买债券 | `product_id`, `amount`, `from_account`, `risk_confirm` |
| `bond_sell` | 卖出债券 | `product_id`, `to_account`, `amount`（可选，默认全部） |

### 保险类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `insurance_product_list` | 保险产品查询 | `insurance_type`（可选）, `premium_max`（可选） |
| `insurance_holdings` | 我的保险（保单）查询 | `status`（默认生效中） |
| `insurance_buy` | 购买保险 | `product_id`, `insured_name`, `insured_id`, `coverage_period`, `payment_period`, `from_account`, `risk_confirm` |

### 通知存款类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `notice_deposit_query` | 通知存款查询 | `account_type`（一天通知/七天通知/全部） |
| `notice_deposit_open` | 开立通知存款 | `from_account`, `amount`, `notice_type`（一天通知/七天通知） |
| `notice_deposit_withdraw` | 支取通知存款 | `deposit_id`, `to_account`, `withdraw_amount`（可选） |

### 大额存单类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `large_cd_query` | 大额存单查询 | `status`（默认全部） |
| `large_cd_open` | 开立大额存单（≥20万） | `from_account`, `amount`, `term`, `interest_method` |
| `large_cd_withdraw` | 支取大额存单 | `cd_id`, `to_account`, `withdraw_type`（到期/提前） |

### 收款方管理类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `payee_list` | 注册收款方查询 | `payee_type`（全部/行内/跨行） |
| `payee_add` | 添加收款方 | `payee_name`, `payee_bank`, `payee_account`, `payee_type` |
| `payee_delete` | 删除收款方 | `payee_id` |

### 信用卡取现类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `credit_card_cash_advance_query` | 信用卡取现记录查询 | `card_suffix`, `time_range`（默认最近30天） |
| `credit_card_cash_advance` | 信用卡取现 | `card_suffix`, `amount`, `to_account` |
| `cash_advance_installment` | 取现分期 | `card_suffix`, `advance_id`, `installment_periods`（3/6/12） |

### 工银i豆类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `ibean_query` | 工银i豆余额查询 | 无必填参数 |
| `ibean_exchange` | 工银i豆兑换 | `ibean_count`, `exchange_item`, `exchange_category`（商城/话费/航空里程） |

### 基金类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `fund_list` | 可购基金产品查询 | `fund_type`（混合型/股票型/债券型/货币型，可选）, `risk_level`（可选）, `min_amount`（可选） |
| `fund_nav_query` | 基金净值查询 | `fund_code`（6位基金代码） |
| `fund_holdings` | 基金持仓查询 | `status`（默认持有中） |
| `fund_buy` | 申购基金 | `fund_code`, `amount`, `from_account`, `risk_confirm` |
| `fund_redeem` | 赎回基金 | `fund_code`, `to_account`, `redeem_share`（可选，None=全额） |
| `fund_transfer` | 基金转换（基金间互转） | `from_fund_code`, `to_fund_code`, `transfer_share`, `risk_confirm` |

### 工银理财类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `icbc_wealth_product_list` | 工银理财专属产品查询 | `product_type`（固定收益类/混合类/现金管理类，可选）, `risk_level`（可选） |
| `icbc_wealth_holdings` | 工银理财持仓查询 | `status`（默认持有中） |
| `icbc_wealth_buy` | 购买工银理财产品 | `product_id`, `amount`, `from_account`, `risk_confirm` |

### 征信查询类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `credit_report_query` | 央行征信报告查询 | `person_name`, `id_number`, `query_purpose`（默认本人查询） |

### 银行卡管理类
| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `card_status_query` | 名下银行卡状态查询 | `card_type`（借记卡/信用卡/全部） |
| `card_apply` | 申请新银行卡 | `card_type`, `card_level`（普通卡/金卡/白金卡/钻石卡）, `delivery_address` |
| `card_cancel` | 销卡（⚠️不可撤销） | `card_number`, `cancel_reason` |

---

## 特殊工具

| 工具 | 执行方 | 用途 |
|------|--------|------|
| `user_confirm` | 主 Agent | 展示操作详情请求用户确认；信息不完整时用于追问 |
| `web_search` | **子 Agent 专用** | 获取外部实时信息（市场行情、利率政策、新闻等）；主 Agent 不可直接调用，需通过 `task` 工具委托 |
