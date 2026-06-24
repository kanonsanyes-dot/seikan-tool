from __future__ import annotations
import logging
import os
from pathlib import Path
from flask import Flask, render_template, request
from database import init_db, db
from services.cleanup_service import cleanup_startup
from config.edition import EDITION

BASE_DIR = Path(__file__).resolve().parent

def create_app():
    cleanup_startup()
    app = Flask(__name__)
    app.secret_key = os.environ.get("SEIKAN_SECRET_KEY", "seikan-tool-dev-secret")
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
    init_logging()
    init_db(app)

    from routes.orders import orders_bp
    from routes.reports import reports_bp
    from routes.masters import masters_bp
    from routes.scheduler import scheduler_bp
    from routes.progress import progress_bp, progress_api_bp
    from routes.capacity import capacity_bp
    from routes.delay import delay_bp
    from routes.admin import admin_bp
    from routes.work_orders import wo_bp
    from routes.quality_issues import qi_bp
    from routes.measurements import meas_bp
    app.register_blueprint(orders_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(masters_bp)
    app.register_blueprint(scheduler_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(progress_api_bp)
    app.register_blueprint(capacity_bp)
    app.register_blueprint(delay_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(wo_bp)
    app.register_blueprint(qi_bp)
    app.register_blueprint(meas_bp)

    from models import Order
    from sqlalchemy import func
    from datetime import date, timedelta
    from services.capacity_service import get_capacity_summary
    from services.delay_service import get_delay_summary

    @app.route("/")
    def dashboard():
        today = date.today()
        month_start = today.replace(day=1)
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        total = Order.query.count()
        ok = Order.query.filter_by(data_quality="照合OK").count()
        ng = Order.query.filter(Order.data_quality != "照合OK").count()
        this_month_qty = db.session.query(func.coalesce(func.sum(Order.quantity), 0)).filter(Order.ship_date >= month_start, Order.ship_date < next_month).scalar()
        upcoming = Order.query.filter(Order.ship_date >= today, Order.ship_date <= today + timedelta(days=30)).order_by(Order.ship_date).limit(20).all()
        cap = get_capacity_summary(today.year, today.month)
        delay = get_delay_summary()
        return render_template(
            "dashboard.html",
            total=total, ok=ok, ng=ng,
            this_month_qty=this_month_qty,
            upcoming=upcoming,
            edition=EDITION,
            delay_overdue=delay["overdue"],
            delay_critical=delay["critical"],
            delay_total=delay["total"],
            bottleneck=cap.bottleneck,
            critical_count=len(cap.critical_processes),
        )

    @app.route("/progress/gantt")
    def progress_gantt():
        return render_template("progress_gantt.html")

    @app.context_processor
    def inject_current_path():
        return {"current_path": request.path}

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        logging.exception("500 error: %s", e)
        return render_template("errors/500.html"), 500

    return app

def init_logging():
    log_dir = BASE_DIR / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_dir / "seikan.log",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        encoding="utf-8"
    )
    logging.info("SeikanTool startup")

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("SEIKAN_HOST", "127.0.0.1")
    port = int(os.environ.get("SEIKAN_PORT", "5000"))
    app.run(host=host, port=port, debug=(EDITION == "dev"), use_reloader=False)
