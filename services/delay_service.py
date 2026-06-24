from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from models import Order, ProcessProgress
from database import db


@dataclass
class DelayRisk:
    order_id: int
    product_name: str
    customer: str
    ship_date: date
    days_until_ship: int          # 負 = 出荷日超過
    incomplete_processes: list[str]
    overdue_processes: list[str]  # end_date 超過 & 未完了
    level: str                    # critical / high / medium / overdue


def _risk_level(days_until: int, has_incomplete: bool, has_overdue: bool) -> str:
    if not has_incomplete:
        return None
    if days_until < 0:
        return "overdue"    # 出荷日超過 & 未完了
    if days_until <= 3:
        return "critical"   # 3日以内
    if days_until <= 7:
        return "high"       # 7日以内
    if has_overdue:
        return "medium"     # 工程が遅れているが出荷日まで余裕あり
    return None


def get_delay_risks(days_ahead: int = 30) -> list[DelayRisk]:
    """遅延リスクのある受注一覧を返す"""
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)

    # 対象: 未完了工程がある受注（出荷日が未来30日以内 or 既に超過）
    orders = (
        Order.query
        .filter(Order.ship_date <= cutoff)
        .filter(Order.status != "完了")
        .order_by(Order.ship_date.asc())
        .all()
    )

    result = []
    for order in orders:
        progresses = ProcessProgress.query.filter_by(order_id=order.order_id).all()
        if not progresses:
            continue

        incomplete = [p.process_name for p in progresses if p.status != "完了"]
        overdue = [
            p.process_name for p in progresses
            if p.status != "完了" and p.end_date and p.end_date < today
        ]

        days_until = (order.ship_date - today).days
        level = _risk_level(days_until, bool(incomplete), bool(overdue))
        if level is None:
            continue

        result.append(DelayRisk(
            order_id=order.order_id,
            product_name=order.product_name,
            customer=order.customer,
            ship_date=order.ship_date,
            days_until_ship=days_until,
            incomplete_processes=incomplete,
            overdue_processes=overdue,
            level=level,
        ))

    return result


def get_delay_summary() -> dict:
    """ダッシュボード用のサマリ"""
    risks = get_delay_risks(days_ahead=30)
    return {
        "overdue": sum(1 for r in risks if r.level == "overdue"),
        "critical": sum(1 for r in risks if r.level == "critical"),
        "high": sum(1 for r in risks if r.level == "high"),
        "medium": sum(1 for r in risks if r.level == "medium"),
        "total": len(risks),
        "items": risks,
    }
