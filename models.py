from __future__ import annotations
from datetime import datetime, timezone
from database import db

def utc_now():
    return datetime.now(timezone.utc)

class TimestampMixin:
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

class Order(db.Model, TimestampMixin):
    __tablename__ = "orders"
    order_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_name = db.Column(db.String(255), nullable=False)
    process_product_name = db.Column(db.String(255))
    customer = db.Column(db.String(255), nullable=False)
    ship_date = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="受注中")
    data_quality = db.Column(db.String(50), default="未チェック")
    # 拡張フィールド（受注Excelインポート対応）
    order_no = db.Column(db.String(100))
    order_date = db.Column(db.Date)
    remaining_qty = db.Column(db.Integer)
    product_category = db.Column(db.String(100))
    sales_category = db.Column(db.String(100))
    sales_person = db.Column(db.String(100))
    unit_price = db.Column(db.Float)
    amount = db.Column(db.Float)
    remarks = db.Column(db.Text)
    schedules = db.relationship("Schedule", backref="order", cascade="all, delete-orphan", lazy=True)
    progresses = db.relationship("ProcessProgress", backref="order", cascade="all, delete-orphan", lazy=True)
    anomalies = db.relationship("Anomaly", backref="order", cascade="all, delete-orphan", lazy=True)
    work_orders = db.relationship("WorkOrder", backref="order_ref", lazy=True)

class Customer(db.Model):
    __tablename__ = "customers"
    customer_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_name = db.Column(db.String(255), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

class Product(db.Model):
    __tablename__ = "products"
    product_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_name = db.Column(db.String(255), nullable=False, unique=True)
    process_product_name = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

DEFAULT_PROCESSES = [
    "受注", "部材発注", "部材受入", "プレス工程", "外観検査",
    "洗浄", "バレル", "めっき", "計量", "梱包", "出荷",
]

class ProcessMaster(db.Model, TimestampMixin):
    __tablename__ = "process_masters"
    process_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    process_name = db.Column(db.String(100), unique=True, nullable=False)
    display_order = db.Column(db.Integer, default=0)
    hours_per_day = db.Column(db.Float, default=8.0)
    overtime_hours = db.Column(db.Float, default=0.0)
    pace_per_hour = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    remarks = db.Column(db.Text)


class ProductProcessStandard(db.Model, TimestampMixin):
    __tablename__ = "product_process_standards"
    __table_args__ = (
        db.UniqueConstraint("product_name", "process_name", name="uq_standard_product_process"),
    )
    standard_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_name = db.Column(db.String(255), nullable=False)
    process_product_name = db.Column(db.String(255))
    process_name = db.Column(db.String(100), nullable=False)
    process_order = db.Column(db.Integer, nullable=False)
    standard_time_min = db.Column(db.Float, default=0.0)
    daily_capacity = db.Column(db.Integer, default=0)
    lot_size = db.Column(db.Integer, default=0)
    pace_per_hour = db.Column(db.Integer, default=0)
    hours_per_run = db.Column(db.Float, default=8.0)
    is_active = db.Column(db.Boolean, default=True)
    remarks = db.Column(db.Text)

class ProcessCapacity(db.Model, TimestampMixin):
    __tablename__ = "process_capacities"
    __table_args__ = (
        db.UniqueConstraint("process_name", "work_date", name="uq_capacity_proc_date"),
    )
    capacity_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    process_name = db.Column(db.String(100), nullable=False)
    work_date = db.Column(db.Date, nullable=False)
    available_hours = db.Column(db.Float, default=8.0)
    workers = db.Column(db.Integer, default=1)
    overtime_hours = db.Column(db.Float, default=0.0)
    capacity_quantity = db.Column(db.Integer, default=0)
    remarks = db.Column(db.Text)

class ProcessProgress(db.Model, TimestampMixin):
    __tablename__ = "process_progresses"
    progress_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.order_id"), nullable=False)
    product_name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    process_name = db.Column(db.String(100), nullable=False)
    process_order = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    actual_end_date = db.Column(db.Date)
    ship_date = db.Column(db.Date)
    status = db.Column(db.String(20), default="未着手")
    completed_qty = db.Column(db.Integer, default=0)
    department = db.Column(db.String(100))
    remarks = db.Column(db.Text)

class Schedule(db.Model, TimestampMixin):
    __tablename__ = "schedules"
    schedule_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.order_id"), nullable=False)
    process_name = db.Column(db.String(100), nullable=False)
    process_order = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    required_days = db.Column(db.Integer)
    status = db.Column(db.String(20), default="未着手")
    has_quality_issue = db.Column(db.Boolean, default=False)
    quality_issue_detail = db.Column(db.Text)
    locked = db.Column(db.Boolean, default=False)

class Anomaly(db.Model, TimestampMixin):
    __tablename__ = "anomalies"
    anomaly_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.order_id"), nullable=False)
    status = db.Column(db.String(20), default="調査中")
    detail = db.Column(db.Text)


# ─── ミニERP 拡張モデル ──────────────────────────────────

class WorkOrder(db.Model, TimestampMixin):
    __tablename__ = "work_orders"
    work_order_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    work_order_no = db.Column(db.String(50), unique=True, nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.order_id"), nullable=True)
    product_name = db.Column(db.String(255), nullable=False)
    process_product_name = db.Column(db.String(255))
    customer = db.Column(db.String(255))
    lot_no = db.Column(db.String(100))
    quantity = db.Column(db.Integer, nullable=False, default=0)
    ship_date = db.Column(db.Date)
    status = db.Column(db.String(20), default="未着手")
    priority = db.Column(db.String(20), default="通常")
    remarks = db.Column(db.Text)
    processes = db.relationship("WorkOrderProcess", backref="work_order",
                                cascade="all, delete-orphan", lazy=True,
                                order_by="WorkOrderProcess.process_order")
    quality_issues = db.relationship("QualityIssue", backref="work_order", lazy=True)
    measurements = db.relationship("MeasurementRecord", backref="work_order", lazy=True)


class WorkOrderProcess(db.Model, TimestampMixin):
    __tablename__ = "work_order_processes"
    process_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey("work_orders.work_order_id"), nullable=False)
    process_name = db.Column(db.String(100), nullable=False)
    process_order = db.Column(db.Integer, nullable=False)
    planned_start_date = db.Column(db.Date)
    planned_end_date = db.Column(db.Date)
    actual_start_date = db.Column(db.Date)
    actual_end_date = db.Column(db.Date)
    planned_quantity = db.Column(db.Integer, default=0)
    input_quantity = db.Column(db.Integer, default=0)
    good_quantity = db.Column(db.Integer, default=0)
    defect_quantity = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="未着手")
    operator = db.Column(db.String(100))
    equipment = db.Column(db.String(100))
    remarks = db.Column(db.Text)
    quality_issues = db.relationship("QualityIssue", backref="work_order_process", lazy=True)
    measurements = db.relationship("MeasurementRecord", backref="work_order_process", lazy=True)


class QualityIssue(db.Model, TimestampMixin):
    __tablename__ = "quality_issues"
    issue_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey("work_orders.work_order_id"), nullable=True)
    process_id = db.Column(db.Integer, db.ForeignKey("work_order_processes.process_id"), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.order_id"), nullable=True)
    issue_no = db.Column(db.String(50), unique=True)
    occurred_date = db.Column(db.Date)
    process_name = db.Column(db.String(100))
    product_name = db.Column(db.String(255))
    lot_no = db.Column(db.String(100))
    issue_type = db.Column(db.String(100))
    detail = db.Column(db.Text)
    temporary_action = db.Column(db.Text)
    root_cause = db.Column(db.Text)
    corrective_action = db.Column(db.Text)
    owner = db.Column(db.String(100))
    due_date = db.Column(db.Date)
    close_date = db.Column(db.Date)
    status = db.Column(db.String(20), default="調査中")


class MeasurementRecord(db.Model, TimestampMixin):
    __tablename__ = "measurement_records"
    measurement_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey("work_orders.work_order_id"), nullable=True)
    process_id = db.Column(db.Integer, db.ForeignKey("work_order_processes.process_id"), nullable=True)
    product_name = db.Column(db.String(255), nullable=False)
    lot_no = db.Column(db.String(100))
    measured_date = db.Column(db.Date)
    measurement_item = db.Column(db.String(255))
    result = db.Column(db.String(50))
    file_path = db.Column(db.String(1000))
    storage_note = db.Column(db.Text)
    inspector = db.Column(db.String(100))
    remarks = db.Column(db.Text)
