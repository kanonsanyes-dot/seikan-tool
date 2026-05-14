from __future__ import annotations
from datetime import datetime
from database import db

class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    schedules = db.relationship("Schedule", backref="order", cascade="all, delete-orphan", lazy=True)
    progresses = db.relationship("ProcessProgress", backref="order", cascade="all, delete-orphan", lazy=True)

class Customer(db.Model):
    __tablename__ = "customers"
    customer_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_name = db.Column(db.String(255), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    __tablename__ = "products"
    product_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_name = db.Column(db.String(255), nullable=False, unique=True)
    process_product_name = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProductProcessStandard(db.Model, TimestampMixin):
    __tablename__ = "product_process_standards"
    standard_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_name = db.Column(db.String(255), nullable=False)
    process_product_name = db.Column(db.String(255))
    process_name = db.Column(db.String(100), nullable=False)
    process_order = db.Column(db.Integer, nullable=False)
    standard_time_min = db.Column(db.Float, default=0.0)
    daily_capacity = db.Column(db.Integer, default=0)
    lot_size = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    remarks = db.Column(db.Text)

class ProcessCapacity(db.Model, TimestampMixin):
    __tablename__ = "process_capacities"
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
    order_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="調査中")
    detail = db.Column(db.Text)
