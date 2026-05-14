from __future__ import annotations
import re
import csv
from pathlib import Path
import chardet
from dateutil import parser
from datetime import date
from werkzeug.utils import secure_filename
from database import db
from models import Order, Customer, Product
from services.quality_check_service import check_data_quality
from services import cache_service
from config.edition import current_limits

REQUIRED_COLUMNS = ["品名", "出荷先", "出荷日", "数量"]
ALLOWED_EXT = {".csv"}

class ImportErrorDetail(Exception):
    pass

def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXT

def read_csv_auto(path: Path) -> list[dict]:
    """Read CSV without pandas to avoid numpy/pandas install trouble on locked-down PCs."""
    raw = path.read_bytes()
    detected = chardet.detect(raw)
    candidates = []
    enc = detected.get("encoding")
    if enc:
        candidates.append(enc)
    candidates += ["utf-8-sig", "utf-8", "cp932", "shift_jis"]
    last = None
    for enc in dict.fromkeys(candidates):
        try:
            text = raw.decode(enc)
            # Remove NUL characters and normalize BOM if present
            text = text.replace("\x00", "")
            rows = list(csv.DictReader(text.splitlines()))
            if rows is not None:
                return rows
        except Exception as e:
            last = e
    raise ImportErrorDetail(f"CSV読込に失敗しました: {last}")

def is_blank(value) -> bool:
    return value is None or str(value).strip() == ""

def parse_jp_date(value):
    if is_blank(value):
        return None
    text = str(value).strip()
    m = re.match(r"R(\d+)\.(\d+)\.(\d+)", text, re.IGNORECASE)
    if m:
        y, mo, d = map(int, m.groups())
        return date(2018 + y, mo, d)
    try:
        dt = parser.parse(text, yearfirst=True)
        return dt.date()
    except Exception:
        return None

def to_int(value):
    if is_blank(value):
        return None
    try:
        return int(float(str(value).replace(",", "").strip()))
    except Exception:
        return None

def import_orders(file_storage, upload_dir: Path):
    if not file_storage or not file_storage.filename:
        raise ImportErrorDetail("ファイルが選択されていません。")
    if not allowed_file(file_storage.filename):
        raise ImportErrorDetail("CSVファイルのみアップロードできます。")
    filename = secure_filename(file_storage.filename)
    path = upload_dir / filename
    file_storage.save(path)
    if path.stat().st_size > 10 * 1024 * 1024:
        path.unlink(missing_ok=True)
        raise ImportErrorDetail("ファイルサイズは10MB以下にしてください。")

    rows = read_csv_auto(path)
    if not rows:
        raise ImportErrorDetail("CSVにデータ行がありません。")
    fieldnames = rows[0].keys()
    missing = [c for c in REQUIRED_COLUMNS if c not in fieldnames]
    if missing:
        raise ImportErrorDetail("必須列が不足しています: " + ", ".join(missing))

    max_rows = current_limits().get("max_csv_rows")
    if max_rows and len(rows) > max_rows:
        rows = rows[:max_rows]

    success = 0
    errors = []
    ng = 0
    new_customers = set()
    new_products = set()

    for idx, row in enumerate(rows):
        rownum = idx + 2
        try:
            product_name = str(row.get("品名", "")).strip()
            customer = str(row.get("出荷先", "")).strip()
            ship_date = parse_jp_date(row.get("出荷日"))
            quantity = to_int(row.get("数量"))
            if not product_name:
                raise ValueError("品名が空です")
            if not customer:
                raise ValueError("出荷先が空です")
            if not ship_date:
                raise ValueError("出荷日が日付として読めません")
            if quantity is None:
                raise ValueError("数量が数値として読めません")
            status = str(row.get("ステータス", "受注中")).strip() or "受注中"
            if status not in ["受注中", "完了", "調整中"]:
                status = "受注中"
            order = Order(
                product_name=product_name,
                process_product_name=str(row.get("工程品名", "")).strip() or None,
                customer=customer,
                ship_date=ship_date,
                quantity=quantity,
                status=status,
            )
            order.data_quality = check_data_quality(order)
            if order.data_quality != "照合OK":
                ng += 1
            if order.data_quality == "客先未登録":
                new_customers.add(customer)
            if order.data_quality in ["品名未登録", "工程標準未登録"]:
                new_products.add(product_name)
            db.session.add(order)
            success += 1
        except Exception as e:
            errors.append({"row": rownum, "message": str(e)})
    db.session.commit()
    cache_service.clear()
    return {
        "success": success,
        "error_count": len(errors),
        "ng_count": ng,
        "errors": errors,
        "new_customers": sorted(new_customers),
        "new_products": sorted(new_products),
    }

def add_missing_masters(customers, products):
    for name in customers:
        if name and not Customer.query.filter_by(customer_name=name).first():
            db.session.add(Customer(customer_name=name, is_active=True))
    for name in products:
        if name and not Product.query.filter_by(product_name=name).first():
            db.session.add(Product(product_name=name, is_active=True))
    db.session.commit()
    cache_service.clear()
