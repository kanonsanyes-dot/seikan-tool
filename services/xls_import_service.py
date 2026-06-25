"""
受注Excelインポーター
対象: 既存の HTML-in-XLS 形式（grd_Receive_1.xls など）
列順: 受注区分,客先指定納期,回答納品日,出荷予定日,注文番号,納入先,客先製品名,工程製品名,
      受注数,単位,単価(外貨),単価(円),受注金額,備考,出荷数,注残,完納日,受注日,
      営業区分,製品区分,検収予定月,担当者,データ区分
"""
from __future__ import annotations
import re
from datetime import date
from html.parser import HTMLParser


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self._cur_row: list[str] = []
        self._cur_cell = ""
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._cur_row = []
        elif tag in ("td", "th"):
            self._in_cell = True
            self._cur_cell = ""

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self._cur_row.append(self._cur_cell.strip())
            self._in_cell = False
        elif tag == "tr" and any(c for c in self._cur_row):
            self.rows.append(self._cur_row)

    def handle_data(self, data):
        if self._in_cell:
            self._cur_cell += data


def _parse_date(s: str) -> date | None:
    if not s or not s.strip():
        return None
    s = s.strip()
    m = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})", s)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None
    return None


def _parse_int(s: str) -> int:
    if not s:
        return 0
    try:
        return int(str(s).replace(",", "").replace(" ", "").split(".")[0])
    except Exception:
        return 0


def _parse_float(s: str) -> float:
    if not s:
        return 0.0
    try:
        return float(str(s).replace(",", "").replace(" ", ""))
    except Exception:
        return 0.0


COL_MAP = {
    "受注区分": 0, "客先指定納期": 1, "回答納品日": 2, "出荷予定日": 3,
    "注文番号": 4, "納入先": 5, "客先製品名": 6, "工程製品名": 7,
    "受注数": 8, "単位": 9, "単価外貨": 10, "単価円": 11, "受注金額": 12,
    "備考": 13, "出荷数": 14, "注残": 15, "完納日": 16, "受注日": 17,
    "営業区分": 18, "製品区分": 19, "検収予定月": 20, "担当者": 21, "データ区分": 22,
}


def parse_xls_file(filepath: str) -> list[dict]:
    """
    HTML-XLS ファイルをパースし、受注レコードのリストを返す。
    - ヘッダ行を自動検出
    - 注残 > 0 のものだけ返す（完納済み除外）
    - データ区分 が "その他" のものは含める（金型・サンプル含む）
    """
    for enc in ("shift_jis", "cp932", "utf-8", errors := None):
        if enc is None:
            raise ValueError("エンコーディング検出失敗")
        try:
            with open(filepath, encoding=enc, errors="replace") as f:
                html = f.read()
            break
        except Exception:
            continue

    parser = _TableParser()
    parser.feed(html)
    rows = parser.rows
    if not rows:
        return []

    # ヘッダ行を検出（"受注区分" が含まれる行）
    header_idx = None
    for i, row in enumerate(rows):
        if any("受注区分" in cell for cell in row):
            header_idx = i
            break
    if header_idx is None:
        header_idx = 0

    data_rows = rows[header_idx + 1:]
    records = []
    for row in data_rows:
        def g(idx, default=""):
            try:
                return row[idx].strip() if idx < len(row) else default
            except Exception:
                return default

        order_type = g(0)
        if order_type not in ("受注", "内示"):
            continue

        ship_date = _parse_date(g(3)) or _parse_date(g(2)) or _parse_date(g(1))
        if not ship_date:
            continue

        product_name = g(7) or g(6)
        if not product_name:
            continue

        remaining = _parse_int(g(15))

        records.append({
            "order_type": order_type,
            "customer_due_date": _parse_date(g(1)),
            "confirmed_due_date": _parse_date(g(2)),
            "ship_date": ship_date,
            "order_no": g(4),
            "customer": g(5),
            "customer_product_name": g(6),
            "product_name": product_name,
            "quantity": _parse_int(g(8)),
            "unit": g(9),
            "unit_price": _parse_float(g(11)),
            "amount": _parse_float(g(12)),
            "remarks": g(13),
            "shipped_qty": _parse_int(g(14)),
            "remaining_qty": remaining,
            "order_date": _parse_date(g(17)),
            "sales_category": g(18),
            "product_category": g(19),
            "sales_person": g(21),
            "data_category": g(22),
        })
    return records


def import_to_db(records: list[dict], skip_zero_remaining: bool = True) -> dict:
    """
    パース済みレコードをOrderテーブルにインポート。
    order_no が重複するものはスキップ（冪等）。
    Returns: {"imported": n, "skipped": n, "errors": [...]}
    """
    from models import Order
    from database import db

    imported = skipped = 0
    errors = []

    for rec in records:
        if skip_zero_remaining and rec["remaining_qty"] == 0:
            skipped += 1
            continue
        try:
            existing = Order.query.filter_by(order_no=rec["order_no"]).first() if rec["order_no"] else None
            if existing:
                skipped += 1
                continue
            order = Order(
                product_name=rec["product_name"],
                process_product_name=rec["customer_product_name"] or rec["product_name"],
                customer=rec["customer"] or "不明",
                ship_date=rec["ship_date"],
                quantity=rec["quantity"] or 0,
                remaining_qty=rec["remaining_qty"],
                order_no=rec["order_no"],
                order_date=rec["order_date"],
                product_category=rec["product_category"],
                sales_category=rec["sales_category"],
                sales_person=rec["sales_person"],
                unit_price=rec["unit_price"],
                amount=rec["amount"],
                remarks=rec["remarks"],
                status="受注中",
                data_quality="未チェック",
            )
            db.session.add(order)
            imported += 1
        except Exception as e:
            errors.append(f"{rec.get('order_no','?')}: {e}")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        errors.append(f"コミットエラー: {e}")

    return {"imported": imported, "skipped": skipped, "errors": errors}
