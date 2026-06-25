from __future__ import annotations
from collections import defaultdict
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database import db, commit_or_rollback
from models import Order, ProcessProgress, ProcessMaster, Schedule, QualityIssue
from services import cache_service

progress_bp = Blueprint("progress", __name__, url_prefix="/progress")
progress_api_bp = Blueprint("progress_api", __name__)


@progress_bp.route("")
def index():
    from models import ProcessMaster
    processes = ProcessMaster.query.filter_by(is_active=True).order_by(ProcessMaster.display_order).all()
    process_names = [p.process_name for p in processes]
    if not process_names:
        from models import DEFAULT_PROCESSES
        process_names = DEFAULT_PROCESSES

    today = date.today()
    active_filter = request.args.get("status", "active")

    q = ProcessProgress.query.join(Order)
    if active_filter == "active":
        q = q.filter(Order.status.notin_(["完了", "キャンセル"]))
    elif active_filter == "inprogress":
        q = q.filter(ProcessProgress.status == "進行中")
    elif active_filter == "overdue":
        q = q.filter(ProcessProgress.end_date < today, ProcessProgress.status != "完了")

    rows = q.order_by(ProcessProgress.end_date, ProcessProgress.process_order).limit(500).all()

    # カンバン列構築: {process_name: [rows]}
    kanban = defaultdict(list)
    for r in rows:
        kanban[r.process_name].append(r)

    return render_template(
        "progress/index.html",
        process_names=process_names,
        kanban=kanban,
        active_filter=active_filter,
        today=today,
    )


@progress_bp.route("/<int:id>/detail")
def detail(id):
    p = db.session.get(ProcessProgress, id)
    if not p:
        return "Not found", 404
    return render_template("progress/detail.html", p=p, order=p.order, today=date.today())


@progress_bp.route("/<int:id>/update", methods=["POST"])
def update(id):
    p = db.session.get(ProcessProgress, id)
    if p:
        p.status = request.form.get("status", p.status)
        actual = request.form.get("actual_end_date")
        p.actual_end_date = datetime.fromisoformat(actual).date() if actual else None
        p.completed_qty = int(request.form.get("completed_qty") or p.completed_qty or 0)
        p.department = request.form.get("department")
        p.remarks = request.form.get("remarks")
        commit_or_rollback()
        cache_service.clear()
        flash("進捗を更新しました。", "success")
    return redirect(url_for("progress.index"))

def _iso_or_none(value):
    return value.isoformat() if value else None

def _serialize_process(progress):
    return {
        "progress_id": progress.progress_id,
        "process_name": progress.process_name,
        "process_order": progress.process_order,
        "start_date": _iso_or_none(progress.start_date),
        "end_date": _iso_or_none(progress.end_date),
        "actual_end_date": _iso_or_none(progress.actual_end_date),
        "status": progress.status,
        "quantity": progress.quantity,
        "completed_qty": progress.completed_qty or 0,
        "department": progress.department or "",
        "remarks": progress.remarks or "",
    }

@progress_api_bp.route("/api/progress/gantt")
def gantt_data():
    rows=(
        db.session.query(ProcessProgress)
        .join(Order, ProcessProgress.order_id == Order.order_id)
        .order_by(Order.ship_date.asc(), ProcessProgress.order_id.asc(), ProcessProgress.process_order.asc())
        .limit(1000)
        .all()
    )
    grouped={}
    for row in rows:
        order=row.order
        if order.order_id not in grouped:
            grouped[order.order_id] = {
                "order_id": order.order_id,
                "order_no": order.order_no or "",
                "product_name": order.product_name,
                "process_product_name": order.process_product_name or "",
                "customer": order.customer,
                "ship_date": _iso_or_none(order.ship_date),
                "quantity": order.quantity or 0,
                "remaining_qty": order.remaining_qty,
                "product_category": order.product_category or "",
                "status": order.status or "受注中",
                "data_quality": order.data_quality or "",
                "processes": [],
            }
        grouped[order.order_id]["processes"].append(_serialize_process(row))
    return jsonify({"orders": list(grouped.values()), "today": date.today().isoformat()})

def _patch_progress_dates(progress_id, data):
    try:
        start_date=datetime.fromisoformat(data.get("start_date", "")).date()
        end_date=datetime.fromisoformat(data.get("end_date", "")).date()
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "start_date / end_date が不正です"}), 400
    if start_date > end_date:
        return jsonify({"ok": False, "error": "start_date は end_date 以前にしてください"}), 400
    progress=db.session.get(ProcessProgress, progress_id)
    if not progress:
        return jsonify({"ok": False, "error": "進捗がありません"}), 404
    progress.start_date=start_date
    progress.end_date=end_date
    try:
        commit_or_rollback(); cache_service.clear()
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    return jsonify({"ok": True})

@progress_api_bp.route("/api/progress/gantt/<int:progress_id>", methods=["PATCH"])
def patch_gantt(progress_id):
    return _patch_progress_dates(progress_id, request.get_json(force=True) or {})

@progress_api_bp.route("/api/progress/gantt/", methods=["PATCH"])
def patch_gantt_with_body_id():
    data = request.get_json(force=True) or {}
    try:
        progress_id = int(data.get("progress_id", 0))
    except (TypeError, ValueError):
        progress_id = 0
    if not progress_id:
        return jsonify({"ok": False, "error": "progress_id が必要です"}), 400
    return _patch_progress_dates(progress_id, data)


@progress_api_bp.route("/api/progress/<int:progress_id>", methods=["PATCH"])
def patch_progress(progress_id):
    data = request.get_json(force=True) or {}
    p = db.session.get(ProcessProgress, progress_id)
    if not p:
        return jsonify({"ok": False, "error": "進捗がありません"}), 404
    if "status" in data:
        p.status = data["status"]
    if "completed_qty" in data:
        p.completed_qty = int(data["completed_qty"] or 0)
    if "remarks" in data:
        p.remarks = data["remarks"]
    commit_or_rollback()
    cache_service.clear()
    return jsonify({"ok": True, "status": p.status, "completed_qty": p.completed_qty})


@progress_api_bp.route("/api/alerts")
def alerts():
    """全アラート集計: キャパ超過・遅延リスク・品質異常"""
    today = date.today()
    items = []

    # 遅延リスク
    from services.delay_service import get_delay_summary
    delay = get_delay_summary()
    if delay.get("overdue", 0) > 0:
        items.append({
            "level": "danger",
            "category": "遅延",
            "message": f"出荷日超過 {delay['overdue']}件の未完了工程があります",
            "url": "/delay",
        })
    if delay.get("critical", 0) > 0:
        items.append({
            "level": "warning",
            "category": "遅延リスク",
            "message": f"出荷日まで3日以内 {delay['critical']}件",
            "url": "/delay",
        })

    # 品質異常
    qi_open = QualityIssue.query.filter(QualityIssue.status != "完了").count()
    qi_overdue = QualityIssue.query.filter(
        QualityIssue.due_date < today, QualityIssue.status != "完了"
    ).count()
    if qi_overdue > 0:
        items.append({
            "level": "danger",
            "category": "品質異常",
            "message": f"期限超過の品質異常が {qi_overdue}件あります",
            "url": "/quality-issues",
        })
    elif qi_open > 0:
        items.append({
            "level": "warning",
            "category": "品質異常",
            "message": f"未完了の品質異常が {qi_open}件あります",
            "url": "/quality-issues",
        })

    # キャパ超過（当日〜7日の負荷サマリから）
    try:
        from services.scheduler_service import get_load_summary
        end = today + timedelta(days=14)
        load = get_load_summary(today, end)
        over_processes = []
        for proc, days in load.items():
            for d, info in days.items():
                if info.get("status") == "over":
                    over_processes.append(proc)
                    break
        if over_processes:
            procs = "、".join(sorted(set(over_processes))[:4])
            items.append({
                "level": "danger",
                "category": "キャパ超過",
                "message": f"工程キャパ超過: {procs}",
                "url": "/scheduler",
            })
    except Exception:
        pass

    # 進行中で期限超過の工程
    overdue_prog = ProcessProgress.query.filter(
        ProcessProgress.end_date < today,
        ProcessProgress.status.in_(["未着手", "進行中"]),
    ).count()
    if overdue_prog > 0:
        items.append({
            "level": "warning",
            "category": "工程遅延",
            "message": f"予定終了日を過ぎた工程が {overdue_prog}件あります",
            "url": "/progress",
        })

    return jsonify({"alerts": items, "total": len(items)})
