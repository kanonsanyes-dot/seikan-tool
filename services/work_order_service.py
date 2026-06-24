from __future__ import annotations
from datetime import date, datetime
from database import db
from models import WorkOrder, WorkOrderProcess, ProductProcessStandard, Order


def _next_wo_no() -> str:
    today = date.today().strftime("%Y%m%d")
    prefix = f"WO-{today}-"
    last = (WorkOrder.query
            .filter(WorkOrder.work_order_no.like(f"{prefix}%"))
            .order_by(WorkOrder.work_order_no.desc())
            .first())
    seq = int(last.work_order_no.split("-")[-1]) + 1 if last else 1
    return f"{prefix}{seq:03d}"


def create_work_order(data: dict) -> WorkOrder:
    wo = WorkOrder(
        work_order_no=_next_wo_no(),
        product_name=data["product_name"],
        process_product_name=data.get("process_product_name", ""),
        customer=data.get("customer", ""),
        lot_no=data.get("lot_no", ""),
        quantity=int(data.get("quantity", 0)),
        ship_date=data.get("ship_date"),
        status=data.get("status", "未着手"),
        priority=data.get("priority", "通常"),
        remarks=data.get("remarks", ""),
        order_id=data.get("order_id"),
    )
    db.session.add(wo)
    db.session.flush()
    _generate_processes(wo)
    db.session.commit()
    return wo


def _generate_processes(wo: WorkOrder) -> None:
    standards = (ProductProcessStandard.query
                 .filter_by(product_name=wo.product_name, is_active=True)
                 .order_by(ProductProcessStandard.process_order)
                 .all())
    for s in standards:
        p = WorkOrderProcess(
            work_order_id=wo.work_order_id,
            process_name=s.process_name,
            process_order=s.process_order,
            planned_quantity=wo.quantity,
        )
        db.session.add(p)


def generate_from_order(order: Order) -> WorkOrder | None:
    if WorkOrder.query.filter_by(order_id=order.order_id).first():
        return None
    wo = WorkOrder(
        work_order_no=_next_wo_no(),
        order_id=order.order_id,
        product_name=order.product_name,
        process_product_name=order.process_product_name or "",
        customer=order.customer,
        quantity=order.quantity,
        ship_date=order.ship_date,
        status="未着手",
        priority="通常",
    )
    db.session.add(wo)
    db.session.flush()
    _generate_processes(wo)
    db.session.commit()
    return wo


def update_work_order(wo: WorkOrder, data: dict) -> WorkOrder:
    wo.product_name = data.get("product_name", wo.product_name)
    wo.process_product_name = data.get("process_product_name", wo.process_product_name)
    wo.customer = data.get("customer", wo.customer)
    wo.lot_no = data.get("lot_no", wo.lot_no)
    wo.quantity = int(data.get("quantity", wo.quantity))
    wo.ship_date = data.get("ship_date", wo.ship_date)
    wo.status = data.get("status", wo.status)
    wo.priority = data.get("priority", wo.priority)
    wo.remarks = data.get("remarks", wo.remarks)
    db.session.commit()
    return wo


def update_process_actual(proc: WorkOrderProcess, data: dict) -> WorkOrderProcess:
    def _d(key):
        v = data.get(key, "")
        if not v:
            return None
        try:
            return datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            return None

    def _i(key, default):
        try:
            return int(data.get(key) or default)
        except (ValueError, TypeError):
            return default

    proc.actual_start_date = _d("actual_start_date")
    proc.actual_end_date = _d("actual_end_date")
    proc.input_quantity = _i("input_quantity", proc.input_quantity)
    proc.good_quantity = _i("good_quantity", proc.good_quantity)
    proc.defect_quantity = _i("defect_quantity", proc.defect_quantity)
    proc.status = data.get("status", proc.status)
    proc.operator = data.get("operator", proc.operator)
    proc.equipment = data.get("equipment", proc.equipment)
    proc.remarks = data.get("remarks", proc.remarks)
    db.session.commit()
    return proc


def get_work_order_list(q="", status="", customer="", date_from=None, date_to=None):
    query = WorkOrder.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(WorkOrder.product_name.like(like),
                   WorkOrder.customer.like(like),
                   WorkOrder.lot_no.like(like),
                   WorkOrder.work_order_no.like(like))
        )
    if status:
        query = query.filter(WorkOrder.status == status)
    if customer:
        query = query.filter(WorkOrder.customer.like(f"%{customer}%"))
    if date_from:
        query = query.filter(WorkOrder.ship_date >= date_from)
    if date_to:
        query = query.filter(WorkOrder.ship_date <= date_to)
    return query.order_by(WorkOrder.ship_date.asc().nullslast(),
                          WorkOrder.work_order_id.desc()).all()
