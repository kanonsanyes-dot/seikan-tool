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
        seed_defaults()

def commit_or_rollback():
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logging.error("database commit failed: %s", e)
        raise

def seed_defaults():
    try:
        from models import ProductProcessStandard, ProcessCapacity
        from datetime import date, timedelta
        defaults = ["プレス", "バレル", "めっき", "外観検査", "出荷"]
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
