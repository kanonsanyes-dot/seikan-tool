# SeikanTool サイドバーリデザイン Claudeレビュー指示書

## 目的

SeikanTool のサイドバーUIリデザインについて、実装内容・副作用・動作確認をレビューしてください。

対象ファイル：

- `templates/base.html`
- `app.py`
- `static/css/style.css`
- `templates/dashboard.html`

---

## 今回の変更概要

### 1. base.html

- Bootstrap Icons CDNをbase.html側に追加
- サイドバーHTMLを新デザインへ変更
- ブランドエリアを追加
- MAIN / MASTER セクションへ分割
- 各リンクにBootstrap Iconsを追加
- `current_path` によるアクティブ表示を追加

### 2. app.py

- `request` をimport
- `create_app()` 内に `context_processor` を追加
- 全テンプレートで `current_path` を参照可能にした

追加コード：

```python
@app.context_processor
def inject_current_path():
    return {"current_path": request.path}
```

### 3. style.css

- 既存CSSは削除・変更せず、末尾追記のみ
- `.sidebar` の背景とpaddingを上書き
- `.sb-brand`
- `.sb-link`
- `.sb-active`
- `.sb-nav-master`
- `.sb-section-label`
- `.sb-divider`
- などを追加

### 4. dashboard.html

- Bootstrap Icons CDNをdashboard.html側から削除
- base.html側のCDN読み込みに一本化

---

## レビューしてほしいポイント

### 1. 起動確認

以下で起動できるか確認してください。

```bat
python app.py
```

ブラウザで以下を開く。

```text
http://127.0.0.1:5000
```

確認項目：

- 500エラーが出ない
- base.htmlの構文エラーがない
- `current_path` 未定義エラーが出ない
- Bootstrap Icons が表示される

---

### 2. アクティブ表示確認

以下のページで、対応するサイドバーリンクがアクティブ表示になるか確認してください。

| URL | 期待するアクティブ |
|---|---|
| `/` | ダッシュボード |
| `/orders/import` | 受注取込 |
| `/orders` または `/orders/` | 受注一覧 |
| `/reports/summary` | 集計レポート |
| `/scheduler` | スケジューラー |
| `/scheduler/...` | スケジューラー |
| `/progress` または `/progress/` | 進捗表 |
| `/masters/customers` | 出荷先マスタ |
| `/masters/products` | 品名マスタ |
| `/masters/standards` または `/masters/process-standards` | 工程標準 |
| `/masters/capacity` または `/masters/process-capacity` | 工程キャパ |

---

### 3. CSS副作用確認

確認してほしい点：

- 既存の `.sidebar` 固定配置が崩れていない
- `main` 側の余白が変わっていない
- 他画面のカード・テーブル・ボタンに影響が出ていない
- `.nav-link` 既存CSSと `.sb-link` が競合していない
- MASTERセクションの文字がMAINより一回り小さく・暗い
- ホバー時に薄い背景が出る
- アクティブ時に左ボーダーと背景が出る

---

### 4. Bootstrap Icons確認

base.htmlに以下を追加しています。

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
```

確認してほしいこと：

- サイドバーのアイコンが表示される
- ダッシュボードなど既存画面のアイコンも表示される
- dashboard.html側にBootstrap Icons CDNが残っていない
- 重複ロードが起きていない

---

### 5. パス判定の妥当性

`current_path` 判定について、以下を確認してください。

- `/orders` と `/orders/` の両方を受注一覧として扱えているか
- `/scheduler` 配下は `startswith('/scheduler')` で問題ないか
- 工程標準・工程キャパの実際のURLが `/masters/process-standards` / `/masters/process-capacity` でアクティブになるか
- URLが実装と違う場合は `current_path` 判定だけ修正する

---

## 注意点

今回の修正はUIリデザインが目的です。  
以下は変更しないでください。

- DBモデル
- 受注取込処理
- スケジューラー処理
- 集計レポート処理
- Excel出力処理
- 既存のルート処理

---

## 期待するレビュー結果

以下の形式でレビューしてください。

```md
# SeikanTool サイドバーリデザイン レビュー結果

## 結論
- OK / 要修正

## 確認結果
- 起動：
- アイコン表示：
- アクティブ表示：
- MAIN / MASTER表示：
- 他画面への副作用：

## 修正が必要な点
1.
2.
3.

## 軽微な改善案
1.
2.

## 本番投入可否
- 可 / 条件付き可 / 不可
```
