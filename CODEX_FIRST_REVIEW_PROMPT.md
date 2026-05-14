# CODEX FIRST REVIEW PROMPT

このリポジトリは **SeikanTool** です。  
Python / Flask / SQLite / Bootstrap 5 / Chart.js で作成した、ローカルWebアプリ型の生産管理・工程スケジューラーです。

## 最初に読んでください

まず以下のファイルを読んで、現在の設計意図と作業履歴を把握してください。

- `DAILY_SUMMARY_20260513.md`
- `SEIKANTOOL_DESIGN_SYSTEM.md`
- `PROCESS_KILL_README.md`
- `FIX_REPORT_20260513_FIX12_CODEX_CLEANUP_READY.md` が存在する場合はそれも読む

---

## 目的

Codex投入前の初回レビューとして、以下を確認してください。

**大改造はしないでください。**  
まずは、起動不能・重大バグ・テンプレートエラー・CSSの明確な重複や副作用だけを確認し、必要な場合のみ最小変更で修正してください。

---

## 重点確認項目

### 1. 起動確認

以下で起動できるか確認してください。

```bash
python app.py
```

または、ランチャー経由で確認してください。

```bat
run.bat
```

確認URL：

```text
http://127.0.0.1:5000
```

確認対象：

- `/`
- `/orders`
- `/orders/import`
- `/reports/summary`
- `/scheduler`
- `/progress`
- `/masters/customers`
- `/masters/products`
- `/masters/standards`
- `/masters/capacity`

---

## 2. Python / Flask 側の確認

以下を確認してください。

- `app.py` が起動時に例外を出さない
- Blueprint登録が正しい
- `current_path` の context_processor が全テンプレートで使える
- `use_reloader=False` により二重プロセス化しない
- `SEIKAN_HOST` / `SEIKAN_PORT` の環境変数が有効
- `launcher.py` 経由で5000番ポートの残プロセスを整理できる
- `python app.py` 直接起動時は launcher 機能が使われないが、通常起動はできる

---

## 3. テンプレート確認

### `templates/base.html`

- サイドバーが表示される
- Bootstrap Icons が読み込まれている
- MAIN / MASTER セクションが表示される
- `current_path` に応じて active 表示が正しく付く
- 他画面のレイアウトを壊していない

### `templates/dashboard.html`

- `/` で500エラーにならない
- `ng > 0` のとき未照合アラートが表示される
- `ng == 0` のとき未照合アラートが非表示になる
- `total == 0` のときゼロ除算しない
- Chart.js のグラフが表示される
- Chart.js が多重生成されない
- Bootstrap Icons CDN が base.html 側に移され、重複していない

### `templates/reports/summary.html`

- SQLAlchemy Row を `tojson` に渡して落ちない
- 月別・客先別・品名別集計が表示できる
- 月別スコープ切替が動く
- Excel出力リンクに条件が引き継がれる

### `templates/scheduler/index.html`

- 工程カードが表示される
- 横スクロールとカードドラッグが競合しない
- PDF出力ボタンが存在する
- Excel出力ボタンが存在する

---

## 4. JavaScript確認

### `static/js/scheduler.js`

以下は特に重要です。

- `pointermove` 中に PATCH / DB保存APIを送っていない
- `pointerup` 後にだけ保存している
- `pointercancel` 時に保存しない
- クリックだけでは保存しない
- `trySnap()` で `res.ok` を確認し、スナップAPI失敗時はスナップなしとして扱う
- 未定義工程の fallback 色が以下になっている

```javascript
{ bg: '#D3D1C7', border: '#5F5E5A', text: '#444441' }
```

- イベントリスナーが重複登録されない
- `requestAnimationFrame` を使い、操作感が重くならない
- `locked=true` の工程カードがドラッグ不可になる

---

## 5. CSS確認

現在のCSSは、fixを重ねた結果、追記が多く重複があります。  
ただし、初回Codex作業では**大規模整理をしないでください**。

まずは以下を確認してください。

- 明らかな構文エラーがない
- `.sidebar` / `.sb-brand-icon` / `::-webkit-scrollbar` などの重複がある場合、影響範囲を報告する
- すぐ壊れる重複だけ最小修正する
- 大規模なCSS変数化や全面整理は、提案だけに留める
- ダッシュボード用の `.badge-quality` が他画面へ副作用を出していない
- デザインシステムのウォームアンバー方針から明らかに外れる色が残っていないか確認する

---

## 6. デザインシステム確認

`SEIKANTOOL_DESIGN_SYSTEM.md` に従い、以下を確認してください。

- ページ背景：`#FFFBF5`
- サイドバー背景：`#FDF6EC`
- カード背景：`#FFFFFF`
- 主要テキスト：`#412402`
- 本文：`#633806`
- 補助：`#854F0B`
- ボーダー：`#F0D9B8`
- アクティブ / 主操作：アンバー系
- 成功：グリーン系
- 警告：テラコッタ系
- 工程カラー：
  - プレス：`#AFA9EC` / `#534AB7` / `#3C3489`
  - バレル：`#F4C0D1` / `#993556` / `#72243E`
  - めっき：`#B5D4F4` / `#185FA5` / `#0C447C`
  - 外観検査：`#FAC775` / `#BA7517` / `#633806`
  - 出荷：`#C0DD97` / `#3B6D11` / `#27500A`
  - 未定義：`#D3D1C7` / `#5F5E5A` / `#444441`

---

## 7. Git管理確認

以下を確認してください。

- `.gitignore` が存在する
- `.venv/` が除外されている
- `__pycache__/` が除外されている
- `*.pyc` が除外されている
- `data/*.db` または `*.db` が除外されている
- `uploads/` の実データが除外されている
- `data/logs/` や `data/temp/` が除外されている

---

## 8. 修正方針

### やってよいこと

- 起動不能の修正
- 明確なテンプレートエラーの修正
- 1〜数行で済む重大バグの修正
- 明確なCSS副作用の最小修正
- `.gitignore` の不足修正
- コメント・README・レビュー文書の軽微な追記

### やらないこと

- DB設計変更
- 画面構成の大幅変更
- CSS全面リファクタリング
- 大規模なファイル分割
- routes構成の大幅変更
- スケジューラー仕様の大改造
- デザインの方向性変更
- ライブラリ追加

---

## 9. 出力してほしい内容

作業後、以下の形式で報告してください。

```md
# Codex 初回レビュー結果

## 結論
- OK / 要修正 / 条件付きOK

## 確認したファイル
- 
- 
- 

## 実行したコマンド
```bash
...
```

## 修正したファイル
| ファイル | 修正内容 | 理由 |
|---|---|---|
| | | |

## 動作確認結果
| 画面 | 結果 | 備考 |
|---|---|---|
| `/` | OK/NG | |
| `/orders` | OK/NG | |
| `/reports/summary` | OK/NG | |
| `/scheduler` | OK/NG | |

## 残課題
1.
2.
3.

## 次にやるべきこと
1.
2.
3.
```

---

## 最重要メッセージ

このリポジトリは、現時点では「実機で動くこと」を優先しています。  
最初のCodex作業では、綺麗に作り直すよりも、**壊さずに安全確認すること**を優先してください。

大改造ではなく、**レビュー＋重大バグの最小修正**でお願いします。
