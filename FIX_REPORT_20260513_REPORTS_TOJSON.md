# Fix Report: 集計レポート TypeError 修正

## 問題
集計レポート `/reports/summary` 表示時に以下のエラーが発生。

```text
TypeError: Object of type Row is not JSON serializable
```

## 原因
SQLAlchemy の集計結果 `Row` オブジェクトを、そのまま Jinja の `tojson` フィルタへ渡していたため。

対象箇所：

```python
return render_template("reports/summary.html", monthly=monthly, customer=customer, product=product, month=month)
```

テンプレート側：

```javascript
monthly: {{ monthly|tojson }}
```

## 修正内容
`routes/reports.py` に `_to_json_rows()` を追加し、SQLAlchemy Row を通常の list に変換してからテンプレートへ渡すように変更。

```python
def _to_json_rows(rows):
    return [[label or "未設定", int(total or 0)] for label, total in rows]
```

## 確認してほしい内容
- `/reports/summary` が表示できる
- 月別・客先別・品名別タブが表示できる
- Chart.js の棒グラフが表示できる
- Excel出力が動く
- 対象月フィルタが動く
