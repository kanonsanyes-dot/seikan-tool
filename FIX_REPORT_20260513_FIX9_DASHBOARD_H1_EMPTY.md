# Fix9 Dashboard h1 空白除去対応

## 対応内容

Claudeレビュー指摘に対応し、`templates/dashboard.html` の空見出しブロックを Jinja2 の空白制御付きに変更しました。

```jinja2
{%- block h1 -%}{%- endblock -%}
```

これにより、`base.html` 側の `<h1>{% block h1 %}...{% endblock %}</h1>` がダッシュボード表示時に `<h1></h1>` としてレンダリングされやすくなり、CSS の `.topbar h1:empty { display: none; }` が安定して効くようにします。

## 変更ファイル

- `templates/dashboard.html`

## 確認ポイント

1. `http://127.0.0.1:5000/` を開く。
2. ダッシュボード上部に見出しが二重表示されないこと。
3. F12 → Elements で `.topbar h1` の中身が空であること。
4. 他画面の topbar 見出し（受注一覧、集計レポート等）は従来どおり表示されること。

## 備考

CSS の `:empty` は空白テキストノードがあると適用されないため、テンプレート側で空白を出さない対策を入れました。
