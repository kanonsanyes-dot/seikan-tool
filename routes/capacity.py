from __future__ import annotations
from datetime import date
from flask import Blueprint, render_template, request, jsonify
from services.capacity_service import get_capacity_summary, get_monthly_loads, get_overtime_simulation, get_monthly_trend

capacity_bp = Blueprint("capacity", __name__, url_prefix="/capacity")


@capacity_bp.route("")
def index():
    today = date.today()
    year = int(request.args.get("year", today.year))
    month = int(request.args.get("month", today.month))
    summary = get_capacity_summary(year, month)

    # 月ナビ用
    prev_year, prev_month = (year, month - 1) if month > 1 else (year - 1, 12)
    next_year, next_month = (year, month + 1) if month < 12 else (year + 1, 1)

    return render_template(
        "capacity/index.html",
        summary=summary,
        year=year,
        month=month,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
    )


@capacity_bp.route("/api/summary")
def api_summary():
    today = date.today()
    year = int(request.args.get("year", today.year))
    month = int(request.args.get("month", today.month))
    summary = get_capacity_summary(year, month)
    return jsonify({
        "year": year,
        "month": month,
        "total_orders": summary.total_orders,
        "total_quantity": summary.total_quantity,
        "bottleneck": summary.bottleneck,
        "process_loads": [
            {
                "process_name": p.process_name,
                "process_order": p.process_order,
                "required_hours": p.required_hours,
                "available_hours": p.available_hours,
                "overtime_hours": p.overtime_hours,
                "load_rate": p.load_rate,
                "required_overtime": p.required_overtime,
                "status": p.status,
            }
            for p in summary.process_loads
        ],
    })


@capacity_bp.route("/api/monthly")
def api_monthly():
    months = int(request.args.get("months", 6))
    return jsonify(get_monthly_loads(months))


@capacity_bp.route("/api/overtime-simulation")
def api_overtime_simulation():
    today = date.today()
    year = int(request.args.get("year", today.year))
    month = int(request.args.get("month", today.month))
    return jsonify(get_overtime_simulation(year, month))


@capacity_bp.route("/api/trend")
def api_trend():
    months = int(request.args.get("months", 6))
    return jsonify(get_monthly_trend(months))
