from __future__ import annotations
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import db, commit_or_rollback
from models import Customer, Product, ProductProcessStandard, ProcessCapacity, ProcessMaster, DEFAULT_PROCESSES, Order
from services.quality_check_service import recheck_all
from services import cache_service
from datetime import datetime

masters_bp=Blueprint("masters", __name__, url_prefix="/masters")

@masters_bp.route("/customers")
def customers():
    return render_template("masters/customers.html", customers=Customer.query.order_by(Customer.customer_name).all())

@masters_bp.route("/customers/add", methods=["POST"])
def add_customer():
    name=request.form.get("customer_name","").strip()
    if name and not Customer.query.filter_by(customer_name=name).first():
        db.session.add(Customer(customer_name=name, is_active=True)); commit_or_rollback(); cache_service.clear(); flash("出荷先を追加しました。", "success")
    return redirect(url_for("masters.customers"))

@masters_bp.route("/customers/<int:id>/edit", methods=["POST"])
def edit_customer(id):
    c=db.session.get(Customer,id)
    if c:
        c.customer_name=request.form.get("customer_name",c.customer_name); c.is_active=bool(request.form.get("is_active")); commit_or_rollback(); cache_service.clear(); recheck_all(Order.query.all()); commit_or_rollback()
        flash("出荷先を更新しました。", "success")
    return redirect(url_for("masters.customers"))

@masters_bp.route("/customers/<int:id>/delete", methods=["POST"])
def delete_customer(id):
    c=db.session.get(Customer,id)
    if c: db.session.delete(c); commit_or_rollback(); cache_service.clear(); flash("出荷先を削除しました。", "success")
    return redirect(url_for("masters.customers"))

@masters_bp.route("/products")
def products():
    return render_template("masters/products.html", products=Product.query.order_by(Product.product_name).all())

@masters_bp.route("/products/add", methods=["POST"])
def add_product():
    name=request.form.get("product_name","").strip()
    if name and not Product.query.filter_by(product_name=name).first():
        db.session.add(Product(product_name=name, process_product_name=request.form.get("process_product_name"), is_active=True)); commit_or_rollback(); cache_service.clear(); flash("品名を追加しました。", "success")
    return redirect(url_for("masters.products"))

@masters_bp.route("/products/<int:id>/edit", methods=["POST"])
def edit_product(id):
    p=db.session.get(Product,id)
    if p:
        p.product_name=request.form.get("product_name",p.product_name); p.process_product_name=request.form.get("process_product_name"); p.is_active=bool(request.form.get("is_active")); commit_or_rollback(); cache_service.clear(); recheck_all(Order.query.all()); commit_or_rollback(); flash("品名を更新しました。", "success")
    return redirect(url_for("masters.products"))

@masters_bp.route("/products/<int:id>/delete", methods=["POST"])
def delete_product(id):
    p=db.session.get(Product,id)
    if p: db.session.delete(p); commit_or_rollback(); cache_service.clear(); flash("品名を削除しました。", "success")
    return redirect(url_for("masters.products"))

@masters_bp.route("/process-standards")
def standards():
    return render_template("masters/process_standards.html", standards=ProductProcessStandard.query.order_by(ProductProcessStandard.product_name, ProductProcessStandard.process_order).all())

@masters_bp.route("/process-standards/add", methods=["POST"])
def add_standard():
    product_name=request.form.get("product_name", "").strip()
    process_name=request.form.get("process_name", "").strip()
    if not product_name or not process_name:
        flash("品名と工程名は必須です。", "danger")
        return redirect(url_for("masters.standards"))
    if ProductProcessStandard.query.filter_by(product_name=product_name, process_name=process_name).first():
        flash("同じ品名・工程名の工程標準は既に登録されています。", "warning")
        return redirect(url_for("masters.standards"))
    try:
        s=ProductProcessStandard(product_name=product_name, process_product_name=request.form.get("process_product_name"), process_name=process_name, process_order=int(request.form.get("process_order",1)), standard_time_min=float(request.form.get("standard_time_min",0) or 0), daily_capacity=int(request.form.get("daily_capacity",0) or 0), lot_size=int(request.form.get("lot_size",0) or 0), is_active=True, remarks=request.form.get("remarks"))
        db.session.add(s); commit_or_rollback(); cache_service.clear(); flash("工程標準を追加しました。", "success")
    except Exception as e:
        db.session.rollback(); flash(f"工程標準の追加に失敗しました: {e}", "danger")
    return redirect(url_for("masters.standards"))

@masters_bp.route("/process-standards/<int:id>/delete", methods=["POST"])
def delete_standard(id):
    s=db.session.get(ProductProcessStandard,id)
    if s: db.session.delete(s); commit_or_rollback(); cache_service.clear(); flash("工程標準を削除しました。", "success")
    return redirect(url_for("masters.standards"))

@masters_bp.route("/process-capacity")
def capacity():
    return render_template("masters/process_capacity.html", capacities=ProcessCapacity.query.order_by(ProcessCapacity.work_date.desc()).limit(200).all())

@masters_bp.route("/process-capacity/add", methods=["POST"])
def add_capacity():
    process_name=request.form.get("process_name", "").strip()
    work_date_raw=request.form.get("work_date", "")
    if not process_name or not work_date_raw:
        flash("工程名と稼働日は必須です。", "danger")
        return redirect(url_for("masters.capacity"))
    try:
        work_date=datetime.fromisoformat(work_date_raw).date()
        if ProcessCapacity.query.filter_by(process_name=process_name, work_date=work_date).first():
            flash("同じ工程名・稼働日の工程キャパは既に登録されています。", "warning")
            return redirect(url_for("masters.capacity"))
        c=ProcessCapacity(process_name=process_name, work_date=work_date, available_hours=float(request.form.get("available_hours",8) or 8), workers=int(request.form.get("workers",1) or 1), overtime_hours=float(request.form.get("overtime_hours",0) or 0), capacity_quantity=int(request.form.get("capacity_quantity",0) or 0), remarks=request.form.get("remarks"))
        db.session.add(c); commit_or_rollback(); cache_service.clear(); flash("工程キャパを追加しました。", "success")
    except Exception as e:
        db.session.rollback(); flash(f"工程キャパの追加に失敗しました: {e}", "danger")
    return redirect(url_for("masters.capacity"))

@masters_bp.route("/process-capacity/<int:id>/delete", methods=["POST"])
def delete_capacity(id):
    c=db.session.get(ProcessCapacity,id)
    if c: db.session.delete(c); commit_or_rollback(); cache_service.clear(); flash("工程キャパを削除しました。", "success")
    return redirect(url_for("masters.capacity"))


# ─── 工程マスタ ──────────────────────────────────────────────────
@masters_bp.route("/process-masters")
def process_masters():
    masters = ProcessMaster.query.order_by(ProcessMaster.display_order).all()
    return render_template("masters/process_masters.html",
                           masters=masters, default_processes=DEFAULT_PROCESSES)

@masters_bp.route("/process-masters/add", methods=["POST"])
def add_process_master():
    name = request.form.get("process_name", "").strip()
    if not name:
        flash("工程名は必須です。", "danger")
        return redirect(url_for("masters.process_masters"))
    if ProcessMaster.query.filter_by(process_name=name).first():
        flash("同名の工程が既に存在します。", "warning")
        return redirect(url_for("masters.process_masters"))
    last = ProcessMaster.query.order_by(ProcessMaster.display_order.desc()).first()
    order = (last.display_order + 1) if last else 1
    pm = ProcessMaster(
        process_name=name, display_order=order,
        hours_per_day=float(request.form.get("hours_per_day", 8) or 8),
        overtime_hours=float(request.form.get("overtime_hours", 0) or 0),
        pace_per_hour=int(request.form.get("pace_per_hour", 0) or 0),
        is_active=True,
        remarks=request.form.get("remarks", ""),
    )
    db.session.add(pm)
    commit_or_rollback()
    flash(f"工程「{name}」を追加しました。", "success")
    return redirect(url_for("masters.process_masters"))

@masters_bp.route("/process-masters/<int:pid>/edit", methods=["POST"])
def edit_process_master(pid):
    pm = db.session.get(ProcessMaster, pid)
    if not pm:
        flash("工程が見つかりません。", "danger")
        return redirect(url_for("masters.process_masters"))
    pm.process_name = request.form.get("process_name", pm.process_name).strip()
    pm.hours_per_day = float(request.form.get("hours_per_day", pm.hours_per_day) or pm.hours_per_day)
    pm.overtime_hours = float(request.form.get("overtime_hours", 0) or 0)
    pm.pace_per_hour = int(request.form.get("pace_per_hour", 0) or 0)
    pm.is_active = bool(request.form.get("is_active"))
    pm.remarks = request.form.get("remarks", "")
    commit_or_rollback()
    flash("工程を更新しました。", "success")
    return redirect(url_for("masters.process_masters"))

@masters_bp.route("/process-masters/<int:pid>/delete", methods=["POST"])
def delete_process_master(pid):
    pm = db.session.get(ProcessMaster, pid)
    if pm:
        db.session.delete(pm); commit_or_rollback()
        flash("工程を削除しました。", "success")
    return redirect(url_for("masters.process_masters"))

@masters_bp.route("/process-masters/import-excel", methods=["POST"])
def import_capacity_excel():
    from pathlib import Path
    f = request.files.get("file")
    if not f or not f.filename:
        flash("ファイルを選択してください。", "danger")
        return redirect(url_for("masters.process_masters"))
    fpath = Path("/tmp") / "capacity_import.xlsx"
    f.save(str(fpath))
    try:
        from openpyxl import load_workbook
        wb = load_workbook(str(fpath), data_only=True)
        ws = wb.active
        imported = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[0]:
                continue
            name = str(row[0]).strip()
            hours = float(row[1] or 8)
            overtime = float(row[2] or 0)
            pace = int(row[3] or 0) if len(row) > 3 else 0
            pm = ProcessMaster.query.filter_by(process_name=name).first()
            if pm:
                pm.hours_per_day = hours; pm.overtime_hours = overtime; pm.pace_per_hour = pace
            else:
                last = ProcessMaster.query.order_by(ProcessMaster.display_order.desc()).first()
                ord_ = (last.display_order + 1) if last else 1
                db.session.add(ProcessMaster(
                    process_name=name, display_order=ord_,
                    hours_per_day=hours, overtime_hours=overtime, pace_per_hour=pace, is_active=True
                ))
            imported += 1
        commit_or_rollback()
        flash(f"{imported} 件の工程キャパシティを取込しました。", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"インポートエラー: {e}", "danger")
    return redirect(url_for("masters.process_masters"))


# ─── 品名工程テンプレート ──────────────────────────────────────────
@masters_bp.route("/product-templates")
def product_templates():
    p_masters = ProcessMaster.query.filter_by(is_active=True).order_by(ProcessMaster.display_order).all()
    products = db.session.query(ProductProcessStandard.product_name).distinct().all()
    product_names = [p[0] for p in products]
    from models import Product
    all_products = Product.query.filter_by(is_active=True).order_by(Product.product_name).all()
    for ap in all_products:
        if ap.product_name not in product_names:
            product_names.append(ap.product_name)
    return render_template("masters/product_templates.html",
                           process_masters=p_masters,
                           product_names=sorted(product_names))

@masters_bp.route("/product-templates/<path:product_name>")
def product_template_detail(product_name):
    p_masters = ProcessMaster.query.filter_by(is_active=True).order_by(ProcessMaster.display_order).all()
    standards = {s.process_name: s for s in
                 ProductProcessStandard.query.filter_by(product_name=product_name).all()}
    return render_template("masters/product_template_edit.html",
                           product_name=product_name,
                           process_masters=p_masters,
                           standards=standards)

@masters_bp.route("/product-templates/<path:product_name>/save", methods=["POST"])
def save_product_template(product_name):
    p_masters = ProcessMaster.query.filter_by(is_active=True).order_by(ProcessMaster.display_order).all()
    selected = set(request.form.getlist("processes"))
    for i, pm in enumerate(p_masters, start=1):
        existing = ProductProcessStandard.query.filter_by(
            product_name=product_name, process_name=pm.process_name).first()
        if pm.process_name in selected:
            hours = float(request.form.get(f"hours_{pm.process_id}", pm.hours_per_day) or pm.hours_per_day)
            pace = int(request.form.get(f"pace_{pm.process_id}", pm.pace_per_hour) or 0)
            daily = int(hours * pace) if pace else 0
            if existing:
                existing.process_order = i; existing.hours_per_run = hours
                existing.pace_per_hour = pace; existing.daily_capacity = daily; existing.is_active = True
            else:
                db.session.add(ProductProcessStandard(
                    product_name=product_name, process_name=pm.process_name,
                    process_order=i, hours_per_run=hours, pace_per_hour=pace,
                    daily_capacity=daily, is_active=True,
                ))
        else:
            if existing:
                db.session.delete(existing)
    commit_or_rollback()
    flash(f"「{product_name}」の工程テンプレートを保存しました。", "success")
    return redirect(url_for("masters.product_template_detail", product_name=product_name))

@masters_bp.route("/process-masters/capacity-template")
def download_capacity_template():
    from io import BytesIO
    from flask import send_file
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        wb = Workbook()
        ws = wb.active
        ws.title = "工程キャパ"
        hdr_fill = PatternFill("solid", fgColor="2563EB")
        hdr_font = Font(bold=True, color="FFFFFF")
        headers = ["工程名", "定時h/日", "残業h/日", "pcs/h（ペース）"]
        ws.append(headers)
        for i, h in enumerate(headers, 1):
            cell = ws.cell(1, i)
            cell.fill = hdr_fill; cell.font = hdr_font
            cell.alignment = Alignment(horizontal="center")
        from models import ProcessMaster
        for pm in ProcessMaster.query.order_by(ProcessMaster.display_order).all():
            ws.append([pm.process_name, pm.hours_per_day, pm.overtime_hours, pm.pace_per_hour])
        for col, width in zip("ABCD", [20, 12, 12, 16]):
            ws.column_dimensions[col].width = width
        buf = BytesIO(); wb.save(buf); buf.seek(0)
        return send_file(buf, as_attachment=True, download_name="工程キャパシティ_テンプレート.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        flash(f"テンプレート生成エラー: {e}", "danger")
        return redirect(url_for("masters.process_masters"))
