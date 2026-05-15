from __future__ import annotations
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import db, commit_or_rollback
from models import Customer, Product, ProductProcessStandard, ProcessCapacity, Order
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
