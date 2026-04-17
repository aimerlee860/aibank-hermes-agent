# coding: utf-8
"""
Mock 函数模块 - 模拟银行系统返回数据

优先从 data/accountData.json 读取真实配置数据；
文件不存在或数据缺失时降级为内置桩数据。
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

# ── accountData.json loader ────────────────────────────────────────────────────
_DATA_FILE = Path.home() / ".hermes" / "data" / "mobile_bank" / "accountData.json"
_account_data: Dict[str, Any] | None = None


def _load_account_data() -> Dict[str, Any]:
    global _account_data
    if _account_data is not None:
        return _account_data
    try:
        if _DATA_FILE.exists():
            with open(_DATA_FILE, "r", encoding="utf-8") as f:
                _account_data = json.load(f)
        else:
            _account_data = {}
    except Exception as e:
        print(f"[mocks] 加载 accountData.json 失败: {e}")
        _account_data = {}
    return _account_data


def _resolve_account_id(ref: str, data: dict) -> str:
    """将账户后4位或账户类型名映射到完整 accountId（19位）。

    Rules:
    - 19位字符串 → 已是 accountId，直接返回
    - 4位数字字符串 → 匹配 accounts[].accountNo
    - 其他字符串（如"储蓄卡"）→ 匹配 accounts[].accountType 子串
    """
    if len(ref) == 19 and ref.isdigit():
        return ref
    accounts = data.get("accounts", [])
    # 优先精确匹配 accountNo（末4位）
    if len(ref) == 4 and ref.isdigit():
        matched = next((a for a in accounts if a.get("accountNo") == ref), None)
        if matched:
            return matched["accountId"]
    # 按 accountType 子串匹配，取第一个非信用账户
    matched = next(
        (a for a in accounts if ref in a.get("accountType", "") and a.get("accountType") != "信用账户"),
        None
    )
    if matched:
        return matched["accountId"]
    return ref  # 无法映射，原样返回


def balance_query_mock(account_type: str, currency: str = "CNY") -> str:
    """查询指定账户的实时余额。

    account_type 接受：
    - 账户类型名（如 "活期储蓄账户"、"储蓄卡"、"储蓄账户"）
    - 账户后4位（如 "0113"）
    - 账户名称（如 "工资卡"、"个人活期账户"）

    注意：account_list 不含余额字段，余额信息必须调用本接口获取。
    """
    data = _load_account_data()
    accounts = data.get("accounts", [])

    # 账户类型别名映射（用户常用说法 → 数据中的 accountType）
    type_aliases = {
        "储蓄卡": "活期储蓄账户",
        "储蓄账户": "活期储蓄账户",
        "活期": "活期储蓄账户",
        "定期": "定期储蓄账户",
        "信用卡": "信用账户",
    }

    # 别名转换
    search_term = type_aliases.get(account_type, account_type)

    # 按 accountNo 精确匹配
    filtered = [a for a in accounts if a.get("accountNo") == account_type and a.get("currency", "CNY") == currency]

    # 按 accountType 子串匹配（使用转换后的别名）
    if not filtered:
        filtered = [
            a for a in accounts
            if search_term in a.get("accountType", "")
            and a.get("accountType") != "信用账户"
            and a.get("currency", "CNY") == currency
        ]

    # 按 accountName 匹配（支持用户说"工资卡"、"主账户"等）
    if not filtered:
        filtered = [
            a for a in accounts
            if account_type in a.get("accountName", "")
            and a.get("accountType") != "信用账户"
            and a.get("currency", "CNY") == currency
        ]

    if filtered:
        acc = filtered[0]
        return json.dumps({
            "success": True,
            "accountId": acc.get("accountId"),
            "accountNo": acc.get("accountNo"),
            "accountName": acc.get("accountName"),
            "accountType": acc.get("accountType"),
            "balance": acc.get("balance", 0),
            "availableBalance": acc.get("availableBalance", 0),
            "frozenBalance": acc.get("frozenBalance", 0),
            "currency": acc.get("currency", "CNY"),
        }, ensure_ascii=False)

    # fallback - 返回未找到提示，而不是假数据
    return json.dumps({
        "success": False,
        "error": f"未找到账户 '{account_type}'",
        "hint": "请使用 account_list 查询可用账户，然后用 accountNo（如0113）或 accountName 查询余额",
    }, ensure_ascii=False)


def account_list_mock(include_frozen: str = "否") -> str:
    """查询名下全部账户元数据列表。

    返回账户标识、类型、状态、卡号等静态元数据。
    注意：本接口不含余额字段（balance/availableBalance），查询余额请调用 balance_query。
    信用账户含额度字段（creditLimit/availableCredit），不含账单数据（账单请调 credit_card_bill）。

    accountNo 字段为 accountId 末4位，可作为 balance_query / credit_card_bill 的传参后缀。
    """
    data = _load_account_data()
    accounts = data.get("accounts", [])

    if include_frozen != "是":
        accounts = [a for a in accounts if a.get("accountStatus", "正常") != "冻结"]

    result = []
    for acc in accounts:
        entry = {
            "accountId": acc.get("accountId"),
            "accountNo": acc.get("accountNo"),       # accountId 末4位，用于 balance_query/credit_card_bill 传参
            "accountType": acc.get("accountType"),
            "accountName": acc.get("accountName"),
            "accountStatus": acc.get("accountStatus", "正常"),
            "currency": acc.get("currency", "CNY"),
            "isDefault": acc.get("isDefault", False),
        }
        # 信用账户附加额度字段（不含账单）
        if acc.get("accountType") == "信用账户":
            entry["creditLimit"] = acc.get("creditLimit")
            entry["availableCredit"] = acc.get("availableCredit")
            entry["usedCredit"] = acc.get("usedCredit")
        result.append(entry)

    if result:
        return json.dumps({"success": True, "count": len(result), "accounts": result}, ensure_ascii=False)

    # fallback
    fallback = [
        {"accountId": "6222021234567890112", "accountNo": "0112", "accountType": "活期储蓄账户", "accountStatus": "正常", "currency": "CNY", "isDefault": False},
        {"accountId": "6222021234567890113", "accountNo": "0113", "accountType": "活期储蓄账户", "accountStatus": "正常", "currency": "CNY", "isDefault": True},
        {"accountId": "6222021234567890567", "accountNo": "0567", "accountType": "信用账户", "accountStatus": "正常", "currency": "CNY", "isDefault": True,
         "creditLimit": 50000, "availableCredit": 44800, "usedCredit": 5200},
    ]
    if include_frozen == "是":
        fallback.append({"accountId": "6222021234567890119", "accountNo": "0119", "accountType": "活期储蓄账户", "accountStatus": "冻结", "currency": "CNY", "isDefault": False})
    return json.dumps({"success": True, "count": len(fallback), "accounts": fallback}, ensure_ascii=False)


def transaction_history_mock(
    account_type: str,
    time_range: str,
    transaction_type: Optional[str] = None,
    amount_min: Optional[float] = None,
    amount_max: Optional[float] = None
) -> str:
    """模拟交易明细查询"""
    days = int(time_range.replace("最近", "").replace("天", "")) if "天" in time_range else 30

    transactions = [
        {"date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"),
         "type": "支出", "amount": -100.00 - i*10, "description": f"消费{i+1}"}
        for i in range(min(days, 10))
    ]
    transactions.append({"date": datetime.now().strftime("%Y-%m-%d"),
                        "type": "收入", "amount": 10000.00, "description": "工资"})

    # 应用筛选
    if transaction_type:
        transactions = [t for t in transactions if t["type"] == transaction_type]
    if amount_min is not None:
        transactions = [t for t in transactions if abs(t["amount"]) >= amount_min]
    if amount_max is not None:
        transactions = [t for t in transactions if abs(t["amount"]) <= amount_max]

    return json.dumps({
        "success": True,
        "account_type": account_type,
        "time_range": time_range,
        "transactions": transactions,
        "total_count": len(transactions),
    }, ensure_ascii=False)


def stock_data_query_mock(
    symbol: str = "000001",
    period: str = "daily",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    adjust: str = "qfq"
) -> str:
    """模拟股票数据查询"""
    return json.dumps({
        "success": True,
        "symbol": symbol,
        "period": period,
        "data": [
            {"date": "2024-01-01", "open": 10.5, "high": 11.0, "low": 10.2, "close": 10.8, "volume": 1000000},
            {"date": "2024-01-02", "open": 10.8, "high": 11.2, "low": 10.6, "close": 11.0, "volume": 1200000},
        ],
    }, ensure_ascii=False)


def _load_icbc_products():
    """加载 ICBC 真实产品数据（数据截至 2026-04-01，仅供演示）"""
    import os
    _data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "icbc_products.json")
    try:
        with open(_data_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # 映射为 mock 格式：PR→R，补全字段
        products = []
        for i, p in enumerate(raw):
            rl = (p.get("riskLevel") or "PR2").replace("PR", "R")
            products.append({
                "product_id": p.get("code") or f"ICBC{i+1:03d}",
                "name": p.get("name", ""),
                "risk_level": rl,
                "min_amount": p.get("minAmount") or 1,
                "term": p.get("period") or "无固定期限",
                "annual_return": p.get("yieldValue") or 0,
                "yield_type": p.get("yieldType") or "",
                "yield_raw": p.get("yieldRaw") or "",
            })
        return products
    except Exception:
        # 回退到硬编码
        return [
            {"product_id": "FP001", "name": "稳盈宝1号", "risk_level": "R2", "min_amount": 1000, "term": "90天", "annual_return": 3.5},
            {"product_id": "FP002", "name": "增盈宝2号", "risk_level": "R3", "min_amount": 10000, "term": "180天", "annual_return": 4.2},
        ]

_ICBC_PRODUCTS = None

def financial_product_list_mock(
    product_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    min_amount: Optional[str] = None,
    term: Optional[str] = None,
    keyword: Optional[str] = None,
) -> str:
    """理财产品列表查询（数据来源：ICBC公开信息，截至2026-04-01）"""
    global _ICBC_PRODUCTS
    if _ICBC_PRODUCTS is None:
        _ICBC_PRODUCTS = _load_icbc_products()
    all_products = list(_ICBC_PRODUCTS)
    products = all_products

    # 关键词搜索
    if keyword:
        kw = keyword.strip()
        products = [p for p in products if kw in p.get("name", "") or kw in p.get("product_id", "")]

    # 应用筛选
    if product_type:
        products = [p for p in products if product_type in p["name"] or product_type in p.get("yield_type", "")]
    if risk_level:
        products = [p for p in products if p["risk_level"] == risk_level]
    if min_amount:
        try:
            products = [p for p in products if p["min_amount"] >= int(min_amount)]
        except (ValueError, TypeError):
            pass
    if term:
        products = [p for p in products if term in p.get("term", "")]

    # 限制返回数量
    products = products[:20]

    # 动态边界反馈
    all_types = sorted({p.get("yield_type", p.get("product_type", "未分类")) for p in all_products})
    all_risks = sorted({p.get("risk_level", "") for p in all_products if p.get("risk_level")})
    if not products:
        filters = []
        if keyword:
            filters.append(f"关键词'{keyword}'")
        if product_type:
            filters.append(f"类型'{product_type}'")
        if risk_level:
            filters.append(f"风险等级'{risk_level}'")
        filter_desc = "、".join(filters) if filters else "当前条件"
        message = (f"未找到{filter_desc}匹配的理财产品。"
                   f"当前共{len(all_products)}款可购产品，"
                   f"风险等级：{'、'.join(all_risks)}。"
                   f"请调整筛选条件或告知用户当前无该产品。")
    else:
        message = ""

    return json.dumps({
        "success": True,
        "products": products,
        "total_count": len(products),
        "available_risk_levels": all_risks,
        "message": message,
        "data_source": "ICBC公开信息（截至2026-04-01，仅供演示）",
    }, ensure_ascii=False)


def financial_holdings_mock(product_type: str = "全部", status: str = "持有中") -> str:
    """模拟理财持仓查询"""
    holdings = [
        {"product_id": "FP001", "name": "稳盈宝1号", "amount": 50000.00, "current_value": 50432.88, "profit": 432.88, "status": "持有中"},
        {"product_id": "FP002", "name": "增盈宝2号", "amount": 100000.00, "current_value": 102080.00, "profit": 2080.00, "status": "持有中"},
    ]

    if product_type != "全部":
        holdings = [h for h in holdings if product_type in h["name"]]
    if status:
        holdings = [h for h in holdings if h["status"] == status]

    return json.dumps({
        "success": True,
        "holdings": holdings,
        "total_assets": sum(h["current_value"] for h in holdings),
        "total_profit": sum(h["profit"] for h in holdings),
    }, ensure_ascii=False)


def credit_card_bill_mock(card_suffix: str, bill_type: str, bill_month: Optional[str] = None) -> str:
    """查询信用卡账单（动态数据，每月变化）。

    card_suffix: 信用卡后4位，即 account_list 返回的 accountNo（如 "0567"）。
    账单数据从 creditCards[].billing 子对象读取，与账户元数据隔离。
    """
    data = _load_account_data()
    credit_cards = data.get("creditCards", [])
    cc = next((c for c in credit_cards if c.get("cardNo") == card_suffix), None)
    if cc:
        billing = cc.get("billing", {})
        return json.dumps({
            "success": True,
            "cardNo": card_suffix,
            "cardName": cc.get("cardName", "工银信用卡"),
            "bill_month": bill_month or datetime.now().strftime("%Y-%m"),
            "bill_type": bill_type,
            "bill_amount": billing.get("currentBillAmount", 5200.00),
            "min_payment": billing.get("minPayment", 520.00),
            "payment_due_date": billing.get("dueDate", "2025-02-22"),
            "bill_period": billing.get("currentBillPeriod"),
        }, ensure_ascii=False)
    # fallback
    return json.dumps({
        "success": True,
        "cardNo": card_suffix,
        "bill_month": bill_month or datetime.now().strftime("%Y-%m"),
        "bill_type": bill_type,
        "bill_amount": 2500.00,
        "min_payment": 100.00,
        "payment_due_date": "2025-02-28",
    }, ensure_ascii=False)


def credit_limit_query_mock(card_suffix: str, limit_type: str = "全部") -> str:
    """查询信用卡额度。card_suffix 为信用卡后4位（account_list 返回的 accountNo）。"""
    data = _load_account_data()
    credit_cards = data.get("creditCards", [])
    cc = next((c for c in credit_cards if c.get("cardNo") == card_suffix), None)
    if cc:
        return json.dumps({
            "success": True,
            "cardNo": card_suffix,
            "cardName": cc.get("cardName", "工银信用卡"),
            "total_limit": cc.get("creditLimit", 50000.00),
            "available_limit": cc.get("availableCredit", 44800.00),
            "used_limit": cc.get("usedCredit", 5200.00),
            "cash_credit_limit": cc.get("cashCreditLimit", 25000.00),
            "available_cash_credit": cc.get("availableCashCredit", 25000.00),
        }, ensure_ascii=False)
    return json.dumps({
        "success": True,
        "cardNo": card_suffix,
        "total_limit": 50000.00,
        "available_limit": 44800.00,
        "used_limit": 5200.00,
    }, ensure_ascii=False)


def fixed_deposit_query_mock(account_type: str = "全部") -> str:
    """查询定期存款账户。字段与 accounts[] 统一（使用 term 而非 depositTerm）。"""
    data = _load_account_data()
    accounts = data.get("accounts", [])
    deposits = [
        {
            "accountId": a.get("accountId"),
            "accountNo": a.get("accountNo"),
            "accountName": a.get("accountName"),
            "principal": a.get("balance", 0),
            "interestRate": a.get("interestRate", 0),
            "term": a.get("term"),                   # 统一字段名（原 depositTerm）
            "openDate": a.get("openDate"),
            "maturityDate": a.get("maturityDate"),
            "accountStatus": a.get("accountStatus"),
        }
        for a in accounts if a.get("accountType") == "定期储蓄账户"
    ]
    if not deposits:
        deposits = [
            {"accountNo": "0115", "accountName": "个人定期账户", "principal": 2500.00,
             "interestRate": 0.015, "term": "12个月", "openDate": "2024-06-01",
             "maturityDate": "2025-06-01", "accountStatus": "正常"},
        ]
    return json.dumps({"success": True, "deposits": deposits, "count": len(deposits)}, ensure_ascii=False)


def loan_query_mock(loan_type: str = "全部") -> str:
    """模拟贷款信息查询"""
    loans = [
        {"loan_type": "房贷", "account": "LN20230101", "balance": 1500000.00, "monthly_payment": 8500.00, "next_due_date": "2024-02-15"},
    ]
    return json.dumps({
        "success": True,
        "loans": loans,
    }, ensure_ascii=False)


def consumer_loan_query_mock(loan_account: Optional[str] = None) -> str:
    """模拟消费贷款查询"""
    return json.dumps({
        "success": True,
        "loan_account": loan_account,
        "balance": 50000.00,
        "monthly_payment": 1500.00,
    }, ensure_ascii=False)


def mortgage_balance_query_mock(mortgage_account: Optional[str] = None) -> str:
    """模拟房贷余额查询"""
    return json.dumps({
        "success": True,
        "mortgage_account": mortgage_account,
        "original_amount": 2000000.00,
        "current_balance": 1500000.00,
        "remaining_term": 240,
    }, ensure_ascii=False)


def mortgage_repayment_plan_mock(mortgage_account: str) -> str:
    """模拟房贷还款计划查询"""
    return json.dumps({
        "success": True,
        "mortgage_account": mortgage_account,
        "plan": [
            {"month": "2024-01", "principal": 2000.00, "interest": 6500.00, "balance": 1498000.00},
            {"month": "2024-02", "principal": 2100.00, "interest": 6400.00, "balance": 1495900.00},
        ],
    }, ensure_ascii=False)


def business_loan_query_mock(loan_account: Optional[str] = None) -> str:
    """模拟经营贷款查询"""
    return json.dumps({
        "success": True,
        "loan_account": loan_account,
        "balance": 500000.00,
        "interest_rate": 4.35,
    }, ensure_ascii=False)


def car_loan_query_mock(loan_account: Optional[str] = None) -> str:
    """模拟车贷查询"""
    return json.dumps({
        "success": True,
        "loan_account": loan_account,
        "balance": 80000.00,
        "monthly_payment": 2500.00,
    }, ensure_ascii=False)


def points_query_mock(card_type: str = "信用卡") -> str:
    """模拟积分查询"""
    return json.dumps({
        "success": True,
        "card_type": card_type,
        "points": 5000,
        "expiry_date": "2025-12-31",
    }, ensure_ascii=False)


def internal_transfer_mock(
    from_account: str,
    to_account: str,
    amount: float,
    currency: str = "CNY",
    remark: Optional[str] = None
) -> str:
    """模拟行内转账。

    from_account / to_account 接受三种格式（服务层自动映射到 accountId）：
    - 账户后4位（如 "0113"）← 推荐，从 account_list 的 accountNo 字段获取
    - 完整 accountId（19位数字字符串）
    - 账户类型名（如 "活期储蓄账户"，取该类型第一个非信用账户）
    """
    data = _load_account_data()
    resolved_from = _resolve_account_id(from_account, data)
    resolved_to = _resolve_account_id(to_account, data)
    return json.dumps({
        "success": True,
        "transaction_id": f"TXN{int(datetime.now().timestamp())}",
        "from_account": resolved_from,
        "to_account": resolved_to,
        "amount": amount,
        "currency": currency,
        "remark": remark,
        "status": "转账成功",
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False)


def interbank_transfer_mock(
    from_account: str,
    to_bank: str,
    to_account: str,
    amount: float,
    currency: str = "CNY",
    remark: Optional[str] = None
) -> str:
    """模拟跨行转账"""
    return json.dumps({
        "success": True,
        "transaction_id": f"TXN{int(datetime.now().timestamp())}",
        "from_account": from_account,
        "to_bank": to_bank,
        "to_account": to_account,
        "amount": amount,
        "currency": currency,
        "remark": remark,
        "status": "转账成功（预计2小时内到账）",
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False)


def financial_product_buy_mock(
    product_id: str,
    amount: float,
    account_type: str = "储蓄卡",
    risk_confirm: bool = False
) -> str:
    """模拟理财产品购买"""
    if amount < 1000:
        return json.dumps({
            "success": False,
            "error": "购买金额低于起购金额",
            "product_id": product_id,
        }, ensure_ascii=False)

    if not risk_confirm:
        return json.dumps({
            "success": False,
            "error": "请确认风险",
            "product_id": product_id,
            "risk_warning": "理财非存款，产品有风险，投资需谨慎",
        }, ensure_ascii=False)

    return json.dumps({
        "success": True,
        "transaction_id": f"FPB{int(datetime.now().timestamp())}",
        "product_id": product_id,
        "amount": amount,
        "account_type": account_type,
        "status": "购买成功",
        "confirm_date": datetime.now().strftime("%Y-%m-%d"),
    }, ensure_ascii=False)


def financial_product_redeem_mock(
    product_id: str,
    amount: Optional[float] = None,
    account_type: str = "储蓄卡"
) -> str:
    """模拟理财产品赎回"""
    return json.dumps({
        "success": True,
        "transaction_id": f"FPR{int(datetime.now().timestamp())}",
        "product_id": product_id,
        "redeem_amount": amount,
        "account_type": account_type,
        "status": "赎回成功（预计3个工作日内到账）",
    }, ensure_ascii=False)


def credit_card_repay_mock(card_suffix: str, amount: float, account_type: str = "储蓄卡") -> str:
    """模拟信用卡还款"""
    return json.dumps({
        "success": True,
        "transaction_id": f"CCR{int(datetime.now().timestamp())}",
        "card_suffix": card_suffix,
        "amount": amount,
        "account_type": account_type,
        "status": "还款成功",
    }, ensure_ascii=False)


def custom_confirm_mock(message: str) -> str:
    """请求用户确认操作 - 返回确认请求状态，由 Hermes agent 的 clarify 机制处理

    Args:
        message: 确认信息，包括操作详情和风险提示

    Returns:
        JSON格式的确认请求状态（confirmed=false 表示需要用户确认）
    """
    # 不使用 input()，因为会阻塞 Hermes agent 的交互系统
    # 返回一个需要用户确认的状态，让 agent 通过 clarify 工具处理
    return json.dumps({
        "confirmed": False,
        "requires_user_confirmation": True,
        "message": message,
        "status": "等待用户确认",
        "hint": "请使用 clarify 工具请求用户确认此操作"
    }, ensure_ascii=False)




# ============ 转账汇款类 ============

def mobile_transfer_mock(
    from_account: str,
    to_mobile: str,
    amount: float,
    verification_method: str = "短信验证码"
) -> str:
    """模拟手机号转账"""
    return json.dumps({
        "success": True,
        "transaction_id": f"MT{int(datetime.now().timestamp())}",
        "from_account": from_account,
        "to_mobile": to_mobile,
        "amount": amount,
        "status": "转账成功",
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False)


# ============ 信用卡类 ============

def credit_limit_adjust_mock(
    card_suffix: str,
    adjust_amount: float,
    valid_days: int,
    reason: str
) -> str:
    """模拟信用卡额度调整"""
    return json.dumps({
        "success": True,
        "card_suffix": card_suffix,
        "adjust_amount": adjust_amount,
        "valid_days": valid_days,
        "reason": reason,
        "status": "申请已提交，等待审核",
        "apply_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False)


def bill_installment_mock(
    card_suffix: str,
    installment_amount: float,
    installment_periods: int
) -> str:
    """模拟信用卡账单分期"""
    monthly_payment = installment_amount / installment_periods
    service_fee = installment_amount * 0.006
    return json.dumps({
        "success": True,
        "card_suffix": card_suffix,
        "installment_amount": installment_amount,
        "installment_periods": installment_periods,
        "monthly_payment": round(monthly_payment, 2),
        "service_fee": round(service_fee, 2),
        "status": "分期申请成功",
        "apply_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False)


# ============ 定期存款类 ============

def fixed_deposit_open_mock(
    from_account: str,
    amount: float,
    term: str,
    interest_method: str = "到期取息",
    auto_renew: str = "否",
    verification_method: str = "短信验证码"
) -> str:
    """模拟开立定期存款"""
    deposit_id = f"DD{datetime.now().strftime('%Y%m%d%H%M%S')}"
    days_map = {"3个月": 90, "6个月": 180, "1年": 365, "2年": 730, "3年": 1095}
    days = days_map.get(term, 365)
    maturity_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    return json.dumps({
        "success": True,
        "deposit_id": deposit_id,
        "from_account": from_account,
        "amount": amount,
        "term": term,
        "interest_method": interest_method,
        "auto_renew": auto_renew,
        "maturity_date": maturity_date,
        "open_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "开立成功",
    }, ensure_ascii=False)


def fixed_deposit_withdraw_mock(
    deposit_id: str,
    withdraw_type: str,
    to_account: str,
    verification_method: str = "短信验证码",
    withdraw_amount: Optional[float] = None
) -> str:
    """模拟支取定期存款"""
    return json.dumps({
        "success": True,
        "transaction_id": f"WD{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "deposit_id": deposit_id,
        "withdraw_type": withdraw_type,
        "withdraw_amount": withdraw_amount,
        "to_account": to_account,
        "withdraw_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "支取成功",
    }, ensure_ascii=False)


# ============ 缴费支付类 ============

def utility_payment_mock(
    payment_type: str,
    payment_region: str,
    payment_company: str,
    account_number: str,
    from_account: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟生活缴费（水电燃气等）"""
    return json.dumps({
        "success": True,
        "transaction_id": f"UT{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "payment_type": payment_type,
        "payment_region": payment_region,
        "payment_company": payment_company,
        "account_number": account_number,
        "amount": 150.00,
        "from_account": from_account,
        "payment_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "缴费成功",
    }, ensure_ascii=False)


def mobile_recharge_mock(
    mobile_number: str,
    recharge_amount: int,
    from_account: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟手机话费充值"""
    return json.dumps({
        "success": True,
        "transaction_id": f"RC{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "mobile_number": mobile_number,
        "recharge_amount": recharge_amount,
        "from_account": from_account,
        "recharge_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "充值成功",
    }, ensure_ascii=False)


# ============ 交通出行类 ============

def bus_card_recharge_mock(
    card_number: str,
    recharge_amount: float,
    from_account: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟公交卡充值"""
    new_balance = 100.00 + recharge_amount
    return json.dumps({
        "success": True,
        "transaction_id": f"BC{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "card_number": card_number,
        "recharge_amount": recharge_amount,
        "from_account": from_account,
        "recharge_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "充值成功",
        "new_balance": new_balance,
    }, ensure_ascii=False)


def metro_qr_code_mock(
    city: str,
    from_account: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟开通/查询地铁乘车码"""
    qr_code = f"METRO{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return json.dumps({
        "success": True,
        "city": city,
        "qr_code": qr_code,
        "from_account": from_account,
        "status": "已开通",
        "activate_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": f"地铁乘车码已开通，可在{city}地铁使用",
    }, ensure_ascii=False)


def taxi_booking_mock(
    departure: str,
    destination: str,
    booking_time: Optional[str] = None,
    from_account: str = "",
    verification_method: str = "短信验证码"
) -> str:
    """模拟打车服务"""
    return json.dumps({
        "success": True,
        "order_id": f"TAXI{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "departure": departure,
        "destination": destination,
        "estimated_fare": 25.00,
        "estimated_distance": 8.5,
        "estimated_time": "20分钟",
        "booking_time": booking_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "订单已提交",
        "message": "正在为您匹配附近车辆，请稍候",
    }, ensure_ascii=False)


def train_ticket_booking_mock(
    departure_station: str,
    arrival_station: str,
    departure_date: str,
    train_number: Optional[str] = None,
    seat_type: str = "二等座",
    passenger_count: int = 1,
    from_account: str = "",
    verification_method: str = "短信验证码"
) -> str:
    """模拟火车票预订"""
    fare_map = {"一等座": 500, "二等座": 300, "硬座": 150, "硬卧": 250}
    fare = fare_map.get(seat_type, 300) * passenger_count

    return json.dumps({
        "success": True,
        "order_id": f"TRAIN{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "departure_station": departure_station,
        "arrival_station": arrival_station,
        "departure_date": departure_date,
        "train_number": train_number or "G1234",
        "seat_type": seat_type,
        "passenger_count": passenger_count,
        "fare": fare,
        "from_account": from_account,
        "status": "订票成功",
        "message": "请在30分钟内完成支付",
    }, ensure_ascii=False)


# ============ 购物消费类 ============

def ecommerce_platform_connect_mock(
    platform: str,
    account: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟电商平台绑定"""
    return json.dumps({
        "success": True,
        "platform": platform,
        "account": account,
        "status": "绑定成功",
        "connect_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False)


def coupon_receive_mock(
    coupon_type: str,
    coupon_amount: float,
    conditions: str = "无限制"
) -> str:
    """模拟优惠券领取"""
    coupon_id = f"CPN{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return json.dumps({
        "success": True,
        "coupon_id": coupon_id,
        "coupon_type": coupon_type,
        "coupon_amount": coupon_amount,
        "conditions": conditions,
        "status": "领取成功",
        "expiry_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
    }, ensure_ascii=False)


def movie_ticket_booking_mock(
    movie_name: str,
    cinema: str,
    show_time: str,
    seat_count: int = 2,
    from_account: str = "",
    verification_method: str = "短信验证码"
) -> str:
    """模拟电影票预订"""
    return json.dumps({
        "success": True,
        "order_id": f"MOVIE{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "movie_name": movie_name,
        "cinema": cinema,
        "show_time": show_time,
        "seat_count": seat_count,
        "fare": 35.00 * seat_count,
        "from_account": from_account,
        "status": "预订成功",
        "message": "请在15分钟内完成支付",
    }, ensure_ascii=False)


def food_delivery_order_mock(
    restaurant: str,
    dishes: list,
    delivery_address: str,
    from_account: str = "",
    verification_method: str = "短信验证码"
) -> str:
    """模拟外卖订单"""
    total_amount = sum(d.get("price", 0) * d.get("quantity", 1) for d in dishes)
    delivery_fee = 3.00

    return json.dumps({
        "success": True,
        "order_id": f"FOOD{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "restaurant": restaurant,
        "dishes": dishes,
        "delivery_address": delivery_address,
        "subtotal": total_amount,
        "delivery_fee": delivery_fee,
        "total_amount": total_amount + delivery_fee,
        "from_account": from_account,
        "status": "订单已提交",
        "estimated_delivery_time": "35分钟",
    }, ensure_ascii=False)


# ============ 政务服务类 ============

def social_security_query_mock(
    person_name: str,
    id_number: str
) -> str:
    """模拟社保查询"""
    return json.dumps({
        "success": True,
        "person_name": person_name,
        "id_number": id_number,
        "social_security_balance": 52000.00,
        "medical_insurance_balance": 12500.00,
        "employment_insurance_balance": 3500.00,
        "last_payment_date": "2024-01-15",
    }, ensure_ascii=False)


def tax_payment_mock(
    tax_type: str,
    tax_amount: float,
    from_account: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟税务申报"""
    return json.dumps({
        "success": True,
        "transaction_id": f"TAX{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "tax_type": tax_type,
        "tax_amount": tax_amount,
        "from_account": from_account,
        "payment_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "申报成功",
    }, ensure_ascii=False)


def fine_payment_mock(
    fine_type: str,
    fine_number: str,
    fine_amount: float,
    from_account: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟罚款缴纳"""
    return json.dumps({
        "success": True,
        "transaction_id": f"FINE{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "fine_type": fine_type,
        "fine_number": fine_number,
        "fine_amount": fine_amount,
        "from_account": from_account,
        "payment_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "缴纳成功",
    }, ensure_ascii=False)


# ============ 医疗健康类 ============

def hospital_registration_mock(
    hospital: str,
    department: str,
    doctor: Optional[str] = None,
    registration_date: str = "",
    from_account: str = "",
    verification_method: str = "短信验证码"
) -> str:
    """模拟医院挂号"""
    return json.dumps({
        "success": True,
        "registration_id": f"REG{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "hospital": hospital,
        "department": department,
        "doctor": doctor,
        "registration_date": registration_date or datetime.now().strftime("%Y-%m-%d"),
        "from_account": from_account,
        "registration_fee": 50.00,
        "status": "挂号成功",
        "message": "请按预约时间到医院就诊",
    }, ensure_ascii=False)


def medical_consultation_mock(
    symptoms: str,
    duration: str,
    medical_history: Optional[str] = None
) -> str:
    """模拟在线问诊"""
    return json.dumps({
        "success": True,
        "consultation_id": f"CONSULT{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "symptoms": symptoms,
        "duration": duration,
        "medical_history": medical_history,
        "status": "问诊已提交",
        "message": "医生将在24小时内回复",
    }, ensure_ascii=False)


def medical_insurance_payment_mock(
    hospital: str,
    medical_type: str,
    amount: float,
    from_account: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟医保支付"""
    insurance_coverage = amount * 0.7
    self_payment = amount * 0.3

    return json.dumps({
        "success": True,
        "transaction_id": f"MED{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "hospital": hospital,
        "medical_type": medical_type,
        "total_amount": amount,
        "insurance_coverage": insurance_coverage,
        "self_payment": self_payment,
        "from_account": from_account,
        "payment_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "支付成功",
    }, ensure_ascii=False)


# ============ 贷款服务类 ============

def loan_repayment_mock(
    loan_account: str,
    repayment_amount: float,
    from_account: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟贷款还款"""
    return json.dumps({
        "success": True,
        "transaction_id": f"LR{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "loan_account": loan_account,
        "repayment_amount": repayment_amount,
        "from_account": from_account,
        "payment_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "还款成功",
    }, ensure_ascii=False)


def consumer_loan_apply_mock(
    loan_amount: float,
    loan_term: int,
    loan_purpose: str,
    from_account: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟消费贷款申请"""
    monthly_rate = 0.05 / 12
    monthly_payment = loan_amount * monthly_rate * (1 + monthly_rate) ** loan_term / ((1 + monthly_rate) ** loan_term - 1)

    return json.dumps({
        "success": True,
        "application_id": f"CLA{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "loan_amount": loan_amount,
        "loan_term": loan_term,
        "loan_purpose": loan_purpose,
        "monthly_payment": round(monthly_payment, 2),
        "from_account": from_account,
        "application_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "申请已提交",
        "message": "等待审核，预计1-3个工作日出结果",
    }, ensure_ascii=False)


def mortgage_prepayment_appointment_mock(
    mortgage_account: str,
    prepayment_amount: float,
    prepayment_date: str,
    from_account: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟房贷提前还款预约"""
    return json.dumps({
        "success": True,
        "appointment_id": f"MPA{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "mortgage_account": mortgage_account,
        "prepayment_amount": prepayment_amount,
        "prepayment_date": prepayment_date,
        "from_account": from_account,
        "application_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "预约成功",
        "message": "请按预约日期携带相关证件到银行办理",
    }, ensure_ascii=False)


def business_loan_apply_mock(
    loan_amount: float,
    loan_term: int,
    business_type: str,
    from_account: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟经营贷款申请"""
    return json.dumps({
        "success": True,
        "application_id": f"BLA{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "loan_amount": loan_amount,
        "loan_term": loan_term,
        "business_type": business_type,
        "from_account": from_account,
        "application_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "申请已提交",
        "message": "需要提供经营证明材料，等待审核",
    }, ensure_ascii=False)


def car_loan_apply_mock(
    car_price: float,
    down_payment: float,
    loan_term: int,
    from_account: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟车贷申请"""
    loan_amount = car_price - down_payment
    monthly_rate = 0.05 / 12
    monthly_payment = loan_amount * monthly_rate * (1 + monthly_rate) ** loan_term / ((1 + monthly_rate) ** loan_term - 1)

    return json.dumps({
        "success": True,
        "application_id": f"CLA{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "car_price": car_price,
        "down_payment": down_payment,
        "loan_amount": loan_amount,
        "loan_term": loan_term,
        "monthly_payment": round(monthly_payment, 2),
        "from_account": from_account,
        "application_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "申请已提交",
        "message": "等待审核，预计3-5个工作日出结果",
    }, ensure_ascii=False)


# ============ 账户设置类 ============

def transaction_limit_set_mock(
    account: str,
    limit_type: str,
    limit_amount: float,
    verification_method: str = "短信验证码"
) -> str:
    """模拟设置交易限额"""
    return json.dumps({
        "success": True,
        "account": account,
        "limit_type": limit_type,
        "limit_amount": limit_amount,
        "effective_date": datetime.now().strftime("%Y-%m-%d"),
        "status": "设置成功",
    }, ensure_ascii=False)


def quick_pay_manage_mock(
    operation: str,
    from_account: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟快捷支付管理"""
    return json.dumps({
        "success": True,
        "operation": operation,
        "from_account": from_account,
        "operation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "操作成功",
    }, ensure_ascii=False)


def password_change_mock(
    account: str,
    password_type: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟密码修改"""
    return json.dumps({
        "success": True,
        "account": account,
        "password_type": password_type,
        "change_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "修改成功",
        "message": "密码修改成功，请妥善保管新密码",
    }, ensure_ascii=False)


def account_loss_report_mock(
    account: str,
    loss_reason: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟账户挂失"""
    return json.dumps({
        "success": True,
        "account": account,
        "loss_reason": loss_reason,
        "report_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "挂失成功",
        "message": "账户已挂失，请尽快到柜台办理新卡",
    }, ensure_ascii=False)


# ============ 积分服务类 ============

def points_exchange_mock(
    points: int,
    exchange_item: str,
    from_account: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟积分兑换"""
    return json.dumps({
        "success": True,
        "exchange_id": f"PE{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "points_used": points,
        "exchange_item": exchange_item,
        "from_account": from_account,
        "exchange_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "兑换成功",
        "message": "积分已扣除，礼品将在7个工作日内发放",
    }, ensure_ascii=False)


# ============ 外汇类 ============

def _load_icbc_rates():
    """加载 ICBC 真实汇率数据"""
    import os
    _path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "icbc_exchange_rates.json")
    try:
        with open(_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        data = raw.get("data", raw) if isinstance(raw, dict) else raw
        rates = {}
        for item in data:
            name = item.get("currencyCHName", "")
            pair = f"{item.get('currencyENName','')}/CNY"
            # ICBC rates are per 100 foreign currency units for most currencies
            ref = float(item.get("reference", 0))
            divisor = 100 if ref > 10 else 1  # JPY/KRW etc. have small values
            rates[pair] = {
                "name": name,
                "现汇买入": float(item.get("foreignBuy", 0)) / divisor,
                "现汇卖出": float(item.get("foreignSell", 0)) / divisor,
                "现钞买入": float(item.get("cashBuy", 0)) / divisor,
                "现钞卖出": float(item.get("cashSell", 0)) / divisor,
                "中间价": ref / divisor,
                "publish_time": f"{item.get('publishDate','')} {item.get('publishTime','')}",
            }
        return rates
    except Exception:
        return {}

_ICBC_RATES = None

def exchange_rate_query_mock(currency_pair: str, rate_type: str = "现汇") -> str:
    """外汇汇率查询（数据来源：ICBC公开信息，截至2026-04-01）"""
    global _ICBC_RATES
    if _ICBC_RATES is None:
        _ICBC_RATES = _load_icbc_rates()

    # 匹配货币对
    pair_data = _ICBC_RATES.get(currency_pair)
    if not pair_data:
        # 尝试模糊匹配
        for k, v in _ICBC_RATES.items():
            if currency_pair.upper() in k.upper() or currency_pair in v.get("name", ""):
                pair_data = v
                currency_pair = k
                break

    if not pair_data:
        pair_data = {"现汇买入": 0, "现汇卖出": 0, "中间价": 0}

    rate_key = "现汇买入" if rate_type == "现汇" else ("现钞买入" if rate_type == "现钞" else "中间价")
    return json.dumps({
        "success": True,
        "currency_pair": currency_pair,
        "rate_type": rate_type,
        "rate": pair_data.get(rate_key, 0.0),
        "all_rates": {k: v for k, v in pair_data.items() if k != "name" and k != "publish_time"},
        "update_time": pair_data.get("publish_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "data_source": "ICBC公开信息（截至2026-04-01，仅供演示）",
    }, ensure_ascii=False)


def forex_holdings_query_mock(currency: Optional[str] = None, account_type: str = "全部") -> str:
    """模拟外汇持仓查询"""
    holdings = [
        {"currency": "USD", "amount": 1000.00, "cny_value": 7241.50, "account": "外汇储蓄卡"},
        {"currency": "EUR", "amount": 500.00, "cny_value": 3910.00, "account": "外汇储蓄卡"},
    ]
    if currency:
        holdings = [h for h in holdings if h["currency"] == currency]
    return json.dumps({
        "success": True,
        "holdings": holdings,
        "total_cny_value": sum(h["cny_value"] for h in holdings),
    }, ensure_ascii=False)


def forex_buy_mock(
    from_account: str,
    to_account: str,
    currency: str,
    amount: float,
    rate_type: str = "现汇买入",
    verification_method: str = "短信验证码"
) -> str:
    """模拟个人购汇"""
    rate_map = {"USD": 7.2415, "EUR": 7.8200, "JPY": 0.0484, "GBP": 9.1200, "HKD": 0.9280}
    rate = rate_map.get(currency, 7.2415)
    foreign_amount = round(amount / rate, 2)
    return json.dumps({
        "success": True,
        "transaction_id": f"FX{int(datetime.now().timestamp())}",
        "from_account": from_account,
        "to_account": to_account,
        "currency": currency,
        "cny_amount": amount,
        "foreign_amount": foreign_amount,
        "exchange_rate": rate,
        "status": "购汇成功",
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False)


def forex_settle_mock(
    from_account: str,
    to_account: str,
    currency: str,
    amount: float,
    rate_type: str = "现汇卖出",
    verification_method: str = "短信验证码"
) -> str:
    """模拟个人结汇"""
    rate_map = {"USD": 7.2100, "EUR": 7.7900, "JPY": 0.0481, "GBP": 9.0800, "HKD": 0.9240}
    rate = rate_map.get(currency, 7.2100)
    cny_amount = round(amount * rate, 2)
    return json.dumps({
        "success": True,
        "transaction_id": f"FS{int(datetime.now().timestamp())}",
        "from_account": from_account,
        "to_account": to_account,
        "currency": currency,
        "foreign_amount": amount,
        "cny_amount": cny_amount,
        "exchange_rate": rate,
        "status": "结汇成功",
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False)


def forex_trade_mock(
    from_account: str,
    from_currency: str,
    to_currency: str,
    amount: float,
    verification_method: str = "短信验证码"
) -> str:
    """模拟外汇买卖（外币互换）"""
    return json.dumps({
        "success": True,
        "transaction_id": f"FT{int(datetime.now().timestamp())}",
        "from_account": from_account,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "from_amount": amount,
        "to_amount": round(amount * 0.92, 2),
        "status": "外汇买卖成功",
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False)


def cross_border_transfer_mock(
    from_account: str,
    to_bank: str,
    to_account: str,
    to_name: str,
    currency: str,
    amount: float,
    country: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟跨境汇款"""
    return json.dumps({
        "success": True,
        "transaction_id": f"CB{int(datetime.now().timestamp())}",
        "from_account": from_account,
        "to_bank": to_bank,
        "to_account": to_account,
        "to_name": to_name,
        "currency": currency,
        "amount": amount,
        "country": country,
        "status": "跨境汇款已提交（预计1-3个工作日到账）",
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False)


# ============ 贵金属类 ============

def _load_icbc_metals():
    """加载 ICBC 真实贵金属数据"""
    import os
    _path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "icbc_precious_metals.json")
    try:
        with open(_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        quotes = {}
        for section in raw.get("sections", []):
            for row in section.get("rows", []):
                name = row.get("name", "")
                if "黄金" in name:
                    quotes["黄金"] = {"price": float(row.get("midPrice") or row.get("buyPrice", 0)), "unit": "元/克", "change_pct": row.get("changeRate", "")}
                elif "白银" in name:
                    quotes["白银"] = {"price": float(row.get("midPrice") or row.get("buyPrice", 0)), "unit": "元/克", "change_pct": row.get("changeRate", "")}
                elif "铂金" in name:
                    quotes["铂金"] = {"price": float(row.get("midPrice") or row.get("buyPrice", 0)), "unit": "元/克", "change_pct": row.get("changeRate", "")}
                elif "钯金" in name:
                    quotes["钯金"] = {"price": float(row.get("midPrice") or row.get("buyPrice", 0)), "unit": "元/克", "change_pct": row.get("changeRate", "")}
        return quotes if quotes else None
    except Exception:
        return None

_ICBC_METALS = None

def precious_metal_quote_mock(metal_type: str = "全部", quote_type: str = "实时") -> str:
    """贵金属行情查询（数据来源：ICBC公开信息，截至2026-04-01）"""
    global _ICBC_METALS
    if _ICBC_METALS is None:
        _ICBC_METALS = _load_icbc_metals()

    quotes = _ICBC_METALS or {
        "黄金": {"price": 1033.84, "unit": "元/克", "change_pct": "-2.27%"},
        "白银": {"price": 15.907, "unit": "元/克", "change_pct": "-3.45%"},
        "铂金": {"price": 424.82, "unit": "元/克", "change_pct": "-1.83%"},
    }
    if metal_type != "全部":
        data = {metal_type: quotes.get(metal_type, {})}
    else:
        data = quotes
    return json.dumps({
        "success": True,
        "metal_type": metal_type,
        "quote_type": quote_type,
        "quotes": data,
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source": "ICBC公开信息（截至2026-04-01，仅供演示）",
    }, ensure_ascii=False)


def precious_metal_holdings_mock(metal_type: str = "全部") -> str:
    """模拟贵金属持仓查询"""
    holdings = [
        {"metal_type": "黄金", "amount_grams": 50.0, "cost_price": 460.00, "current_price": 485.32,
         "current_value": 24266.00, "profit": 1266.00, "profit_pct": "+5.5%"},
    ]
    if metal_type != "全部":
        holdings = [h for h in holdings if h["metal_type"] == metal_type]
    return json.dumps({
        "success": True,
        "holdings": holdings,
        "total_value": sum(h["current_value"] for h in holdings),
        "total_profit": sum(h["profit"] for h in holdings),
    }, ensure_ascii=False)


def precious_metal_buy_mock(
    from_account: str,
    metal_type: str,
    amount: float,
    price_type: str = "市价",
    risk_confirm: bool = False
) -> str:
    """模拟贵金属买入"""
    if not risk_confirm:
        return json.dumps({
            "success": False,
            "error": "请确认投资风险",
            "risk_warning": "⚠️ 投资有风险，市场价格波动可能导致亏损，请确认是否继续。",
        }, ensure_ascii=False)
    price_map = {"黄金": 485.32, "白银": 5.82, "铂金": 220.50}
    unit_price = price_map.get(metal_type, 485.32)
    total_cost = round(amount * unit_price, 2)
    return json.dumps({
        "success": True,
        "transaction_id": f"PMB{int(datetime.now().timestamp())}",
        "from_account": from_account,
        "metal_type": metal_type,
        "amount_grams": amount,
        "unit_price": unit_price,
        "total_cost": total_cost,
        "status": "买入成功",
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False)


def precious_metal_sell_mock(
    metal_type: str,
    amount: float,
    to_account: str,
    price_type: str = "市价"
) -> str:
    """模拟贵金属卖出"""
    price_map = {"黄金": 484.80, "白银": 5.79, "铂金": 219.80}
    unit_price = price_map.get(metal_type, 484.80)
    total_proceeds = round(amount * unit_price, 2)
    return json.dumps({
        "success": True,
        "transaction_id": f"PMS{int(datetime.now().timestamp())}",
        "metal_type": metal_type,
        "amount_grams": amount,
        "unit_price": unit_price,
        "total_proceeds": total_proceeds,
        "to_account": to_account,
        "status": "卖出成功",
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False)


# ============ 债券类 ============

def bond_list_mock(bond_type: Optional[str] = None, term: Optional[str] = None,
                   keyword: Optional[str] = None) -> str:
    """模拟可购债券产品查询"""
    all_bonds = [
        {"product_id": "GB2024001", "name": "2024年凭证式国债一期", "bond_type": "凭证式国债",
         "term": "3年", "annual_rate": 2.38, "min_amount": 100, "status": "在售"},
        {"product_id": "GB2024002", "name": "2024年记账式国债", "bond_type": "记账式国债",
         "term": "5年", "annual_rate": 2.57, "min_amount": 1000, "status": "在售"},
        {"product_id": "CB2024001", "name": "工商银行金融债", "bond_type": "金融债",
         "term": "2年", "annual_rate": 2.15, "min_amount": 10000, "status": "在售"},
    ]
    bonds = all_bonds
    if keyword:
        kw = keyword.strip()
        bonds = [b for b in bonds if kw in b["name"] or kw in b["product_id"]]
    if bond_type:
        bonds = [b for b in bonds if b["bond_type"] == bond_type]
    if term:
        bonds = [b for b in bonds if b["term"] == term]

    all_types = sorted({b["bond_type"] for b in all_bonds})
    if not bonds:
        filters = []
        if keyword:
            filters.append(f"关键词'{keyword}'")
        if bond_type:
            filters.append(f"类型'{bond_type}'")
        filter_desc = "、".join(filters) if filters else "当前条件"
        message = (f"未找到{filter_desc}匹配的债券产品。"
                   f"当前共{len(all_bonds)}款在售债券，类型：{'、'.join(all_types)}。"
                   f"请调整筛选条件或告知用户当前无该产品。")
    else:
        message = ""

    return json.dumps({
        "success": True,
        "bonds": bonds,
        "total_count": len(bonds),
        "available_types": all_types,
        "message": message,
    }, ensure_ascii=False)


def bond_holdings_mock(bond_type: str = "全部", status: str = "持有中") -> str:
    """模拟债券持仓查询"""
    holdings = [
        {"product_id": "GB2023001", "name": "2023年凭证式国债三期", "bond_type": "凭证式国债",
         "face_value": 50000.00, "purchase_date": "2023-05-10", "maturity_date": "2026-05-10",
         "annual_rate": 2.25, "status": "持有中"},
    ]
    if bond_type != "全部":
        holdings = [h for h in holdings if h["bond_type"] == bond_type]
    if status:
        holdings = [h for h in holdings if h["status"] == status]
    return json.dumps({
        "success": True,
        "holdings": holdings,
        "total_face_value": sum(h["face_value"] for h in holdings),
    }, ensure_ascii=False)


def bond_buy_mock(
    product_id: str,
    amount: float,
    from_account: str,
    risk_confirm: bool = False
) -> str:
    """模拟购买债券"""
    if not risk_confirm:
        return json.dumps({
            "success": False,
            "error": "请确认投资风险",
            "risk_warning": "⚠️ 投资有风险，市场价格波动可能导致亏损，请确认是否继续。",
        }, ensure_ascii=False)
    return json.dumps({
        "success": True,
        "transaction_id": f"BB{int(datetime.now().timestamp())}",
        "product_id": product_id,
        "amount": amount,
        "from_account": from_account,
        "status": "购买成功",
        "purchase_date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False)


def bond_sell_mock(
    product_id: str,
    to_account: str,
    amount: Optional[float] = None
) -> str:
    """模拟卖出债券"""
    return json.dumps({
        "success": True,
        "transaction_id": f"BS{int(datetime.now().timestamp())}",
        "product_id": product_id,
        "sell_amount": amount,
        "to_account": to_account,
        "status": "卖出成功（预计T+1到账）",
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False)


# ============ 保险类 ============

def insurance_product_list_mock(
    insurance_type: Optional[str] = None,
    premium_max: Optional[float] = None,
    keyword: Optional[str] = None,
) -> str:
    """模拟保险产品查询"""
    all_products = [
        {"product_id": "INS001", "name": "工银安享意外险", "insurance_type": "意外险",
         "annual_premium": 199.00, "coverage": 300000.00, "coverage_period": "1年"},
        {"product_id": "INS002", "name": "工银惠民医疗险", "insurance_type": "医疗险",
         "annual_premium": 399.00, "coverage": 1000000.00, "coverage_period": "1年"},
        {"product_id": "INS003", "name": "工银人寿定期寿险", "insurance_type": "寿险",
         "annual_premium": 1200.00, "coverage": 500000.00, "coverage_period": "20年"},
    ]
    products = all_products
    if keyword:
        kw = keyword.strip()
        products = [p for p in products if kw in p["name"] or kw in p["product_id"]]
    if insurance_type:
        products = [p for p in products if p["insurance_type"] == insurance_type]
    if premium_max is not None:
        products = [p for p in products if p["annual_premium"] <= premium_max]

    all_types = sorted({p["insurance_type"] for p in all_products})
    if not products:
        filters = []
        if keyword:
            filters.append(f"关键词'{keyword}'")
        if insurance_type:
            filters.append(f"类型'{insurance_type}'")
        filter_desc = "、".join(filters) if filters else "当前条件"
        message = (f"未找到{filter_desc}匹配的保险产品。"
                   f"当前共{len(all_products)}款保险产品，类型：{'、'.join(all_types)}。"
                   f"请调整筛选条件或告知用户当前无该产品。")
    else:
        message = ""

    return json.dumps({
        "success": True,
        "products": products,
        "total_count": len(products),
        "available_types": all_types,
        "message": message,
    }, ensure_ascii=False)


def insurance_holdings_mock(status: str = "生效中") -> str:
    """模拟我的保险查询"""
    holdings = [
        {"policy_id": "POL20230001", "product_name": "工银安享意外险", "insurance_type": "意外险",
         "insured_name": "张三", "start_date": "2023-06-01", "end_date": "2024-05-31",
         "annual_premium": 199.00, "coverage": 300000.00, "status": "生效中"},
    ]
    if status:
        holdings = [h for h in holdings if h["status"] == status]
    return json.dumps({
        "success": True,
        "policies": holdings,
        "total_count": len(holdings),
    }, ensure_ascii=False)


def insurance_buy_mock(
    product_id: str,
    insured_name: str,
    insured_id: str,
    coverage_period: str,
    payment_period: str,
    from_account: str,
    risk_confirm: bool = False
) -> str:
    """模拟购买保险"""
    if not risk_confirm:
        return json.dumps({
            "success": False,
            "error": "请确认投资风险",
            "risk_warning": "⚠️ 投资有风险，市场价格波动可能导致亏损，请确认是否继续。",
        }, ensure_ascii=False)
    return json.dumps({
        "success": True,
        "policy_id": f"POL{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "product_id": product_id,
        "insured_name": insured_name,
        "coverage_period": coverage_period,
        "payment_period": payment_period,
        "from_account": from_account,
        "status": "投保成功",
        "effective_date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False)


# ============ 通知存款类 ============

def notice_deposit_query_mock(account_type: str = "全部") -> str:
    """模拟通知存款查询"""
    deposits = [
        {"deposit_id": "ND001", "account_type": "七天通知", "principal": 200000.00,
         "rate": 1.35, "open_date": "2024-01-15", "status": "存续中"},
        {"deposit_id": "ND002", "account_type": "一天通知", "principal": 50000.00,
         "rate": 0.55, "open_date": "2024-02-01", "status": "存续中"},
    ]
    if account_type != "全部":
        deposits = [d for d in deposits if d["account_type"] == account_type]
    return json.dumps({
        "success": True,
        "deposits": deposits,
        "total_count": len(deposits),
        "total_principal": sum(d["principal"] for d in deposits),
    }, ensure_ascii=False)


def notice_deposit_open_mock(
    from_account: str,
    amount: float,
    notice_type: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟开立通知存款"""
    rate_map = {"一天通知": 0.55, "七天通知": 1.35}
    rate = rate_map.get(notice_type, 1.35)
    return json.dumps({
        "success": True,
        "deposit_id": f"ND{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "from_account": from_account,
        "amount": amount,
        "notice_type": notice_type,
        "rate": rate,
        "open_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "开立成功",
    }, ensure_ascii=False)


def notice_deposit_withdraw_mock(
    deposit_id: str,
    to_account: str,
    withdraw_amount: Optional[float] = None
) -> str:
    """模拟支取通知存款"""
    return json.dumps({
        "success": True,
        "transaction_id": f"NDW{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "deposit_id": deposit_id,
        "withdraw_amount": withdraw_amount,
        "to_account": to_account,
        "withdraw_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "支取成功",
    }, ensure_ascii=False)


# ============ 大额存单类 ============

def large_cd_query_mock(status: str = "全部") -> str:
    """模拟大额存单查询"""
    cds = [
        {"cd_id": "LCD001", "amount": 200000.00, "term": "1年", "rate": 2.10,
         "open_date": "2024-01-01", "maturity_date": "2025-01-01", "status": "未到期"},
        {"cd_id": "LCD002", "amount": 500000.00, "term": "3年", "rate": 2.35,
         "open_date": "2023-06-15", "maturity_date": "2026-06-15", "status": "未到期"},
    ]
    if status != "全部":
        cds = [c for c in cds if c["status"] == status]
    return json.dumps({
        "success": True,
        "cds": cds,
        "total_count": len(cds),
        "total_amount": sum(c["amount"] for c in cds),
    }, ensure_ascii=False)


def large_cd_open_mock(
    from_account: str,
    amount: float,
    term: str,
    interest_method: str = "到期取息",
    verification_method: str = "短信验证码"
) -> str:
    """模拟开立大额存单"""
    if amount < 200000:
        return json.dumps({
            "success": False,
            "error": "大额存单起购金额为20万元",
        }, ensure_ascii=False)
    rate_map = {"1个月": 1.60, "3个月": 1.75, "6个月": 1.90, "1年": 2.10, "2年": 2.25, "3年": 2.35}
    rate = rate_map.get(term, 2.10)
    days_map = {"1个月": 30, "3个月": 90, "6个月": 180, "1年": 365, "2年": 730, "3年": 1095}
    days = days_map.get(term, 365)
    maturity_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    return json.dumps({
        "success": True,
        "cd_id": f"LCD{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "from_account": from_account,
        "amount": amount,
        "term": term,
        "rate": rate,
        "interest_method": interest_method,
        "maturity_date": maturity_date,
        "open_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "开立成功",
    }, ensure_ascii=False)


def large_cd_withdraw_mock(
    cd_id: str,
    to_account: str,
    withdraw_type: str = "到期",
    verification_method: str = "短信验证码"
) -> str:
    """模拟支取大额存单"""
    return json.dumps({
        "success": True,
        "transaction_id": f"LCDW{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "cd_id": cd_id,
        "withdraw_type": withdraw_type,
        "to_account": to_account,
        "withdraw_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "支取成功",
    }, ensure_ascii=False)


# ============ 收款方管理类 ============

def payee_list_mock(payee_type: str = "全部") -> str:
    """模拟注册收款方查询"""
    payees = [
        {"payee_id": "PAY001", "payee_name": "李四", "payee_bank": "中国工商银行",
         "payee_account": "6222021234560001", "payee_type": "行内", "add_date": "2023-08-10"},
        {"payee_id": "PAY002", "payee_name": "王五", "payee_bank": "中国建设银行",
         "payee_account": "6217001234560002", "payee_type": "跨行", "add_date": "2023-10-20"},
    ]
    if payee_type != "全部":
        payees = [p for p in payees if p["payee_type"] == payee_type]
    return json.dumps({
        "success": True,
        "payees": payees,
        "total_count": len(payees),
    }, ensure_ascii=False)


def payee_add_mock(
    payee_name: str,
    payee_bank: str,
    payee_account: str,
    payee_type: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟添加收款方"""
    return json.dumps({
        "success": True,
        "payee_id": f"PAY{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "payee_name": payee_name,
        "payee_bank": payee_bank,
        "payee_account": payee_account,
        "payee_type": payee_type,
        "add_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "添加成功",
    }, ensure_ascii=False)


def payee_delete_mock(
    payee_id: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟删除收款方"""
    return json.dumps({
        "success": True,
        "payee_id": payee_id,
        "delete_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "删除成功",
    }, ensure_ascii=False)


# ============ 信用卡取现类 ============

def credit_card_cash_advance_query_mock(
    card_suffix: str,
    time_range: str = "最近30天"
) -> str:
    """模拟信用卡取现记录查询"""
    records = [
        {"advance_id": "CA001", "card_suffix": card_suffix, "amount": 2000.00,
         "to_account": "6222021234567890", "date": "2024-01-10", "fee": 40.00, "status": "已处理"},
    ]
    return json.dumps({
        "success": True,
        "card_suffix": card_suffix,
        "time_range": time_range,
        "records": records,
        "total_count": len(records),
    }, ensure_ascii=False)


def credit_card_cash_advance_mock(
    card_suffix: str,
    amount: float,
    to_account: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟信用卡取现"""
    fee = round(amount * 0.02, 2)
    return json.dumps({
        "success": True,
        "advance_id": f"CA{int(datetime.now().timestamp())}",
        "card_suffix": card_suffix,
        "amount": amount,
        "fee": fee,
        "to_account": to_account,
        "status": "取现成功",
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False)


def cash_advance_installment_mock(
    card_suffix: str,
    advance_id: str,
    installment_periods: int
) -> str:
    """模拟取现分期"""
    principal = 2000.00
    monthly_fee_rate = 0.006
    monthly_payment = round(principal / installment_periods + principal * monthly_fee_rate, 2)
    return json.dumps({
        "success": True,
        "installment_id": f"CAI{int(datetime.now().timestamp())}",
        "card_suffix": card_suffix,
        "advance_id": advance_id,
        "installment_periods": installment_periods,
        "monthly_payment": monthly_payment,
        "status": "分期申请成功",
        "apply_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False)


# ============ 工银i豆类 ============

def ibean_query_mock() -> str:
    """模拟工银i豆余额查询"""
    return json.dumps({
        "success": True,
        "ibean_balance": 8500,
        "expiring_ibeans": 200,
        "expiry_date": "2024-12-31",
        "equivalent_cash": 85.00,
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False)


def ibean_exchange_mock(
    ibean_count: int,
    exchange_item: str,
    exchange_category: str = "商城"
) -> str:
    """模拟工银i豆兑换"""
    return json.dumps({
        "success": True,
        "exchange_id": f"IB{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "ibean_count": ibean_count,
        "exchange_item": exchange_item,
        "exchange_category": exchange_category,
        "exchange_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "兑换成功",
        "message": "i豆已扣除，奖励将在3个工作日内到账",
    }, ensure_ascii=False)


# ============ 基金类 ============

def fund_list_mock(
    fund_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    min_amount: Optional[float] = None,
    keyword: Optional[str] = None,
) -> str:
    """模拟基金产品列表查询"""
    all_funds = [
        {"fund_code": "000001", "fund_name": "华夏成长混合", "fund_type": "混合型",
         "risk_level": "R3", "nav": 1.5230, "nav_date": "2026-03-19",
         "ytd_return": "+12.35%", "min_purchase": 100.0},
        {"fund_code": "110011", "fund_name": "易方达中小盘混合", "fund_type": "混合型",
         "risk_level": "R4", "nav": 8.8760, "nav_date": "2026-03-19",
         "ytd_return": "+18.20%", "min_purchase": 100.0},
        {"fund_code": "270008", "fund_name": "广发稳健增长混合", "fund_type": "混合型",
         "risk_level": "R2", "nav": 2.1450, "nav_date": "2026-03-19",
         "ytd_return": "+6.80%", "min_purchase": 100.0},
        {"fund_code": "000961", "fund_name": "天弘余额宝货币", "fund_type": "货币型",
         "risk_level": "R1", "nav": 1.0000, "nav_date": "2026-03-19",
         "ytd_return": "+1.65%", "min_purchase": 1.0},
        {"fund_code": "519732", "fund_name": "交银纯债债券", "fund_type": "债券型",
         "risk_level": "R2", "nav": 1.3280, "nav_date": "2026-03-19",
         "ytd_return": "+4.20%", "min_purchase": 1000.0},
        {"fund_code": "510300", "fund_name": "华泰柏瑞沪深300ETF联接", "fund_type": "指数型",
         "risk_level": "R3", "nav": 1.8350, "nav_date": "2026-03-19",
         "ytd_return": "+8.60%", "min_purchase": 10.0},
        {"fund_code": "159919", "fund_name": "嘉实沪深300ETF", "fund_type": "指数型",
         "risk_level": "R3", "nav": 4.2100, "nav_date": "2026-03-19",
         "ytd_return": "+9.15%", "min_purchase": 100.0},
    ]
    funds = all_funds
    if keyword:
        kw = keyword.strip()
        funds = [f for f in funds if kw in f["fund_name"] or kw in f["fund_code"]]
    if fund_type:
        funds = [f for f in funds if f["fund_type"] == fund_type]
    if risk_level:
        funds = [f for f in funds if f["risk_level"] == risk_level]
    if min_amount is not None:
        funds = [f for f in funds if f["min_purchase"] <= min_amount]

    # 动态反馈：告诉 LLM 搜索边界
    all_types = sorted({f["fund_type"] for f in all_funds})
    if not funds:
        filters = []
        if keyword:
            filters.append(f"关键词'{keyword}'")
        if fund_type:
            filters.append(f"类型'{fund_type}'")
        if risk_level:
            filters.append(f"风险等级'{risk_level}'")
        filter_desc = "、".join(filters) if filters else "当前条件"
        message = (f"未找到{filter_desc}匹配的基金。"
                   f"当前共{len(all_funds)}只可购基金，"
                   f"类型：{'、'.join(all_types)}。"
                   f"请调整筛选条件或告知用户当前无该产品。")
    else:
        message = ""

    return json.dumps({
        "success": True,
        "funds": funds,
        "total_count": len(funds),
        "available_types": all_types,
        "message": message,
    }, ensure_ascii=False)


def fund_nav_query_mock(fund_code: str) -> str:
    """模拟基金净值查询"""
    nav_data = {
        "000001": {"fund_name": "华夏成长混合", "nav": 1.5230, "acc_nav": 4.2350,
                   "nav_date": "2026-03-19", "daily_change": "+0.0120", "daily_change_pct": "+0.79%"},
        "110011": {"fund_name": "易方达中小盘混合", "nav": 8.8760, "acc_nav": 12.5380,
                   "nav_date": "2026-03-19", "daily_change": "+0.1050", "daily_change_pct": "+1.20%"},
        "000961": {"fund_name": "天弘余额宝货币", "nav": 1.0000, "acc_nav": 1.0000,
                   "nav_date": "2026-03-19", "daily_change": "0.0000", "daily_change_pct": "0.00%"},
        "510300": {"fund_name": "华泰柏瑞沪深300ETF联接", "nav": 1.8350, "acc_nav": 2.1200,
                   "nav_date": "2026-03-19", "daily_change": "+0.0085", "daily_change_pct": "+0.47%"},
        "159919": {"fund_name": "嘉实沪深300ETF", "nav": 4.2100, "acc_nav": 4.2100,
                   "nav_date": "2026-03-19", "daily_change": "+0.0210", "daily_change_pct": "+0.50%"},
    }
    info = nav_data.get(fund_code, {
        "fund_name": "未知基金", "nav": 0.0, "acc_nav": 0.0,
        "nav_date": "2026-03-19", "daily_change": "0.0000", "daily_change_pct": "0.00%"
    })
    return json.dumps({
        "success": True,
        "fund_code": fund_code,
        **info,
    }, ensure_ascii=False)


def fund_holdings_mock(status: str = "持有中") -> str:
    """模拟基金持仓查询"""
    holdings = [
        {"fund_code": "000001", "fund_name": "华夏成长混合", "fund_type": "混合型",
         "hold_share": 5000.0, "hold_nav": 1.5230, "hold_value": 7615.0,
         "cost_value": 6800.0, "profit": 815.0, "profit_pct": "+11.99%", "status": "持有中"},
        {"fund_code": "000961", "fund_name": "天弘余额宝货币", "fund_type": "货币型",
         "hold_share": 20000.0, "hold_nav": 1.0000, "hold_value": 20000.0,
         "cost_value": 20000.0, "profit": 0.0, "profit_pct": "0.00%", "status": "持有中"},
    ]
    if status != "全部":
        holdings = [h for h in holdings if h["status"] == status]
    return json.dumps({
        "success": True,
        "holdings": holdings,
        "total_value": sum(h["hold_value"] for h in holdings),
        "total_profit": sum(h["profit"] for h in holdings),
    }, ensure_ascii=False)


def fund_buy_mock(
    fund_code: str,
    amount: float,
    from_account: str,
    risk_confirm: bool = False
) -> str:
    """模拟申购基金"""
    if not risk_confirm:
        return json.dumps({
            "success": False,
            "error": "请确认投资风险",
            "risk_warning": "⚠️ 投资有风险，市场价格波动可能导致亏损，请确认是否继续。",
        }, ensure_ascii=False)
    nav_map = {"000001": 1.5230, "110011": 8.8760, "000961": 1.0000, "519732": 1.3280}
    nav = nav_map.get(fund_code, 1.0000)
    estimated_share = round(amount / nav, 2)
    return json.dumps({
        "success": True,
        "order_id": f"FUND{int(datetime.now().timestamp())}",
        "fund_code": fund_code,
        "purchase_amount": amount,
        "from_account": from_account,
        "estimated_share": estimated_share,
        "confirm_nav_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "status": "申购成功，份额将于T+1确认",
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False)


def fund_redeem_mock(
    fund_code: str,
    redeem_share: Optional[float],
    to_account: str
) -> str:
    """模拟赎回基金"""
    nav_map = {"000001": 1.5230, "110011": 8.8760, "000961": 1.0000, "519732": 1.3280}
    nav = nav_map.get(fund_code, 1.0000)
    share = redeem_share or 5000.0
    estimated_amount = round(share * nav, 2)
    return json.dumps({
        "success": True,
        "order_id": f"FREDEM{int(datetime.now().timestamp())}",
        "fund_code": fund_code,
        "redeem_share": redeem_share,
        "estimated_amount": estimated_amount,
        "to_account": to_account,
        "arrive_date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
        "status": "赎回成功，预计T+3到账",
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False)


def fund_transfer_mock(
    from_fund_code: str,
    to_fund_code: str,
    transfer_share: float,
    risk_confirm: bool = False
) -> str:
    """模拟基金转换"""
    if not risk_confirm:
        return json.dumps({
            "success": False,
            "error": "请确认投资风险",
            "risk_warning": "⚠️ 投资有风险，市场价格波动可能导致亏损，请确认是否继续。",
        }, ensure_ascii=False)
    return json.dumps({
        "success": True,
        "order_id": f"FTRANS{int(datetime.now().timestamp())}",
        "from_fund_code": from_fund_code,
        "to_fund_code": to_fund_code,
        "transfer_share": transfer_share,
        "status": "转换申请已提交，将于下一交易日确认",
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False)


# ============ 工银理财类 ============

def icbc_wealth_product_list_mock(
    product_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    min_amount: Optional[float] = None,
    keyword: Optional[str] = None,
) -> str:
    """模拟工银理财专属产品查询"""
    all_products = [
        {"product_id": "IW001", "name": "工银理财·稳享固收1号", "product_type": "固定收益类",
         "risk_level": "R2", "min_amount": 1.0, "term": "90天", "expected_return": "3.25%",
         "open_date": "2026-03-20", "close_date": "2026-03-25"},
        {"product_id": "IW002", "name": "工银理财·鑫尊权益1号", "product_type": "混合类",
         "risk_level": "R3", "min_amount": 10000.0, "term": "180天", "expected_return": "4.50%~6.00%",
         "open_date": "2026-03-20", "close_date": "2026-03-22"},
        {"product_id": "IW003", "name": "工银理财·添益现金管理", "product_type": "现金管理类",
         "risk_level": "R1", "min_amount": 0.01, "term": "随时申赎", "expected_return": "2.10%",
         "open_date": "2026-01-01", "close_date": "长期"},
    ]
    products = all_products
    if keyword:
        kw = keyword.strip()
        products = [p for p in products if kw in p["name"] or kw in p["product_id"]]
    if product_type:
        products = [p for p in products if p["product_type"] == product_type]
    if risk_level:
        products = [p for p in products if p["risk_level"] == risk_level]
    if min_amount is not None:
        products = [p for p in products if p["min_amount"] <= min_amount]

    all_types = sorted({p["product_type"] for p in all_products})
    all_risks = sorted({p["risk_level"] for p in all_products})
    if not products:
        filters = []
        if keyword:
            filters.append(f"关键词'{keyword}'")
        if product_type:
            filters.append(f"类型'{product_type}'")
        if risk_level:
            filters.append(f"风险等级'{risk_level}'")
        filter_desc = "、".join(filters) if filters else "当前条件"
        message = (f"未找到{filter_desc}匹配的工银理财产品。"
                   f"当前共{len(all_products)}款产品，类型：{'、'.join(all_types)}，"
                   f"风险等级：{'、'.join(all_risks)}。"
                   f"请调整筛选条件或告知用户当前无该产品。")
    else:
        message = ""

    return json.dumps({
        "success": True,
        "products": products,
        "total_count": len(products),
        "available_types": all_types,
        "message": message,
    }, ensure_ascii=False)


def icbc_wealth_holdings_mock(status: str = "持有中") -> str:
    """模拟工银理财持仓查询"""
    holdings = [
        {"product_id": "IW001", "name": "工银理财·稳享固收1号", "product_type": "固定收益类",
         "hold_amount": 50000.0, "current_value": 50406.25, "profit": 406.25,
         "annual_return": "3.25%", "maturity_date": "2026-06-20", "status": "持有中"},
    ]
    if status != "全部":
        holdings = [h for h in holdings if h["status"] == status]
    return json.dumps({
        "success": True,
        "holdings": holdings,
        "total_value": sum(h["current_value"] for h in holdings),
        "total_profit": sum(h["profit"] for h in holdings),
    }, ensure_ascii=False)


def icbc_wealth_buy_mock(
    product_id: str,
    amount: float,
    from_account: str,
    risk_confirm: bool = False
) -> str:
    """模拟购买工银理财产品"""
    if not risk_confirm:
        return json.dumps({
            "success": False,
            "error": "请确认投资风险",
            "risk_warning": "⚠️ 投资有风险，理财非存款，产品有风险，投资需谨慎。",
        }, ensure_ascii=False)
    return json.dumps({
        "success": True,
        "order_id": f"IWB{int(datetime.now().timestamp())}",
        "product_id": product_id,
        "amount": amount,
        "from_account": from_account,
        "status": "购买成功",
        "confirm_date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False)


# ============ 征信查询类 ============

def credit_report_query_mock(
    person_name: str,
    id_number: str,
    query_purpose: str = "本人查询"
) -> str:
    """模拟央行征信报告查询"""
    return json.dumps({
        "success": True,
        "person_name": person_name,
        "id_number": id_number[-4:].rjust(18, "*"),
        "query_purpose": query_purpose,
        "query_date": datetime.now().strftime("%Y-%m-%d"),
        "credit_score": 712,
        "credit_level": "良好",
        "loan_accounts": [
            {"loan_type": "个人住房贷款", "bank": "中国工商银行", "balance": 1500000.00,
             "status": "正常", "overdue_times": 0},
        ],
        "credit_card_accounts": [
            {"bank": "中国工商银行", "card_type": "信用卡", "credit_limit": 50000.00,
             "used_amount": 2500.00, "status": "正常", "overdue_times": 0},
        ],
        "query_records_6m": 3,
        "overdue_records": 0,
        "report_url": "仅供本次查询使用，不含下载链接",
        "tip": "您的信用记录良好，近6个月共被查询3次",
    }, ensure_ascii=False)


# ============ 银行卡管理类 ============

def card_status_query_mock(card_type: str = "全部") -> str:
    """模拟银行卡状态查询"""
    cards = [
        {"card_number": "6222 **** **** 7890", "card_type": "借记卡", "card_level": "普通卡",
         "bank_name": "中国工商银行", "open_date": "2018-05-12", "status": "正常",
         "daily_limit": 50000.00, "single_limit": 20000.00},
        {"card_number": "6222 **** **** 7891", "card_type": "借记卡", "card_level": "金卡",
         "bank_name": "中国工商银行", "open_date": "2020-11-03", "status": "正常",
         "daily_limit": 100000.00, "single_limit": 50000.00},
        {"card_number": "6222 **** **** 7892", "card_type": "信用卡", "card_level": "白金卡",
         "bank_name": "中国工商银行", "open_date": "2021-03-25", "status": "正常",
         "credit_limit": 50000.00, "available_limit": 47500.00},
    ]
    if card_type != "全部":
        cards = [c for c in cards if c["card_type"] == card_type]
    return json.dumps({
        "success": True,
        "cards": cards,
        "total_count": len(cards),
    }, ensure_ascii=False)


def card_apply_mock(
    card_type: str,
    card_level: str,
    delivery_address: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟申请新银行卡"""
    return json.dumps({
        "success": True,
        "application_id": f"CARD{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "card_type": card_type,
        "card_level": card_level,
        "delivery_address": delivery_address,
        "apply_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "申请已提交",
        "message": "审核通过后将在5-7个工作日内邮寄到您指定地址",
    }, ensure_ascii=False)


def card_cancel_mock(
    card_number: str,
    cancel_reason: str,
    verification_method: str = "短信验证码"
) -> str:
    """模拟销卡"""
    return json.dumps({
        "success": True,
        "card_number": card_number,
        "cancel_reason": cancel_reason,
        "cancel_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "销卡成功",
        "message": "⚠️ 卡片已注销，此操作不可撤销。如有余额请确认已转出。",
    }, ensure_ascii=False)


# ============ 安全管控类 ============

def login_log_query_mock(days: int = 30, limit: int = 20) -> str:
    """查询登录日志"""
    data = _load_account_data()
    security = data.get("security", {})
    history = security.get("loginHistory", [])
    # 返回前 limit 条
    result = history[:limit]
    return json.dumps({
        "success": True,
        "total": len(history),
        "records": result,
        "query_days": days,
    }, ensure_ascii=False)


def device_list_query_mock() -> str:
    """查询已绑定设备列表"""
    data = _load_account_data()
    security = data.get("security", {})
    devices = security.get("loginDevices", [])
    return json.dumps({
        "success": True,
        "total": len(devices),
        "devices": devices,
    }, ensure_ascii=False)


def device_unbind_mock(
    device_id: str,
    verification_method: str = "短信验证码"
) -> str:
    """解绑指定设备"""
    data = _load_account_data()
    security = data.get("security", {})
    devices = security.get("loginDevices", [])
    device = next((d for d in devices if d.get("deviceId") == device_id), None)
    if not device:
        return json.dumps({"success": False, "message": f"未找到设备 {device_id}"}, ensure_ascii=False)
    if device.get("isCurrent"):
        return json.dumps({"success": False, "message": "不能解绑当前登录设备，请从其他设备操作"}, ensure_ascii=False)
    return json.dumps({
        "success": True,
        "device_id": device_id,
        "device_name": device.get("deviceName"),
        "unbind_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "解绑成功",
        "message": "设备已解绑，该设备将无法直接登录，需重新验证。",
    }, ensure_ascii=False)


def ushield_status_query_mock() -> str:
    """查询U盾状态"""
    data = _load_account_data()
    security = data.get("security", {})
    ushield = security.get("ushield", {})
    return json.dumps({
        "success": True,
        "ushield": ushield,
    }, ensure_ascii=False)


def ushield_report_loss_mock(
    serial_no: str,
    verification_method: str = "短信验证码"
) -> str:
    """U盾挂失（立即生效，不可撤销）"""
    return json.dumps({
        "success": True,
        "serial_no": serial_no,
        "report_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "挂失成功",
        "message": "⚠️ U盾已挂失，此操作立即生效且不可撤销。请尽快前往网点申请新U盾。",
    }, ensure_ascii=False)


def ushield_apply_mock(
    delivery_address: str,
    verification_method: str = "短信验证码"
) -> str:
    """申请新U盾"""
    return json.dumps({
        "success": True,
        "application_id": f"USH{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "delivery_address": delivery_address,
        "apply_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "申请已提交",
        "message": "U盾申请成功，预计3-5个工作日内邮寄到指定地址。收到后需前往网点激活。",
    }, ensure_ascii=False)


def biometric_manage_mock(
    biometric_type: str,
    action: str,
    verification_method: str = "短信验证码"
) -> str:
    """生物识别管理（开启/关闭指纹、面容ID、声纹）

    biometric_type: fingerprint / faceId / voicePrint
    action: enable / disable
    """
    type_name_map = {"fingerprint": "指纹识别", "faceId": "面容ID", "voicePrint": "声纹识别"}
    action_name = "开启" if action == "enable" else "关闭"
    type_name = type_name_map.get(biometric_type, biometric_type)
    return json.dumps({
        "success": True,
        "biometric_type": biometric_type,
        "type_name": type_name,
        "action": action,
        "status": f"{type_name}{action_name}成功",
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False)


def account_freeze_mock(
    account_no: str,
    freeze_reason: str,
    verification_method: str = "短信验证码"
) -> str:
    """紧急冻结账户（发现异常时使用）"""
    return json.dumps({
        "success": True,
        "account_no": account_no,
        "freeze_reason": freeze_reason,
        "freeze_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "冻结成功",
        "message": "账户已冻结，冻结期间无法进行转账、消费等操作。如需解冻请致电客服或前往网点。",
    }, ensure_ascii=False)


def account_unfreeze_mock(
    account_no: str,
    unfreeze_reason: str,
    verification_method: str = "短信验证码"
) -> str:
    """解冻账户"""
    return json.dumps({
        "success": True,
        "account_no": account_no,
        "unfreeze_reason": unfreeze_reason,
        "unfreeze_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "解冻成功",
        "message": "账户已恢复正常状态，可正常使用。",
    }, ensure_ascii=False)


def emergency_contact_set_mock(
    name: str,
    phone: str,
    relationship: str,
    verification_method: str = "短信验证码"
) -> str:
    """设置/更新紧急联系人"""
    return json.dumps({
        "success": True,
        "name": name,
        "phone": phone,
        "relationship": relationship,
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "紧急联系人更新成功",
    }, ensure_ascii=False)


def security_check_mock() -> str:
    """账户安全综合检测（返回安全评分和风险提示）"""
    data = _load_account_data()
    security = data.get("security", {})
    biometric = security.get("biometric", {})
    ushield = security.get("ushield", {})
    devices = security.get("loginDevices", [])
    history = security.get("loginHistory", [])

    risks = []
    score = 100
    if not biometric.get("faceId") and not biometric.get("fingerprint"):
        risks.append("未开启生物识别，建议开启指纹或面容ID登录")
        score -= 10
    if ushield.get("status") not in ("正常", "已激活", "active"):
        risks.append("U盾状态异常，请检查U盾")
        score -= 20
    suspicious = [h for h in history if h.get("isSuspicious")]
    if suspicious:
        risks.append(f"发现 {len(suspicious)} 条异常登录记录，请核实")
        score -= 30
    untrusted = [d for d in devices if not d.get("isTrusted")]
    if untrusted:
        risks.append(f"有 {len(untrusted)} 个未信任设备，建议解绑")
        score -= 15

    level = "优秀" if score >= 90 else ("良好" if score >= 75 else ("一般" if score >= 60 else "较差"))
    return json.dumps({
        "success": True,
        "security_score": max(score, 0),
        "security_level": level,
        "risks": risks,
        "biometric": biometric,
        "ushield_status": ushield.get("status", "未知"),
        "device_count": len(devices),
        "recent_logins": len(history),
        "check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False)


# ============ 渠道服务类 ============

def branch_query_mock(
    city: str,
    district: str = "",
    service_type: str = "",
    limit: int = 5
) -> str:
    """查询附近网点"""
    branches = [
        {
            "branch_id": "BR001",
            "name": f"工商银行{city}{''.join([district])}支行",
            "address": f"{city}{district}建国路88号",
            "phone": "010-95588",
            "business_hours": "周一至周五 09:00-17:00，周六 09:00-12:00",
            "services": ["开户", "挂失", "大额业务", "贷款", "理财", "外汇"],
            "distance": "0.8km",
            "queue_count": 12,
            "waiting_time": "约25分钟",
        },
        {
            "branch_id": "BR002",
            "name": f"工商银行{city}{''.join([district])}分行营业部",
            "address": f"{city}{district}长安街100号",
            "phone": "010-95588",
            "business_hours": "周一至周五 09:00-17:30",
            "services": ["开户", "挂失", "大额业务", "贷款", "理财", "外汇", "贵宾服务"],
            "distance": "1.5km",
            "queue_count": 5,
            "waiting_time": "约12分钟",
        },
    ]
    filtered = branches
    if service_type:
        filtered = [b for b in branches if service_type in b.get("services", [])]
    return json.dumps({
        "success": True,
        "city": city,
        "district": district,
        "total": len(filtered[:limit]),
        "branches": filtered[:limit],
    }, ensure_ascii=False)


def branch_appointment_mock(
    branch_id: str,
    service_type: str,
    appointment_date: str,
    appointment_time: str,
    name: str,
    phone: str
) -> str:
    """预约网点叫号"""
    return json.dumps({
        "success": True,
        "appointment_id": f"APT{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "branch_id": branch_id,
        "service_type": service_type,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "name": name,
        "phone": phone,
        "queue_number": f"A{int(datetime.now().timestamp()) % 100:03d}",
        "status": "预约成功",
        "message": f"您已成功预约 {appointment_date} {appointment_time} 的 {service_type} 服务，请提前10分钟到达并取号。",
        "remind_sms": True,
    }, ensure_ascii=False)


def atm_query_mock(
    city: str,
    district: str = "",
    limit: int = 5
) -> str:
    """查询附近ATM"""
    atms = [
        {
            "atm_id": "ATM001",
            "location": f"{city}{district}建国路88号工商银行网点内",
            "address": f"{city}{district}建国路88号",
            "distance": "0.8km",
            "type": "存取款一体机",
            "status": "正常",
            "supports_cardless": True,
            "business_hours": "24小时",
        },
        {
            "atm_id": "ATM002",
            "location": f"{city}{district}朝阳门地铁站B口旁",
            "address": f"{city}{district}朝阳门外大街10号",
            "distance": "1.2km",
            "type": "取款机",
            "status": "正常",
            "supports_cardless": True,
            "business_hours": "06:00-24:00",
        },
        {
            "atm_id": "ATM003",
            "location": f"{city}{district}国贸商场一层",
            "address": f"{city}{district}建国门外大街1号",
            "distance": "2.0km",
            "type": "存取款一体机",
            "status": "正常",
            "supports_cardless": False,
            "business_hours": "09:00-22:00",
        },
    ]
    return json.dumps({
        "success": True,
        "city": city,
        "total": len(atms[:limit]),
        "atms": atms[:limit],
    }, ensure_ascii=False)


def cardless_withdrawal_apply_mock(
    amount: float,
    from_account: str,
    valid_minutes: int = 30,
    verification_method: str = "短信验证码"
) -> str:
    """预约无卡取款（ATM取款码）"""
    if amount > 20000:
        return json.dumps({
            "success": False,
            "message": "无卡取款单笔限额20000元，请分次操作",
        }, ensure_ascii=False)
    withdrawal_code = f"{int(datetime.now().timestamp()) % 100000000:08d}"
    expiry_time = (datetime.now() + timedelta(minutes=valid_minutes)).strftime("%Y-%m-%d %H:%M:%S")
    return json.dumps({
        "success": True,
        "withdrawal_code": withdrawal_code,
        "amount": amount,
        "from_account": from_account,
        "expiry_time": expiry_time,
        "valid_minutes": valid_minutes,
        "status": "预约成功",
        "message": f"⚠️ 取款码 {withdrawal_code} 有效期{valid_minutes}分钟（至{expiry_time}），请尽快前往工行ATM取款，请勿将取款码告知他人。",
    }, ensure_ascii=False)


def echannel_appointment_mock(
    service_type: str,
    appointment_date: str,
    appointment_time: str,
    branch_id: str = ""
) -> str:
    """预约eChannel自助终端业务"""
    return json.dumps({
        "success": True,
        "appointment_id": f"ECH{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "service_type": service_type,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "branch_id": branch_id or "BR001",
        "status": "预约成功",
        "message": f"eChannel预约成功，请于 {appointment_date} {appointment_time} 携带本人身份证前往指定自助终端办理{service_type}。",
    }, ensure_ascii=False)


def home_service_appointment_mock(
    service_type: str,
    appointment_date: str,
    preferred_time: str,
    contact_name: str,
    contact_phone: str,
    address: str
) -> str:
    """预约上门服务（企业/VIP客户专属）"""
    return json.dumps({
        "success": True,
        "appointment_id": f"HOS{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "service_type": service_type,
        "appointment_date": appointment_date,
        "preferred_time": preferred_time,
        "contact_name": contact_name,
        "contact_phone": contact_phone,
        "address": address,
        "status": "申请已提交",
        "message": "上门服务申请已提交，客户经理将于1个工作日内与您联系确认具体时间。",
    }, ensure_ascii=False)


def phone_banking_transfer_mock(
    service_type: str = "转人工客服",
    callback_phone: str = ""
) -> str:
    """电话银行转人工 / 回拨预约"""
    if callback_phone:
        return json.dumps({
            "success": True,
            "callback_phone": callback_phone,
            "estimated_callback": "5-10分钟内",
            "service_number": "95588",
            "status": "回拨预约成功",
            "message": f"已预约回拨，客服将在5-10分钟内致电 {callback_phone}，请保持电话畅通。",
        }, ensure_ascii=False)
    return json.dumps({
        "success": True,
        "service_type": service_type,
        "service_number": "95588",
        "queue_position": 3,
        "estimated_wait": "约8分钟",
        "status": "已排队",
        "message": "已接入工行客服队列，当前排队3人，预计等待约8分钟，请勿挂断。",
    }, ensure_ascii=False)


# ============ 网页获取类 ============

def web_fetch_mock(url: str, timeout: int = 10) -> str:
    """模拟获取网页内容，返回结构化的银行页面信息"""
    import re

    domain_match = re.search(r'https?://([^/]+)', url)
    domain = domain_match.group(1) if domain_match else "unknown"
    url_lower = url.lower()

    # 识别银行
    if any(k in url_lower for k in ["ccb.com"]):
        bank_name, bank_short = "中国建设银行", "CCB"
    elif any(k in url_lower for k in ["icbc.com"]):
        bank_name, bank_short = "中国工商银行", "ICBC"
    elif any(k in url_lower for k in ["boc.cn"]):
        bank_name, bank_short = "中国银行", "BOC"
    elif any(k in url_lower for k in ["cmb.com", "cmbchina.com"]):
        bank_name, bank_short = "招商银行", "CMB"
    elif any(k in url_lower for k in ["abchina.com"]):
        bank_name, bank_short = "中国农业银行", "ABC"
    elif any(k in url_lower for k in ["bankcomm.com"]):
        bank_name, bank_short = "交通银行", "BOCOM"
    elif any(k in url_lower for k in ["psbc.com"]):
        bank_name, bank_short = "中国邮政储蓄银行", "PSBC"
    else:
        bank_name, bank_short = domain, domain.upper()

    # 根据 URL 路径推断页面内容类型
    page_content = _get_bank_page_content(url_lower, bank_name)

    return json.dumps({
        "success": True,
        "url": url,
        "domain": domain,
        "bank": bank_name,
        "status_code": 200,
        "title": page_content["title"],
        "nav_items": page_content["nav_items"],
        "products": page_content["products"],
        "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False)


def _get_bank_page_content(url: str, bank_name: str) -> dict:
    """根据 URL 路径返回对应的页面结构内容"""

    # 个人理财/投资页
    if any(k in url for k in ["licai", "finance", "wealth", "invest", "理财"]):
        return {
            "title": f"{bank_name} - 个人理财",
            "nav_items": ["理财产品", "基金", "债券", "黄金", "外汇", "保险"],
            "products": [
                {"name": "龙财富固收增强系列", "type": "固定收益类", "risk": "R2", "term": "180天", "min_amount": 10000,
                 "annual_rate": "3.45%", "params": ["product_id", "amount", "from_account", "risk_confirm"]},
                {"name": "龙盈稳健配置系列", "type": "混合类", "risk": "R3", "term": "365天", "min_amount": 10000,
                 "annual_rate": "4.10%", "params": ["product_id", "amount", "from_account", "risk_confirm"]},
                {"name": "现金管理类产品", "type": "现金管理", "risk": "R1", "term": "随存随取", "min_amount": 1,
                 "annual_rate": "2.20%", "params": ["product_id", "amount", "from_account"]},
            ],
        }

    # 基金页
    if any(k in url for k in ["fund", "jijin", "基金"]):
        return {
            "title": f"{bank_name} - 基金超市",
            "nav_items": ["货币基金", "债券基金", "混合基金", "股票基金", "指数基金", "QDII"],
            "products": [
                {"name": "某货币A", "code": "000001", "type": "货币型", "risk": "R1",
                 "nav": 1.0000, "min_amount": 1, "ops": ["申购", "赎回"],
                 "params": {"申购": ["fund_code", "amount", "from_account"], "赎回": ["fund_code", "redeem_share", "to_account"]}},
                {"name": "某债券A", "code": "110022", "type": "债券型", "risk": "R2",
                 "nav": 1.2340, "min_amount": 1000, "ops": ["申购", "赎回", "转换"],
                 "params": {"申购": ["fund_code", "amount", "from_account", "risk_confirm"]}},
                {"name": "某混合A", "code": "161725", "type": "混合型", "risk": "R3",
                 "nav": 2.5680, "min_amount": 1000, "ops": ["申购", "赎回", "转换"],
                 "params": {"申购": ["fund_code", "amount", "from_account", "risk_confirm"]}},
            ],
        }

    # 外汇页
    if any(k in url for k in ["forex", "waihui", "exchange", "外汇"]):
        return {
            "title": f"{bank_name} - 外汇业务",
            "nav_items": ["汇率查询", "外汇买卖", "购汇", "结汇", "跨境汇款", "外汇持仓"],
            "products": [
                {"service": "购汇", "desc": "人民币兑换外币", "min_amount": 100,
                 "params": ["from_account", "to_account", "currency", "amount"],
                 "currencies": ["USD", "EUR", "GBP", "JPY", "HKD", "AUD", "CAD"]},
                {"service": "结汇", "desc": "外币兑换人民币", "min_amount": None,
                 "params": ["from_account", "to_account", "currency", "amount"]},
                {"service": "跨境汇款", "desc": "SWIFT国际汇款", "fee": "50元/笔起",
                 "params": ["from_account", "to_bank", "to_account", "to_name", "currency", "amount", "country"],
                 "note": "⚠️ 汇出后不可撤销，请仔细核对收款账号和SWIFT Code"},
                {"service": "外汇汇率", "desc": "实时汇率查询",
                 "params": ["currency_pair", "rate_type"],
                 "rate_types": ["现汇买入", "现汇卖出", "现钞买入", "现钞卖出", "中间价"]},
            ],
        }

    # 贵金属页
    if any(k in url for k in ["gold", "metal", "huangjin", "귀금속", "黄金", "贵金属"]):
        return {
            "title": f"{bank_name} - 贵金属投资",
            "nav_items": ["实时行情", "我的持仓", "买入", "卖出", "历史成交"],
            "products": [
                {"metal": "黄金", "unit": "克", "current_price": 485.50,
                 "params_buy": ["from_account", "metal_type", "amount", "price_type", "risk_confirm"],
                 "params_sell": ["metal_type", "amount", "to_account", "price_type"],
                 "price_types": ["市价", "限价"], "min_amount": 1},
                {"metal": "白银", "unit": "克", "current_price": 5.82,
                 "params_buy": ["from_account", "metal_type", "amount", "price_type", "risk_confirm"],
                 "min_amount": 100},
                {"metal": "铂金", "unit": "克", "current_price": 210.30,
                 "params_buy": ["from_account", "metal_type", "amount", "price_type", "risk_confirm"],
                 "min_amount": 1},
            ],
        }

    # 存款/大额存单页
    if any(k in url for k in ["deposit", "cunkuan", "存款", "大额存单", "largecd"]):
        return {
            "title": f"{bank_name} - 存款产品",
            "nav_items": ["活期存款", "定期存款", "通知存款", "大额存单", "智慧存款"],
            "products": [
                {"name": "定期存款", "min_amount": 50, "terms": ["3个月", "6个月", "1年", "2年", "3年", "5年"],
                 "params_open": ["from_account", "amount", "term", "interest_method", "auto_renew"],
                 "interest_methods": ["到期取息", "按月付息", "按季付息"]},
                {"name": "通知存款", "min_amount": 50000, "types": ["一天通知", "七天通知"],
                 "params_open": ["from_account", "amount", "notice_type"],
                 "params_withdraw": ["deposit_id", "to_account", "withdraw_amount"]},
                {"name": "大额存单", "min_amount": 200000, "terms": ["1个月", "3个月", "6个月", "1年", "2年", "3年"],
                 "params_open": ["from_account", "amount", "term", "interest_method"],
                 "params_withdraw": ["cd_id", "to_account", "withdraw_type"],
                 "withdraw_types": ["到期支取", "提前支取（损失部分利息）"]},
            ],
        }

    # 信用卡页
    if any(k in url for k in ["credit", "xinyongka", "信用卡"]):
        return {
            "title": f"{bank_name} - 信用卡",
            "nav_items": ["账单查询", "还款", "分期", "额度管理", "取现", "特权权益"],
            "services": [
                {"name": "账单查询", "params": ["card_suffix", "bill_month", "bill_type"]},
                {"name": "额度查询", "params": ["card_suffix", "limit_type"]},
                {"name": "信用卡还款", "params": ["card_suffix", "amount", "account_type"]},
                {"name": "账单分期", "params": ["card_suffix", "installment_amount", "installment_periods"],
                 "periods": [3, 6, 12, 24]},
                {"name": "临时额度调整", "params": ["card_suffix", "adjust_amount", "valid_days", "reason"]},
                {"name": "信用卡取现", "min_fee": "每笔1.5%，最低10元",
                 "params": ["card_suffix", "amount", "to_account"]},
                {"name": "取现分期", "params": ["card_suffix", "advance_id", "installment_periods"],
                 "periods": [3, 6, 12]},
            ],
        }

    # 保险页
    if any(k in url for k in ["insur", "baoxian", "保险"]):
        return {
            "title": f"{bank_name} - 保险服务",
            "nav_items": ["寿险", "意外险", "健康险", "财产险", "我的保单"],
            "products": [
                {"name": "某定期寿险", "type": "寿险", "coverage_periods": ["10年", "20年", "30年"],
                 "payment_periods": ["一次性缴清", "10年缴", "20年缴"],
                 "params": ["product_id", "insured_name", "insured_id", "coverage_period", "payment_period", "from_account", "risk_confirm"]},
                {"name": "某意外险", "type": "意外险", "term": "1年",
                 "params": ["product_id", "insured_name", "insured_id", "coverage_period", "payment_period", "from_account", "risk_confirm"]},
                {"name": "某医疗险", "type": "健康险（医疗险）",
                 "params": ["product_id", "insured_name", "insured_id", "coverage_period", "payment_period", "from_account", "risk_confirm"]},
            ],
        }

    # 首页/个人银行默认页
    return {
        "title": f"{bank_name} - 个人网上银行",
        "nav_items": [
            "账户管理", "转账汇款", "信用卡", "贷款服务",
            "理财投资", "外汇业务", "贵金属", "保险服务",
            "基金", "债券", "存款产品", "收款方管理",
            "银行卡管理", "积分权益", "征信查询"
        ],
        "products": [],
        "note": f"这是{bank_name}个人网银首页。请通过 web_fetch 访问具体业务域 URL 获取详细产品信息。",
    }
