from __future__ import annotations
import logging
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "seikan.db"

db = SQLAlchemy()

def init_db(app):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
        import models  # noqa
        db.create_all()
        _migrate_columns()
        seed_defaults()

def _migrate_columns():
    """既存DBに不足カラムを追加するライトマイグレーション"""
    import sqlite3
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()

        def add_col(table, col, col_type):
            cur.execute(f"PRAGMA table_info({table})")
            cols = {row[1] for row in cur.fetchall()}
            if col not in cols:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")

        add_col("process_progresses", "completed_qty", "INTEGER DEFAULT 0")
        # orders 拡張カラム
        add_col("orders", "order_no", "VARCHAR(100)")
        add_col("orders", "order_date", "DATE")
        add_col("orders", "remaining_qty", "INTEGER")
        add_col("orders", "product_category", "VARCHAR(100)")
        add_col("orders", "sales_category", "VARCHAR(100)")
        add_col("orders", "sales_person", "VARCHAR(100)")
        add_col("orders", "unit_price", "FLOAT")
        add_col("orders", "amount", "FLOAT")
        add_col("orders", "remarks", "TEXT")
        # schedules 拡張カラム
        add_col("schedules", "has_quality_issue", "BOOLEAN DEFAULT 0")
        add_col("schedules", "quality_issue_detail", "TEXT")
        add_col("schedules", "locked", "BOOLEAN DEFAULT 0")
        # product_process_standards 拡張
        add_col("product_process_standards", "pace_per_hour", "INTEGER DEFAULT 0")
        add_col("product_process_standards", "hours_per_run", "FLOAT DEFAULT 8.0")

        conn.commit()
        conn.close()
    except Exception as e:
        logging.warning("_migrate_columns: %s", e)


def commit_or_rollback():
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logging.error("database commit failed: %s", e)
        raise

def seed_defaults():
    try:
        from models import ProductProcessStandard, ProcessCapacity, ProcessMaster, DEFAULT_PROCESSES
        from datetime import date, timedelta
        defaults = ["プレス", "バレル", "めっき", "外観検査", "出荷"]
        if ProcessMaster.query.count() == 0:
            for i, name in enumerate(DEFAULT_PROCESSES, start=1):
                db.session.add(ProcessMaster(
                    process_name=name, display_order=i,
                    hours_per_day=8.0, overtime_hours=0.0, pace_per_hour=0, is_active=True,
                ))
        # 空DBでもスケジュール生成を試せるよう、標準工程の雛形を入れる
        if ProductProcessStandard.query.count() == 0:
            for i, proc in enumerate(defaults, start=1):
                db.session.add(ProductProcessStandard(
                    product_name="サンプル品A", process_product_name="サンプル工程品A",
                    process_name=proc, process_order=i, standard_time_min=0.5,
                    daily_capacity=800, lot_size=1000, is_active=True,
                    remarks="初期サンプル。必要に応じて削除・編集してください。"
                ))
        if ProcessCapacity.query.count() == 0:
            start = date.today().replace(day=1)
            for d in range(0, 120):
                work_date = start + timedelta(days=d)
                if work_date.weekday() >= 5:
                    continue
                for proc in defaults:
                    db.session.add(ProcessCapacity(
                        process_name=proc, work_date=work_date, available_hours=8.0,
                        workers=1, overtime_hours=0.0, capacity_quantity=800,
                        remarks="初期サンプル"
                    ))
        commit_or_rollback()
    except Exception as e:
        db.session.rollback()
        logging.error("seed_defaults failed: %s", e)
