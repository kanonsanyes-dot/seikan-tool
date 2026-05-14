from __future__ import annotations
from flask import Blueprint, render_template, request
from sqlalchemy import func
from database import db
from models import Order
from services.export_service import summary_excel

reports_bp=Blueprint("reports", __name__, url_prefix="/reports")

def _to_json_rows(rows):
    """Jinjaのtojsonで落ちないよう、SQLAlchemy Rowを素のlistへ変換する。"""
    return [[label or "未設定", int(total or 0)] for label, total in rows]

def _month_filter(query, target_month):
    if target_month:
        return query.filter(func.strftime('%Y-%m', Order.ship_date)==target_month)
    return query

def build_summary(target_month=None, monthly_scope="all"):
    """
    集計レポート用データを作る。

    monthly_scope:
      - "all"      : 月別タブは全期間推移を表示する（標準）
      - "filtered" : 月別タブもtarget_monthで絞る

    客先別・品名別はtarget_month指定時に対象月で絞る。
    月別タブは、会議用の推移確認として全期間表示が見やすいケースが多いため、
    既定値はallにしている。
    """
    base_q=Order.query
    filtered_q=_month_filter(base_q, target_month)

    monthly_base = filtered_q if monthly_scope == "filtered" else base_q

    monthly_q=monthly_base.with_entities(
        func.strftime('%Y-%m', Order.ship_date).label('m'),
        func.sum(Order.quantity)
    ).group_by('m').order_by('m').all()

    customer_q=filtered_q.with_entities(
        Order.customer,
        func.sum(Order.quantity)
    ).group_by(Order.customer).order_by(func.sum(Order.quantity).desc()).all()

    product_q=filtered_q.with_entities(
        Order.product_name,
        func.sum(Order.quantity)
    ).group_by(Order.product_name).order_by(func.sum(Order.quantity).desc()).all()

    return _to_json_rows(monthly_q), _to_json_rows(customer_q), _to_json_rows(product_q)

@reports_bp.route("/summary")
def summary():
    month=request.args.get("month")
    monthly_scope=request.args.get("monthly_scope", "all")
    if monthly_scope not in {"all", "filtered"}:
        monthly_scope="all"
    monthly, customer, product=build_summary(month, monthly_scope)
    return render_template(
        "reports/summary.html",
        monthly=monthly,
        customer=customer,
        product=product,
        month=month,
        monthly_scope=monthly_scope,
    )

@reports_bp.route("/summary/export")
def export_summary():
    monthly_scope=request.args.get("monthly_scope", "all")
    if monthly_scope not in {"all", "filtered"}:
        monthly_scope="all"
    monthly, customer, product=build_summary(request.args.get("month"), monthly_scope)
    return summary_excel(monthly, customer, product)
