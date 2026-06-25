from __future__ import annotations
from pathlib import Path
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import asc, desc
from database import db, commit_or_rollback
from models import Order
from services.csv_import_service import import_orders, ImportErrorDetail, add_missing_masters
from services.quality_check_service import recheck_all
from services.export_service import orders_excel
from services import cache_service

orders_bp = Blueprint("orders", __name__, url_prefix="/orders")
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"

@orders_bp.route("")
def list_orders():
    q=Order.query
    f=request.args
    if f.get("customer"): q=q.filter(Order.customer.contains(f.get("customer")))
    if f.get("product"): q=q.filter(Order.product_name.contains(f.get("product")))
    if f.get("status"): q=q.filter(Order.status==f.get("status"))
    if f.get("quality"): q=q.filter(Order.data_quality==f.get("quality"))
    if f.get("date_from"): q=q.filter(Order.ship_date>=f.get("date_from"))
    if f.get("date_to"): q=q.filter(Order.ship_date<=f.get("date_to"))
    sort=f.get("sort","ship_date"); direction=f.get("dir","asc")
    col={"ship_date":Order.ship_date,"quantity":Order.quantity,"customer":Order.customer}.get(sort, Order.ship_date)
    q=q.order_by(desc(col) if direction=="desc" else asc(col))
    page=request.args.get("page",1,type=int)
    pagination=q.paginate(page=page, per_page=20, error_out=False)
    return render_template("orders/list.html", pagination=pagination, orders=pagination.items, f=f)

@orders_bp.route("/import", methods=["GET","POST"])
def import_view():
    result=None
    if request.method=="POST":
        try:
            from services.scheduler_service import generate_schedule
            result=import_orders(request.files.get("file"), UPLOAD_DIR)
            sched_ok = sched_err = 0
            for oid in result.get("order_ids", []):
                try:
                    generate_schedule(oid)
                    sched_ok += 1
                except Exception:
                    sched_err += 1
            flash(
                f"CSV取込完了: 成功{result['success']}件 / エラー{result['error_count']}件 / 照合NG{result['ng_count']}件"
                + f"  ▶ スケジュール自動生成: {sched_ok}件"
                + (f" (失敗 {sched_err}件)" if sched_err else ""),
                "success"
            )
        except ImportErrorDetail as e:
            flash(str(e), "danger")
        except Exception as e:
            flash(f"取込中にエラー: {e}", "danger")
    return render_template("orders/import.html", result=result)

@orders_bp.route("/add_missing_masters", methods=["POST"])
def add_missing():
    customers=request.form.getlist("customers")
    products=request.form.getlist("products")
    add_missing_masters(customers, products)
    recheck_all(Order.query.all()); commit_or_rollback(); cache_service.clear()
    flash("未登録マスタを追加し、品質チェックを再実行しました。", "success")
    return redirect(url_for("orders.list_orders"))

@orders_bp.route("/<int:order_id>/edit", methods=["GET","POST"])
def edit_order(order_id):
    order=db.session.get(Order, order_id)
    if not order:
        return jsonify({"error":"not found"}), 404
    if request.method=="GET":
        return jsonify({"order_id":order.order_id,"product_name":order.product_name,"process_product_name":order.process_product_name,"customer":order.customer,"ship_date":order.ship_date.isoformat(),"quantity":order.quantity,"status":order.status,"data_quality":order.data_quality})
    try:
        order.product_name=request.form.get("product_name", order.product_name)
        order.process_product_name=request.form.get("process_product_name")
        order.customer=request.form.get("customer", order.customer)
        ship_date = request.form.get("ship_date")
        if ship_date:
            order.ship_date = datetime.fromisoformat(ship_date).date()
        order.quantity=int(request.form.get("quantity", order.quantity))
        order.status=request.form.get("status", order.status)
        recheck_all([order]); commit_or_rollback(); cache_service.clear()
        flash("受注を更新しました。", "success")
    except Exception as e:
        db.session.rollback(); flash(f"受注の更新に失敗しました: {e}", "danger")
    return redirect(url_for("orders.list_orders"))

@orders_bp.route("/<int:order_id>/delete", methods=["POST"])
def delete_order(order_id):
    order=db.session.get(Order, order_id)
    if order:
        db.session.delete(order); commit_or_rollback(); cache_service.clear(); flash("受注を削除しました。", "success")
    return redirect(url_for("orders.list_orders"))

@orders_bp.route("/export")
def export_orders():
    return orders_excel(Order.query.order_by(Order.ship_date))

@orders_bp.route("/quality_check", methods=["POST"])
def quality_check():
    recheck_all(Order.query.all()); commit_or_rollback(); cache_service.clear()
    flash("データ品質チェックを一括実行しました。", "success")
    return redirect(url_for("orders.list_orders"))


@orders_bp.route("/import-xls", methods=["GET", "POST"])
def import_xls():
    from services.xls_import_service import parse_xls_file, import_to_db
    preview = None
    result = None
    skip_zero = True

    if request.method == "POST":
        action = request.form.get("action", "preview")
        skip_zero = request.form.get("skip_zero_remaining", "1") == "1"

        if action == "preview":
            f = request.files.get("file")
            if not f or not f.filename:
                flash("ファイルを選択してください。", "danger")
                return render_template("orders/import_xls.html", preview=None, result=None)
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            fpath = UPLOAD_DIR / "tmp_import.xls"
            f.save(str(fpath))
            try:
                records = parse_xls_file(str(fpath))
                if skip_zero:
                    records = [r for r in records if r["remaining_qty"] > 0]
                preview = records
                flash(f"{len(records)} 件を読み込みました。内容を確認して「取込実行」してください。", "info")
                import json
                from flask import session
                session["xls_import_path"] = str(fpath)
                session["xls_skip_zero"] = skip_zero
            except Exception as e:
                flash(f"ファイル解析エラー: {e}", "danger")

        elif action == "import":
            from flask import session
            from services.scheduler_service import generate_schedule
            fpath = session.get("xls_import_path")
            skip_zero = session.get("xls_skip_zero", True)
            if not fpath:
                flash("セッションが切れました。再度ファイルを選択してください。", "danger")
                return redirect(url_for("orders.import_xls"))
            try:
                records = parse_xls_file(fpath)
                result = import_to_db(records, skip_zero_remaining=skip_zero)

                # 新規登録受注に対してスケジュール・進捗・ガント用データを自動生成
                sched_ok = sched_err = 0
                for oid in result.get("order_ids", []):
                    try:
                        generate_schedule(oid)
                        sched_ok += 1
                    except Exception:
                        sched_err += 1

                msg = (
                    f"取込完了: 登録 {result['imported']}件 / スキップ {result['skipped']}件"
                    + (f" / エラー {len(result['errors'])}件" if result["errors"] else "")
                    + f"  ▶ スケジュール自動生成: {sched_ok}件"
                    + (f" (失敗 {sched_err}件)" if sched_err else "")
                )
                level = "success" if not result["errors"] and not sched_err else "warning"
                flash(msg, level)
            except Exception as e:
                flash(f"取込エラー: {e}", "danger")
            return redirect(url_for("orders.list_orders"))

    return render_template("orders/import_xls.html", preview=preview, result=result, skip_zero=skip_zero)
