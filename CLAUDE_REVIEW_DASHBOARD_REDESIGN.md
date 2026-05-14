# SeikanTool ダッシュボードリデザイン Claudeレビュー依頼

## 目的

SeikanTool の `templates/dashboard.html` と `static/css/style.css` 追記部分を、キャパダッシュボードのUI改善として実装しました。
今回のレビューでは、Python側ロジックではなく、主に Flask/Jinja2 テンプレート、CSS、Chart.js、既存画面への副作用を確認してください。

## 変更対象

- `templates/dashboard.html`
- `static/css/style.css` 末尾追記

## 変更しなかったもの

- `app.py`
- `base.html`
- 受注一覧、集計レポート、スケジューラー、マスタ管理など他画面テンプレート

## 実装内容

### 1. 未照合アラートバナー

`ng > 0` のときだけ、ダッシュボード上部に赤系バナーを表示します。

確認ポイント：

- `ng > 0` で表示されるか
- `ng == 0` で非表示になるか
- `→ 受注一覧` リンクが `/orders` に遷移するか
- `url_for('orders.list_orders')` が正しいか

### 2. KPIカード4枚

以下の4カードを実装しました。

- 受注件数
- 照合OK
- 未照合
- 今月出荷数量

確認ポイント：

- `total / ok / ng / this_month_qty` が正しく表示されるか
- 未照合カードだけ `ng > 0` で赤系背景になるか
- `this_month_qty` が `None` の場合でも落ちないか
- Bootstrap Icons CDN読み込みが `block head` で問題ないか

### 3. 照合ステータス プログレスバー

`ok / total` を幅にして表示します。

確認ポイント：

- `total == 0` のとき ZeroDivisionError が出ないか
- `ok / total` の比率がバー幅に反映されるか
- `ng` 件数表示が正しいか

### 4. 直近30日の出荷予定テーブル

`upcoming` を表示します。

確認ポイント：

- `upcoming` が空のとき「出荷予定はありません」と出るか
- `ship_date` がある場合 `MM/DD` 表示になるか
- `ship_date` が `None` の場合に落ちないか
- `quantity` が `None` の場合に落ちないか
- `product_name` が長い場合に崩れないか
- `data_quality` のバッジ表示が現行DB値に合っているか

現在のバッジ仕様：

- `照合OK` → 緑
- `要確認` → 黄
- `除外対象` → グレー
- それ以外の文字列（品名未登録、客先未登録、工程標準未登録、未チェックなど）→ 赤で実値表示

### 5. 工程別負荷率 Chart.js

現時点ではモックデータです。

```javascript
const capacityData = {
  labels: ['プレス', 'バレル', 'めっき', '外観検査', '出荷'],
  values: [65, 42, 82, 38, 15]
};
```

確認ポイント：

- Chart.js が既に base.html で読み込まれている前提で動くか
- `window._seikanCapacityChart` を destroy してから再生成しているか
- Y軸が0〜100%になっているか
- 80%以上は赤、60〜79は黄、59以下は緑になっているか
- legend非表示、下部凡例表示になっているか
- `beforeunload` で Chart インスタンスを destroy しているか

### 6. CSS追記

`static/css/style.css` の末尾に追記しています。既存CSSは削除・変更していません。

確認ポイント：

- 既存 `.card`, `.kpi`, `.badge-quality` への副作用が大きすぎないか
- `.badge-quality` の拡張が受注一覧など他画面のバッジ表示を壊していないか
- `.topbar:has(+ .dashboard-redesign)` でダッシュボードのみ既存topbarを隠す意図が機能するか
- `:has()` はChrome系では動くが、古いブラウザでは非対応の可能性があるため、問題があれば別案を提案してほしい
- スマホ幅、タブレット幅でKPIカードとグラフが崩れないか

## 特に見てほしいリスク

### リスク1：`block h1` を空にしている点

`base.html` の topbar に重複タイトルが出るのを避けるため、`dashboard.html` 側で `{% block h1 %}{% endblock %}` を空にしています。
CSSで `.topbar:has(+ .dashboard-redesign)` を非表示にしています。

確認してほしいこと：

- ダッシュボードだけtopbarが消えるか
- 他ページのtopbarに影響しないか
- `:has()` を避けた方がよい場合、代替案をください

### リスク2：`url_for('orders.list_orders')`

受注一覧リンクは既存Blueprintに合わせて `orders.list_orders` を使っています。

確認してほしいこと：

- 現行コードのエンドポイント名と一致しているか

### リスク3：`upcoming|length`

`upcoming` は list[Order] 想定です。

確認してほしいこと：

- Queryオブジェクトではなくlistなので `length` が問題なく使えるか

### リスク4：Chart.js多重生成

ページ遷移やリロード時にChartインスタンスが積まれないよう destroy しています。

確認してほしいこと：

- `window._seikanCapacityChart` の破棄タイミングが妥当か
- 既存 `main.js` と競合しないか

## 受け入れ条件

以下がOKなら、このダッシュボードUI版は採用可能と判断します。

- `/` が500エラーにならない
- `ng > 0` でアラート表示
- `ng == 0` でアラート非表示
- `total == 0` でプログレスバーが落ちない
- `upcoming` 空で空表示になる
- `upcoming` ありで一覧表示される
- Chart.js棒グラフが表示される
- 受注一覧、集計レポート、スケジューラーにCSS副作用が出ない
- Chromeで表示が大きく崩れない
- スマホ幅で縦積み表示になる

## Claudeへの依頼

問題があれば、以下の形式で返してください。

```text
🔴 致命的：すぐ直すべき問題
🟡 中程度：次Fixで直したい問題
🟢 軽微：任意改善
✅ 良い点
```

可能なら修正コードも、`dashboard.html` と `style.css追記部分` のどちらを直すべきか明記してください。

---

# Fix8 追加レビュー依頼

Fix7レビューで出た軽微な2点をFix8で修正しました。

## 追加確認してほしいこと

1. `.badge-quality` の追記CSSを `.dashboard-redesign .badge-quality` に限定したため、受注一覧など他画面の品質バッジ表示へ副作用が出ていないか。
2. `:has()` セレクタを廃止し、`.topbar h1:empty` に変更したため、ダッシュボードで見出しが二重表示されず、他画面では従来通りh1が表示されるか。
3. ダッシュボードの品質バッジは従来通り薄色デザインで表示されるか。
4. 古いブラウザでもCSSパースエラーになりにくい構成になっているか。

## 重点確認URL

- `/` ダッシュボード
- `/orders` 受注一覧
- `/reports/summary` 集計レポート

今回の変更は `static/css/style.css` のみです。


---

## Fix9 追加確認：dashboard h1 空白制御

### 背景

Fix8では `.topbar h1:empty` により、ダッシュボード画面だけ base.html 側の空見出しを非表示にしていました。
ただし `:empty` は空白・改行テキストノードが入ると効かないため、Fix9で `dashboard.html` の h1 block を空白制御付きに変更しました。

```jinja2
{%- block h1 -%}{%- endblock -%}
```

### 見てほしいこと

1. ダッシュボードで topbar の空 h1 が非表示になるか。
2. 画面上の「キャパダッシュボード」が二重表示されないか。
3. F12 Elements で `<div class="topbar"><h1></h1></div>` 相当になっているか。
4. 他画面では `h1` が従来どおり表示されるか。
5. CSS の `.topbar h1:empty` が古めのブラウザで許容できるか。

### 代替案

もし古い工場PCブラウザで `:empty` が不安定なら、次フェーズで `base.html` に topbar 制御用 block を追加する案を検討してください。

例：

```jinja2
<div class="topbar {% block topbar_class %}{% endblock %}">
```

ただし今回は `base.html` 変更禁止の前提を守るため、dashboard.html 側の空白制御で対応しています。
