from __future__ import annotations
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import db, commit_or_rollback
from models import ProcessProgress
from services import cache_service
from datetime import datetime

progress_bp=Blueprint("progress", __name__, url_prefix="/progress")

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
