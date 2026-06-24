from __future__ import annotations
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import func
from database import db
from models import QualityIssue, WorkOrder

qi_bp = Blueprint("quality_issues", __name__, url_prefix="/quality-issues")

STATUS_LIST = ["調査中", "対策中", "確認待ち", "完了", "保留"]
ISSUE_TYPES = ["寸法不良", "外観不良", "機能不良", "材料不良", "工程異常", "設備異常", "その他"]


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _next_issue_no():
    today = date.today().strftime("%Y%m%d")
    prefix = f"QI-{today}-"
    last = (QualityIssue.query
            .filter(QualityIssue.issue_no.like(f"{prefix}%"))
            .order_by(QualityIssue.issue_no.desc())
            .first())
    seq = int(last.issue_no.split("-")[-1]) + 1 if last else 1
    return f"{prefix}{seq:03d}"


@qi_bp.route("")
def list_issues():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    today = date.today()
    query = QualityIssue.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(QualityIssue.product_name.like(like),
                   QualityIssue.process_name.like(like),
                   QualityIssue.lot_no.like(like),
                   QualityIssue.issue_no.like(like))
        )
    if status:
        query = query.filter(QualityIssue.status == status)
    items = query.order_by(QualityIssue.occurred_date.desc().nullslast(),
                           QualityIssue.issue_id.desc()).all()
    overdue = sum(1 for i in items if i.due_date and i.due_date < today and i.status != "完了")
    open_count = sum(1 for i in items if i.status != "完了")
    return render_template("quality_issues/list.html",
                           items=items, today=today, q=q, status=status,
                           overdue=overdue, open_count=open_count,
                           status_list=STATUS_LIST)


@qi_bp.route("/new", methods=["GET", "POST"])
def new_issue():
    work_order_id = request.args.get("work_order_id", type=int)
    process_id = request.args.get("process_id", type=int)
    if request.method == "POST":
        issue = QualityIssue(
            issue_no=_next_issue_no(),
            work_order_id=request.form.get("work_order_id", type=int),
            process_id=request.form.get("process_id", type=int),
            order_id=request.form.get("order_id", type=int),
            occurred_date=_parse_date(request.form.get("occurred_date")),
            process_name=request.form.get("process_name", "").strip(),
            product_name=request.form.get("product_name", "").strip(),
            lot_no=request.form.get("lot_no", "").strip(),
            issue_type=request.form.get("issue_type", "").strip(),
            detail=request.form.get("detail", "").strip(),
            temporary_action=request.form.get("temporary_action", "").strip(),
            root_cause=request.form.get("root_cause", "").strip(),
            corrective_action=request.form.get("corrective_action", "").strip(),
            owner=request.form.get("owner", "").strip(),
            due_date=_parse_date(request.form.get("due_date")),
            status=request.form.get("status", "調査中"),
        )
        if not issue.product_name:
            flash("品名は必須です。", "danger")
            return render_template("quality_issues/form.html", issue=None,
                                   work_order_id=work_order_id, process_id=process_id,
                                   status_list=STATUS_LIST, issue_types=ISSUE_TYPES)
        db.session.add(issue)
        try:
            db.session.commit()
            flash(f"品質異常 {issue.issue_no} を登録しました。", "success")
            if issue.work_order_id:
                return redirect(url_for("work_orders.detail", wo_id=issue.work_order_id))
            return redirect(url_for("quality_issues.list_issues"))
        except Exception as e:
            db.session.rollback()
            flash(f"登録エラー: {e}", "danger")
    return render_template("quality_issues/form.html", issue=None,
                           work_order_id=work_order_id, process_id=process_id,
                           status_list=STATUS_LIST, issue_types=ISSUE_TYPES)


@qi_bp.route("/<int:issue_id>")
def detail(issue_id):
    issue = QualityIssue.query.get_or_404(issue_id)
    today = date.today()
    return render_template("quality_issues/detail.html", issue=issue, today=today)


@qi_bp.route("/<int:issue_id>/edit", methods=["GET", "POST"])
def edit_issue(issue_id):
    issue = QualityIssue.query.get_or_404(issue_id)
    if request.method == "POST":
        issue.occurred_date = _parse_date(request.form.get("occurred_date"))
        issue.process_name = request.form.get("process_name", "").strip()
        issue.product_name = request.form.get("product_name", "").strip()
        issue.lot_no = request.form.get("lot_no", "").strip()
        issue.issue_type = request.form.get("issue_type", "").strip()
        issue.detail = request.form.get("detail", "").strip()
        issue.temporary_action = request.form.get("temporary_action", "").strip()
        issue.root_cause = request.form.get("root_cause", "").strip()
        issue.corrective_action = request.form.get("corrective_action", "").strip()
        issue.owner = request.form.get("owner", "").strip()
        issue.due_date = _parse_date(request.form.get("due_date"))
        issue.close_date = _parse_date(request.form.get("close_date"))
        issue.status = request.form.get("status", issue.status)
        try:
            db.session.commit()
            flash("更新しました。", "success")
            return redirect(url_for("quality_issues.detail", issue_id=issue_id))
        except Exception as e:
            db.session.rollback()
            flash(f"更新エラー: {e}", "danger")
    return render_template("quality_issues/form.html", issue=issue,
                           work_order_id=issue.work_order_id, process_id=issue.process_id,
                           status_list=STATUS_LIST, issue_types=ISSUE_TYPES)


@qi_bp.route("/api/summary")
def api_summary():
    by_type = (db.session.query(QualityIssue.issue_type, func.count())
               .filter(QualityIssue.issue_type != None, QualityIssue.issue_type != "")
               .group_by(QualityIssue.issue_type)
               .order_by(func.count().desc()).all())
    by_process = (db.session.query(QualityIssue.process_name, func.count())
                  .filter(QualityIssue.process_name != None, QualityIssue.process_name != "")
                  .group_by(QualityIssue.process_name)
                  .order_by(func.count().desc()).limit(10).all())
    by_status = (db.session.query(QualityIssue.status, func.count())
                 .group_by(QualityIssue.status).all())
    return jsonify({
        "by_type": [{"label": t or "未分類", "count": c} for t, c in by_type],
        "by_process": [{"label": p or "-", "count": c} for p, c in by_process],
        "by_status": [{"label": s, "count": c} for s, c in by_status],
    })
