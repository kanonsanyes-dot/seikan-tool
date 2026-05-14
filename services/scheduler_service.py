from __future__ import annotations
from datetime import date, datetime, timedelta
import math
from sqlalchemy import and_
from database import db
from models import Order, ProductProcessStandard, Schedule, ProcessProgress, Anomaly
from services import cache_service

DEFAULT_PROCESSES = ["プレス", "バレル", "めっき", "外観検査", "出荷"]

def get_standards_for(order):
    standards = ProductProcessStandard.query.filter_by(product_name=order.product_name, is_active=True).order_by(ProductProcessStandard.process_order).all()
    if standards:
        return standards
    # 標準未整備でもデバッグできるよう仮工程を返す
    class Std: pass
    arr=[]
    for i,p in enumerate(DEFAULT_PROCESSES,1):
        s=Std(); s.process_name=p; s.process_order=i; s.standard_time_min=0.5; s.daily_capacity=800
        arr.append(s)
    return arr

def generate_schedule(order_id:int):
    order = db.session.get(Order, order_id)
    if not order:
        raise ValueError("受注がありません")
    standards = get_standards_for(order)
    end_date = order.ship_date
    created=[]
    Schedule.query.filter_by(order_id=order_id).delete()
    ProcessProgress.query.filter_by(order_id=order_id).delete()
    for std in reversed(standards):
        cap = std.daily_capacity or 800
        hours = (order.quantity * (std.standard_time_min or 0.5) / 60)
        required_days = max(math.ceil(hours / 8), math.ceil(order.quantity / cap), 1)
        start_date = end_date - timedelta(days=required_days-1)
        sched=Schedule(order_id=order_id, process_name=std.process_name, process_order=std.process_order, start_date=start_date, end_date=end_date, required_days=required_days, status="未着手")
        prog=ProcessProgress(order_id=order_id, product_name=order.product_name, quantity=order.quantity, process_name=std.process_name, process_order=std.process_order, start_date=start_date, end_date=end_date, ship_date=order.ship_date, status="未着手")
        db.session.add(sched); db.session.add(prog); created.insert(0,sched)
        end_date = start_date - timedelta(days=1)
    db.session.commit(); cache_service.clear()
    return Schedule.query.filter_by(order_id=order_id).order_by(Schedule.process_order).all()

def serialize_schedule(s):
    return {"schedule_id":s.schedule_id,"order_id":s.order_id,"product_name":s.order.product_name,"customer":s.order.customer,"quantity":s.order.quantity,"ship_date":s.order.ship_date.isoformat(),"process_name":s.process_name,"process_order":s.process_order,"start_date":s.start_date.isoformat(),"end_date":s.end_date.isoformat(),"required_days":s.required_days,"status":s.status,"has_quality_issue":bool(s.has_quality_issue),"quality_issue_detail":s.quality_issue_detail,"locked":bool(s.locked)}

def serialize_order(o):
    return {"order_id":o.order_id,"product_name":o.product_name,"process_product_name":o.process_product_name,"customer":o.customer,"ship_date":o.ship_date.isoformat(),"quantity":o.quantity,"status":o.status,"data_quality":o.data_quality}

def query_schedules(args):
    q=Schedule.query.join(Order)
    month=args.get("month")
    if month:
        start=datetime.strptime(month+"-01","%Y-%m-%d").date()
        end=(start.replace(day=28)+timedelta(days=4)).replace(day=1)+timedelta(days=92)
        q=q.filter(Schedule.end_date>=start, Schedule.start_date<=end)
    if args.get("customer"): q=q.filter(Order.customer.contains(args.get("customer")))
    if args.get("product"): q=q.filter(Order.product_name.contains(args.get("product")))
    return q.order_by(Order.ship_date, Schedule.process_order)

def update_schedule(schedule_id, start_date, end_date, status=None, locked=None):
    s=db.session.get(Schedule, schedule_id)
    if not s: raise ValueError("スケジュールがありません")
    if s.locked and locked is None: raise ValueError("ロック済みのカードです")
    s.start_date=datetime.fromisoformat(start_date).date() if isinstance(start_date,str) else start_date
    s.end_date=datetime.fromisoformat(end_date).date() if isinstance(end_date,str) else end_date
    s.required_days=(s.end_date-s.start_date).days+1
    if status: s.status=status
    if locked is not None: s.locked=bool(locked)
    p=ProcessProgress.query.filter_by(order_id=s.order_id, process_order=s.process_order).first()
    if p:
        p.start_date=s.start_date; p.end_date=s.end_date; p.status=s.status
    db.session.commit(); cache_service.clear()
    return s

def snap(schedule_id, start_date, end_date, threshold=3):
    s=db.session.get(Schedule, schedule_id)
    if not s: raise ValueError("スケジュールがありません")
    st=datetime.fromisoformat(start_date).date(); en=datetime.fromisoformat(end_date).date()
    prev=Schedule.query.filter_by(order_id=s.order_id, process_order=s.process_order-1).first()
    if not prev: return {"snapped":False,"start_date":st.isoformat(),"end_date":en.isoformat()}
    target=prev.end_date+timedelta(days=1)
    diff=abs((st-target).days)
    if diff<=threshold:
        duration=(en-st).days
        return {"snapped":True,"start_date":target.isoformat(),"end_date":(target+timedelta(days=duration)).isoformat()}
    return {"snapped":False,"start_date":st.isoformat(),"end_date":en.isoformat()}

def load_quality_flags(order_id):
    an=Anomaly.query.filter(Anomaly.order_id==order_id, Anomaly.status.in_(["未対策","調査中"])).first()
    if an:
        Schedule.query.filter_by(order_id=order_id).update({"has_quality_issue":True,"quality_issue_detail":an.detail})
        db.session.commit(); cache_service.clear()
        return {"has_issue":True,"issue_detail":an.detail}
    return {"has_issue":False}
