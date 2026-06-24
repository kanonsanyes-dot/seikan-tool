from __future__ import annotations
from datetime import date
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from services.backup_service import create_backup
from services.capacity_service import get_capacity_summary
from services.delay_service import get_delay_risks
from services.export_service import capacity_report_excel
from config.edition import EDITION, current_limits

BASE = Path(__file__).resolve().parents[1]
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("")
def index():
    limits = current_limits()
    backups_dir = BASE / "data" / "backups"
    backups = sorted(backups_dir.glob("backup_*.zip"), reverse=True) if backups_dir.exists() else []
    backup_list = [{"name": f.name, "size_kb": round(f.stat().st_size / 1024, 1)} for f in backups[:20]]
    return render_template("admin/index.html", edition=EDITION, limits=limits, backups=backup_list)


@admin_bp.route("/backup/create", methods=["POST"])
def backup_create():
    try:
        out = create_backup()
        flash(f"バックアップを作成しました: {out.name}", "success")
    except Exception as e:
        flash(f"バックアップ失敗: {e}", "danger")
    return redirect(url_for("admin.index"))


@admin_bp.route("/backup/download/<name>")
def backup_download(name):
    path = BASE / "data" / "backups" / name
    if not path.exists() or not path.suffix == ".zip":
        flash("ファイルが見つかりません。", "danger")
        return redirect(url_for("admin.index"))
    return send_file(path, as_attachment=True)


# ─── 会議用キャパ確認レポート ─────────────────────────
@admin_bp.route("/report/meeting")
def meeting_report():
    today = date.today()
    year = int(request.args.get("year", today.year))
    month = int(request.args.get("month", today.month))
    summary = get_capacity_summary(year, month)
    risks = get_delay_risks(days_ahead=60)
    prev_year, prev_month = (year, month - 1) if month > 1 else (year - 1, 12)
    next_year, next_month = (year, month + 1) if month < 12 else (year + 1, 1)
    return render_template(
        "admin/meeting_report.html",
        summary=summary,
        risks=risks[:20],
        year=year,
        month=month,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        generated_at=today,
    )


@admin_bp.route("/report/meeting/excel")
def meeting_report_excel():
    today = date.today()
    year = int(request.args.get("year", today.year))
    month = int(request.args.get("month", today.month))
    summary = get_capacity_summary(year, month)
    risks = get_delay_risks(days_ahead=60)
    return capacity_report_excel(summary, risks)
