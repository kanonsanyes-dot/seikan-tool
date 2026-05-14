from __future__ import annotations
from flask import Blueprint, render_template, request, jsonify
from models import Order, Schedule
from services.scheduler_service import generate_schedule as svc_generate, serialize_schedule, serialize_order, query_schedules, update_schedule, snap as svc_snap, load_quality_flags
from services.export_service import scheduler_excel
from config.edition import current_limits

scheduler_bp=Blueprint("scheduler", __name__)

@scheduler_bp.route("/scheduler")
def scheduler_view():
    orders=Order.query.order_by(Order.ship_date).limit(100).all()
    return render_template("scheduler/index.html", orders=orders)

@scheduler_bp.route("/api/scheduler/data")
def scheduler_data():
    limits=current_limits()
    q=query_schedules(request.args)
    max_orders=limits.get("max_scheduler_orders") or 20
    schedules=q.limit(max_orders*10).all()
    order_ids=sorted({s.order_id for s in schedules})[:max_orders]
    schedules=[s for s in schedules if s.order_id in order_ids]
    orders=Order.query.filter(Order.order_id.in_(order_ids)).order_by(Order.ship_date).all() if order_ids else []
    if schedules:
        start=min(s.start_date for s in schedules).isoformat(); end=max(s.end_date for s in schedules).isoformat()
    else:
        start=request.args.get("from", ""); end=request.args.get("to", "")
    return jsonify({"orders":[serialize_order(o) for o in orders],"schedules":[serialize_schedule(s) for s in schedules],"range":{"start":start,"end":end}})

@scheduler_bp.route("/api/scheduler/generate/<int:order_id>", methods=["POST"])
def generate(order_id):
    try:
        schedules=svc_generate(order_id)
        return jsonify({"ok":True,"schedules":[serialize_schedule(s) for s in schedules]})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)}), 400

@scheduler_bp.route("/api/scheduler/<int:schedule_id>", methods=["PATCH"])
def patch_schedule(schedule_id):
    data=request.get_json(force=True)
    try:
        s=update_schedule(schedule_id, data.get("start_date"), data.get("end_date"), data.get("status"), data.get("locked") if "locked" in data else None)
        return jsonify({"ok":True,"schedule":serialize_schedule(s)})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)}), 400

@scheduler_bp.route("/api/scheduler/snap", methods=["POST"])
def snap():
    data=request.get_json(force=True)
    try:
        return jsonify(svc_snap(data.get("schedule_id"), data.get("start_date"), data.get("end_date")))
    except Exception as e:
        return jsonify({"snapped":False,"error":str(e)}), 400

@scheduler_bp.route("/api/scheduler/load/<int:order_id>")
def quality(order_id):
    return jsonify(load_quality_flags(order_id))

@scheduler_bp.route("/scheduler/export/excel")
def export_excel():
    schedules=query_schedules(request.args).limit(1000).all()
    return scheduler_excel(schedules)

@scheduler_bp.route("/scheduler/print")
def print_view():
    schedules=query_schedules(request.args).limit(200).all()
    return render_template("scheduler/print.html", schedules=schedules)
