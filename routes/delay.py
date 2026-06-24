from __future__ import annotations
from flask import Blueprint, render_template, request, jsonify
from services.delay_service import get_delay_risks, get_delay_summary

delay_bp = Blueprint("delay", __name__, url_prefix="/delay")


@delay_bp.route("")
def index():
    days_ahead = int(request.args.get("days", 30))
    risks = get_delay_risks(days_ahead=days_ahead)
    overdue = [r for r in risks if r.level == "overdue"]
    critical = [r for r in risks if r.level == "critical"]
    high = [r for r in risks if r.level == "high"]
    medium = [r for r in risks if r.level == "medium"]
    return render_template(
        "delay/index.html",
        overdue=overdue,
        critical=critical,
        high=high,
        medium=medium,
        total=len(risks),
        days_ahead=days_ahead,
    )


@delay_bp.route("/api/summary")
def api_summary():
    s = get_delay_summary()
    return jsonify({
        "overdue": s["overdue"],
        "critical": s["critical"],
        "high": s["high"],
        "medium": s["medium"],
        "total": s["total"],
    })
