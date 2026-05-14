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
    app.secret_key = "seikan-tool-dev-secret"
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
    init_logging()
    init_db(app)

    from routes.orders import orders_bp
    from routes.reports import reports_bp
    from routes.masters import masters_bp
    from routes.scheduler import scheduler_bp
    from routes.progress import progress_bp
    app.register_blueprint(orders_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(masters_bp)
    app.register_blueprint(scheduler_bp)
    app.register_blueprint(progress_bp)

    from models import Order
    from sqlalchemy import func
    from datetime import date, timedelta

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
        return render_template("dashboard.html", total=total, ok=ok, ng=ng, this_month_qty=this_month_qty, upcoming=upcoming, edition=EDITION)

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
