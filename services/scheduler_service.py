from __future__ import annotations
from datetime import date, datetime, timedelta
from collections import defaultdict
import math
from database import db, commit_or_rollback
from models import Order, ProductProcessStandard, ProcessMaster, Schedule, ProcessProgress, Anomaly
from services import cache_service

DEFAULT_PROCESSES = ["プレス", "バレル", "めっき", "外観検査", "出荷"]

# ── キャパシティ取得 ──────────────────────────────────────────────

def _get_process_capacity_map() -> dict[str, dict]:
    """ProcessMasterから工程ごとの能力を返す {process_name: {daily, overtime_daily, hours, pace}}"""
    caps = {}
    for pm in ProcessMaster.query.filter_by(is_active=True).all():
        daily = int(pm.hours_per_day * pm.pace_per_hour) if pm.pace_per_hour else 0
        overtime_daily = int((pm.hours_per_day + pm.overtime_hours) * pm.pace_per_hour) if pm.pace_per_hour else 0
        caps[pm.process_name] = {
            "daily": daily,
            "overtime_daily": overtime_daily,
            "hours": pm.hours_per_day,
            "overtime_hours": pm.overtime_hours,
            "pace": pm.pace_per_hour,
        }
    return caps


def _skip_weekends(d: date, backward: bool = False) -> date:
    delta = -1 if backward else 1
    while d.weekday() >= 5:
        d += timedelta(days=delta)
    return d


def _prev_workday(d: date) -> date:
    d -= timedelta(days=1)
    return _skip_weekends(d, backward=True)


# ── 工程標準取得 ──────────────────────────────────────────────────

def get_standards_for(order):
    standards = (ProductProcessStandard.query
                 .filter_by(product_name=order.product_name, is_active=True)
                 .order_by(ProductProcessStandard.process_order).all())
    if standards:
        return standards
    class Std: pass
    arr = []
    for i, p in enumerate(DEFAULT_PROCESSES, 1):
        s = Std()
        s.process_name = p; s.process_order = i
        s.standard_time_min = 0.5; s.daily_capacity = 800
        s.pace_per_hour = 0; s.hours_per_run = 8.0
        arr.append(s)
    return arr


# ── 単一受注のスケジュール生成（後ろ倒し）─────────────────────────

def generate_schedule(order_id: int):
    order = db.session.get(Order, order_id)
    if not order:
        raise ValueError("受注がありません")
    standards = get_standards_for(order)
    cap_map = _get_process_capacity_map()
    qty = order.remaining_qty or order.quantity

    end_date = _skip_weekends(order.ship_date, backward=True)
    Schedule.query.filter_by(order_id=order_id).delete()
    ProcessProgress.query.filter_by(order_id=order_id).delete()

    for std in reversed(standards):
        pm_cap = cap_map.get(std.process_name, {})
        # 優先: ProductProcessStandard.daily_capacity, 次: ProcessMaster計算値, フォールバック: 800
        daily = (getattr(std, "daily_capacity", 0) or 0)
        if not daily and pm_cap.get("daily"):
            daily = pm_cap["daily"]
        if not daily:
            daily = 800

        required_days = max(math.ceil(qty / daily), 1)
        start_date = end_date
        # required_days分だけ土日を除いて戻る
        days_counted = 0
        cur = end_date
        while days_counted < required_days:
            if cur.weekday() < 5:
                days_counted += 1
                if days_counted < required_days:
                    cur -= timedelta(days=1)
                    cur = _skip_weekends(cur, backward=True)
            else:
                cur -= timedelta(days=1)
        start_date = cur

        sched = Schedule(
            order_id=order_id, process_name=std.process_name, process_order=std.process_order,
            start_date=start_date, end_date=end_date, required_days=required_days, status="未着手"
        )
        prog = ProcessProgress(
            order_id=order_id, product_name=order.product_name, quantity=qty,
            process_name=std.process_name, process_order=std.process_order,
            start_date=start_date, end_date=end_date, ship_date=order.ship_date, status="未着手"
        )
        db.session.add(sched); db.session.add(prog)
        end_date = _prev_workday(start_date)

    commit_or_rollback(); cache_service.clear()
    return Schedule.query.filter_by(order_id=order_id).order_by(Schedule.process_order).all()


# ── 全受注一括スケジュール生成 ─────────────────────────────────────

def generate_all_schedules(overwrite: bool = False) -> dict:
    orders = (Order.query
              .filter(Order.status.notin_(["完了", "キャンセル"]))
              .order_by(Order.ship_date)
              .all())
    generated = skipped = errors = 0
    for order in orders:
        if not overwrite and Schedule.query.filter_by(order_id=order.order_id).first():
            skipped += 1
            continue
        try:
            generate_schedule(order.order_id)
            generated += 1
        except Exception:
            errors += 1
    return {"generated": generated, "skipped": skipped, "errors": errors}


# ── 負荷サマリ計算 ─────────────────────────────────────────────────

def get_load_summary(start_date: date, end_date: date) -> dict:
    """
    指定期間の工程別・日別負荷を計算。
    Returns {
      process_name: {
        "YYYY-MM-DD": {"qty": int, "status": "ok"|"overtime"|"over"}
      }
    }
    """
    cap_map = _get_process_capacity_map()

    # その期間のScheduleを取得
    schedules = (Schedule.query
                 .join(Order)
                 .filter(Schedule.end_date >= start_date, Schedule.start_date <= end_date)
                 .all())

    # 日別・工程別の処理数量を集計
    load: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for s in schedules:
        qty = s.order.remaining_qty or s.order.quantity
        working_days = max(s.required_days or 1, 1)
        daily_qty = math.ceil(qty / working_days)
        cur = s.start_date
        while cur <= s.end_date:
            if cur.weekday() < 5:
                load[s.process_name][cur.isoformat()] += daily_qty
            cur += timedelta(days=1)

    result = {}
    all_processes = {s.process_name for s in schedules}
    for proc in all_processes:
        caps = cap_map.get(proc, {})
        daily_cap = caps.get("daily", 0)
        overtime_cap = caps.get("overtime_daily", 0) or daily_cap
        result[proc] = {}
        for date_str, qty in load[proc].items():
            if daily_cap == 0:
                status = "unknown"
            elif qty <= daily_cap:
                status = "ok"
            elif qty <= overtime_cap:
                status = "overtime"
            else:
                status = "over"
            result[proc][date_str] = {
                "qty": qty,
                "capacity": daily_cap,
                "overtime_capacity": overtime_cap,
                "status": status,
                "load_pct": round(qty / daily_cap * 100) if daily_cap else None,
            }

    return result


# ── 直近の負荷サマリ（週次集計）─────────────────────────────────────

def get_weekly_load(start_date: date, weeks: int = 8) -> dict:
    end_date = start_date + timedelta(weeks=weeks)
    daily = get_load_summary(start_date, end_date)
    weekly: dict[str, list] = {}
    for proc, day_data in daily.items():
        weeks_data = defaultdict(lambda: {"qty": 0, "capacity": 0, "overtime_capacity": 0})
        for date_str, info in day_data.items():
            d = datetime.fromisoformat(date_str).date()
            week_start = d - timedelta(days=d.weekday())
            key = week_start.isoformat()
            weeks_data[key]["qty"] += info["qty"]
            weeks_data[key]["capacity"] += info["capacity"]
            weeks_data[key]["overtime_capacity"] += info["overtime_capacity"]
        weekly[proc] = [
            {"week": k, **v,
             "status": (
                 "ok" if v["capacity"] == 0 else
                 "over" if v["qty"] > v["overtime_capacity"] else
                 "overtime" if v["qty"] > v["capacity"] else "ok"
             ),
             "load_pct": round(v["qty"] / v["capacity"] * 100) if v["capacity"] else None
             }
            for k, v in sorted(weeks_data.items())
        ]
    return weekly


# ── シリアライズ ──────────────────────────────────────────────────

def serialize_schedule(s):
    return {
        "schedule_id": s.schedule_id, "order_id": s.order_id,
        "product_name": s.order.product_name, "customer": s.order.customer,
        "quantity": s.order.remaining_qty or s.order.quantity,
        "ship_date": s.order.ship_date.isoformat(),
        "process_name": s.process_name, "process_order": s.process_order,
        "start_date": s.start_date.isoformat(), "end_date": s.end_date.isoformat(),
        "required_days": s.required_days, "status": s.status,
        "has_quality_issue": bool(s.has_quality_issue),
        "quality_issue_detail": s.quality_issue_detail,
        "locked": bool(s.locked),
    }


def serialize_order(o):
    return {
        "order_id": o.order_id, "product_name": o.product_name,
        "process_product_name": o.process_product_name,
        "customer": o.customer, "ship_date": o.ship_date.isoformat(),
        "quantity": o.quantity, "remaining_qty": o.remaining_qty,
        "status": o.status, "data_quality": o.data_quality,
    }


def query_schedules(args):
    q = Schedule.query.join(Order)
    month = args.get("month")
    if month:
        from datetime import timedelta
        start = datetime.strptime(month + "-01", "%Y-%m-%d").date()
        end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) + timedelta(days=92)
        q = q.filter(Schedule.end_date >= start, Schedule.start_date <= end)
    if args.get("customer"):
        q = q.filter(Order.customer.contains(args.get("customer")))
    if args.get("product"):
        q = q.filter(Order.product_name.contains(args.get("product")))
    return q.order_by(Order.ship_date, Schedule.process_order)


def update_schedule(schedule_id, start_date, end_date, status=None, locked=None):
    s = db.session.get(Schedule, schedule_id)
    if not s:
        raise ValueError("スケジュールがありません")
    if s.locked and locked is None:
        raise ValueError("ロック済みのカードです")
    s.start_date = datetime.fromisoformat(start_date).date() if isinstance(start_date, str) else start_date
    s.end_date = datetime.fromisoformat(end_date).date() if isinstance(end_date, str) else end_date
    s.required_days = (s.end_date - s.start_date).days + 1
    if status:
        s.status = status
    if locked is not None:
        s.locked = bool(locked)
    p = ProcessProgress.query.filter_by(order_id=s.order_id, process_order=s.process_order).first()
    if p:
        p.start_date = s.start_date; p.end_date = s.end_date; p.status = s.status
    commit_or_rollback(); cache_service.clear()
    return s


def snap(schedule_id, start_date, end_date, threshold=3):
    s = db.session.get(Schedule, schedule_id)
    if not s:
        raise ValueError("スケジュールがありません")
    st = datetime.fromisoformat(start_date).date()
    en = datetime.fromisoformat(end_date).date()
    prev = Schedule.query.filter_by(order_id=s.order_id, process_order=s.process_order - 1).first()
    if not prev:
        return {"snapped": False, "start_date": st.isoformat(), "end_date": en.isoformat()}
    target = prev.end_date + timedelta(days=1)
    diff = abs((st - target).days)
    if diff <= threshold:
        duration = (en - st).days
        return {"snapped": True, "start_date": target.isoformat(),
                "end_date": (target + timedelta(days=duration)).isoformat()}
    return {"snapped": False, "start_date": st.isoformat(), "end_date": en.isoformat()}


def load_quality_flags(order_id):
    an = Anomaly.query.filter(Anomaly.order_id == order_id,
                              Anomaly.status.in_(["未対策", "調査中"])).first()
    if an:
        Schedule.query.filter_by(order_id=order_id).update(
            {"has_quality_issue": True, "quality_issue_detail": an.detail})
        commit_or_rollback(); cache_service.clear()
        return {"has_issue": True, "issue_detail": an.detail}
    return {"has_issue": False}
