from __future__ import annotations
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import db
from models import MeasurementRecord

meas_bp = Blueprint("measurements", __name__, url_prefix="/measurements")

RESULT_LIST = ["OK", "NG", "要確認"]


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


@meas_bp.route("")
def list_measurements():
    q = request.args.get("q", "").strip()
    result = request.args.get("result", "").strip()
    date_from = _parse_date(request.args.get("date_from", ""))
    date_to = _parse_date(request.args.get("date_to", ""))
    query = MeasurementRecord.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(MeasurementRecord.product_name.like(like),
                   MeasurementRecord.lot_no.like(like),
                   MeasurementRecord.measurement_item.like(like))
        )
    if result:
        query = query.filter(MeasurementRecord.result == result)
    if date_from:
        query = query.filter(MeasurementRecord.measured_date >= date_from)
    if date_to:
        query = query.filter(MeasurementRecord.measured_date <= date_to)
    items = query.order_by(MeasurementRecord.measured_date.desc().nullslast(),
                           MeasurementRecord.measurement_id.desc()).all()
    ng_count = sum(1 for i in items if i.result == "NG")
    return render_template("measurements/list.html",
                           items=items, q=q, result=result,
                           date_from=request.args.get("date_from", ""),
                           date_to=request.args.get("date_to", ""),
                           ng_count=ng_count, result_list=RESULT_LIST)


@meas_bp.route("/new", methods=["GET", "POST"])
def new_measurement():
    work_order_id = request.args.get("work_order_id", type=int)
    process_id = request.args.get("process_id", type=int)
    if request.method == "POST":
        m = MeasurementRecord(
            work_order_id=request.form.get("work_order_id", type=int),
            process_id=request.form.get("process_id", type=int),
            product_name=request.form.get("product_name", "").strip(),
            lot_no=request.form.get("lot_no", "").strip(),
            measured_date=_parse_date(request.form.get("measured_date")),
            measurement_item=request.form.get("measurement_item", "").strip(),
            result=request.form.get("result", "").strip(),
            file_path=request.form.get("file_path", "").strip(),
            storage_note=request.form.get("storage_note", "").strip(),
            inspector=request.form.get("inspector", "").strip(),
            remarks=request.form.get("remarks", "").strip(),
        )
        if not m.product_name:
            flash("品名は必須です。", "danger")
            return render_template("measurements/form.html", m=None,
                                   work_order_id=work_order_id, process_id=process_id,
                                   result_list=RESULT_LIST)
        db.session.add(m)
        try:
            db.session.commit()
            flash("測定記録を登録しました。", "success")
            if m.work_order_id:
                return redirect(url_for("work_orders.detail", wo_id=m.work_order_id))
            return redirect(url_for("measurements.list_measurements"))
        except Exception as e:
            db.session.rollback()
            flash(f"登録エラー: {e}", "danger")
    return render_template("measurements/form.html", m=None,
                           work_order_id=work_order_id, process_id=process_id,
                           result_list=RESULT_LIST)


@meas_bp.route("/<int:meas_id>")
def detail(meas_id):
    m = MeasurementRecord.query.get_or_404(meas_id)
    return render_template("measurements/detail.html", m=m)


@meas_bp.route("/<int:meas_id>/edit", methods=["GET", "POST"])
def edit_measurement(meas_id):
    m = MeasurementRecord.query.get_or_404(meas_id)
    if request.method == "POST":
        m.product_name = request.form.get("product_name", "").strip()
        m.lot_no = request.form.get("lot_no", "").strip()
        m.measured_date = _parse_date(request.form.get("measured_date"))
        m.measurement_item = request.form.get("measurement_item", "").strip()
        m.result = request.form.get("result", "").strip()
        m.file_path = request.form.get("file_path", "").strip()
        m.storage_note = request.form.get("storage_note", "").strip()
        m.inspector = request.form.get("inspector", "").strip()
        m.remarks = request.form.get("remarks", "").strip()
        try:
            db.session.commit()
            flash("更新しました。", "success")
            return redirect(url_for("measurements.detail", meas_id=meas_id))
        except Exception as e:
            db.session.rollback()
            flash(f"更新エラー: {e}", "danger")
    return render_template("measurements/form.html", m=m,
                           work_order_id=m.work_order_id, process_id=m.process_id,
                           result_list=RESULT_LIST)
