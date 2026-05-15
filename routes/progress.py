from __future__ import annotations
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database import db, commit_or_rollback
from models import Order, ProcessProgress
from services import cache_service

progress_bp=Blueprint("progress", __name__, url_prefix="/progress")
progress_api_bp=Blueprint("progress_api", __name__)

@progress_bp.route("")
def index():
    process=request.args.get("process")
    q=ProcessProgress.query
    if process: q=q.filter(ProcessProgress.process_name==process)
    rows=q.order_by(ProcessProgress.end_date, ProcessProgress.process_order).limit(300).all()
    return render_template("progress/index.html", rows=rows, process=process)

@progress_bp.route("/<int:id>/update", methods=["POST"])
def update(id):
    p=db.session.get(ProcessProgress,id)
    if p:
        p.status=request.form.get("status",p.status)
        actual=request.form.get("actual_end_date")
        p.actual_end_date=datetime.fromisoformat(actual).date() if actual else None
        p.department=request.form.get("department")
        p.remarks=request.form.get("remarks")
        commit_or_rollback(); cache_service.clear(); flash("進捗を更新しました。", "success")
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
            grouped[order.order_id]={
                "order_id": order.order_id,
                "product_name": order.product_name,
                "customer": order.customer,
                "ship_date": _iso_or_none(order.ship_date),
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
    data=request.get_json(force=True) or {}
    try:
        progress_id=int(data.get("progress_id", 0))
    except (TypeError, ValueError):
        progress_id=0
    if not progress_id:
        return jsonify({"ok": False, "error": "progress_id が必要です"}), 400
    return _patch_progress_dates(progress_id, data)
