# Fix8 Dashboard Redesign Minor Review対応

## 目的
Claudeレビューで指摘された以下2点を修正した。

1. `.badge-quality` の追記CSSが受注一覧など他画面へ波及する可能性
2. `:has()` セレクタ依存により古いブラウザで topbar が非表示にならない可能性

## 修正内容

### 1. badge-quality をダッシュボード内にスコープ限定

Fix7では追記CSSの `.badge-quality` がグローバル指定だったため、既存の受注一覧などのバッジ色も後書きCSSで上書きされる可能性があった。

Fix8では以下のように、ダッシュボード内だけに限定した。

```css
.dashboard-redesign .badge-quality { ... }
.dashboard-redesign .badge-quality.ok { ... }
.dashboard-redesign .badge-quality.ng { ... }
.dashboard-redesign .badge-quality.warn { ... }
.dashboard-redesign .badge-quality.muted { ... }
```

これにより、受注一覧など既存画面の `.badge-quality` は既存CSSのまま維持される。

### 2. :has() 依存のtopbar非表示を廃止

Fix7では以下を使用していた。

```css
.topbar:has(+ .dashboard-redesign) {
  display: none;
}
```

古いブラウザでは `:has()` 非対応の可能性があるため、Fix8では以下に変更した。

```css
.topbar h1:empty {
  display: none;
  margin: 0;
}
```

`dashboard.html` は `{% block h1 %}{% endblock %}` により空の h1 を出すため、ダッシュボードでは topbar の見出し領域が実質消える。
他画面の h1 は空ではないため、影響しない想定。

## 確認ポイント

- `/` ダッシュボードで見出しが二重表示されないこと
- ダッシュボードのKPI、アラート、グラフ表示が崩れないこと
- 受注一覧の品質バッジがFix7の追記CSSで意図せず薄色化されていないこと
- 古いChrome/Edge相当でも `:has()` に依存しないこと
- 他画面の topbar h1 が通常どおり表示されること

## 変更ファイル

- `static/css/style.css`

コード変更はCSSのみ。
