from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from calendar import monthrange
from typing import Optional
from sqlalchemy import func
from database import db
from models import Order, ProductProcessStandard, ProcessCapacity, ProcessProgress

DEFAULT_DAILY_HOURS = 8.0
DEFAULT_WORKING_DAYS = 20


@dataclass
class ProcessLoad:
    process_name: str
    process_order: int
    required_hours: float
    available_hours: float
    overtime_hours: float  # available overtime capacity
    load_rate: float        # required / available * 100
    required_overtime: float  # max(0, required - available_normal)
    status: str             # ok / caution / overtime / critical

    @property
    def available_normal(self) -> float:
        return self.available_hours

    @property
    def can_cover_with_overtime(self) -> bool:
        return self.required_hours <= (self.available_hours + self.overtime_hours)


@dataclass
class CapacitySummary:
    year: int
    month: int
    total_orders: int
    total_quantity: int
    process_loads: list[ProcessLoad] = field(default_factory=list)
    bottleneck: Optional[str] = None

    @property
    def critical_processes(self) -> list[ProcessLoad]:
        return [p for p in self.process_loads if p.status in ("overtime", "critical")]


def _load_status(load_rate: float) -> str:
    if load_rate < 80:
        return "ok"
    if load_rate < 100:
        return "caution"
    if load_rate < 120:
        return "overtime"
    return "critical"


def get_capacity_summary(year: int, month: int) -> CapacitySummary:
    month_start = date(year, month, 1)
    last_day = monthrange(year, month)[1]
    month_end = date(year, month, last_day)

    # 対象月に出荷予定の受注
    orders = (
        Order.query
        .filter(Order.ship_date >= month_start, Order.ship_date <= month_end)
        .all()
    )
    total_quantity = sum(o.quantity for o in orders)

    # 品名 → 標準マスタ
    standards = ProductProcessStandard.query.filter_by(is_active=True).all()
    std_map: dict[tuple[str, str], ProductProcessStandard] = {
        (s.product_name, s.process_name): s for s in standards
    }
    # 工程ごとに必要工数を積算
    process_required: dict[str, float] = {}
    process_order_map: dict[str, int] = {}
    for order in orders:
        order_stds = [s for s in standards if s.product_name == order.product_name]
        for std in order_stds:
            pname = std.process_name
            hours = order.quantity * (std.standard_time_min or 0) / 60.0
            process_required[pname] = process_required.get(pname, 0.0) + hours
            process_order_map[pname] = std.process_order

    # 工程キャパマスタから月内の稼働時間集計
    cap_rows = (
        ProcessCapacity.query
        .filter(ProcessCapacity.work_date >= month_start, ProcessCapacity.work_date <= month_end)
        .all()
    )
    cap_normal: dict[str, float] = {}
    cap_overtime: dict[str, float] = {}
    for cap in cap_rows:
        pname = cap.process_name
        cap_normal[pname] = cap_normal.get(pname, 0.0) + (cap.available_hours or 0)
        cap_overtime[pname] = cap_overtime.get(pname, 0.0) + (cap.overtime_hours or 0)

    # 稼働日数ベースのデフォルト（キャパマスタ未登録の場合）
    working_days = _count_working_days(month_start, month_end)

    process_loads = []
    for pname, req_hours in sorted(process_required.items(), key=lambda x: process_order_map.get(x[0], 99)):
        avail = cap_normal.get(pname)
        if avail is None:
            avail = DEFAULT_DAILY_HOURS * working_days
        ot = cap_overtime.get(pname, 0.0)
        load_rate = (req_hours / avail * 100) if avail > 0 else 0.0
        required_ot = max(0.0, req_hours - avail)
        process_loads.append(ProcessLoad(
            process_name=pname,
            process_order=process_order_map.get(pname, 99),
            required_hours=round(req_hours, 1),
            available_hours=round(avail, 1),
            overtime_hours=round(ot, 1),
            load_rate=round(load_rate, 1),
            required_overtime=round(required_ot, 1),
            status=_load_status(load_rate),
        ))

    bottleneck = None
    if process_loads:
        worst = max(process_loads, key=lambda p: p.load_rate)
        if worst.load_rate >= 100:
            bottleneck = worst.process_name

    return CapacitySummary(
        year=year,
        month=month,
        total_orders=len(orders),
        total_quantity=total_quantity,
        process_loads=process_loads,
        bottleneck=bottleneck,
    )


def get_monthly_loads(months: int = 6) -> list[dict]:
    """直近 N ヶ月の工程別負荷率サマリを返す（ダッシュボード用）"""
    today = date.today()
    result = []
    y, m = today.year, today.month
    for _ in range(months):
        summary = get_capacity_summary(y, m)
        result.append({
            "year": y,
            "month": m,
            "label": f"{y}/{m:02d}",
            "total_orders": summary.total_orders,
            "total_quantity": summary.total_quantity,
            "process_loads": [
                {
                    "process_name": p.process_name,
                    "load_rate": p.load_rate,
                    "status": p.status,
                }
                for p in summary.process_loads
            ],
            "bottleneck": summary.bottleneck,
        })
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(result))


def _count_working_days(start: date, end: date) -> int:
    from datetime import timedelta
    count = 0
    current = start
    while current <= end:
        if current.weekday() < 5:  # 月〜金
            count += 1
        current += timedelta(days=1)
    return count
