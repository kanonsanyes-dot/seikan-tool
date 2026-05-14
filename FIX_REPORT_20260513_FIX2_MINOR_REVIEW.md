# SeikanTool Fix2 Minor Review対応

## 対応日
2026-05-13

## 対応内容

### 1. cleanupGestureClasses に save-error を追加

`pointercancel` や後始末処理後に、保存失敗表示の赤枠が残る可能性をなくすため、`cleanupGestureClasses()` の削除対象に `save-error` を追加。

対象ファイル:

- `static/js/scheduler.js`

変更内容:

```javascript
cardEl.classList.remove('dragging', 'drag-active', 'settling', 'saving', 'snapped', 'save-error');
```

### 2. trySnap のHTTPエラーをスナップなし扱いに変更

スナップAPIが一時的に500等を返した場合でも、スケジュール保存全体が止まらないように修正。

対象ファイル:

- `static/js/scheduler.js`

変更内容:

```javascript
if (!res.ok) {
  console.warn(`snap failed: ${res.status}`);
  return null;
}
```

## 未対応・次フェーズ検討

### スナップ時の吸着アニメーション

現状は、スナップ後にDOM位置を即時確定し、`snapped` クラスによる軽いpop表現でフィードバックしている。

「スナップ前位置から吸着先へヌルっと移動する」アニメーションは、次フェーズで操作感を見ながら検討する。

## Claude確認依頼ポイント

- `pointercancel` 後に `save-error` 表示が残らないか
- スナップAPIエラー時に保存処理全体が止まらないか
- 通常ドラッグ保存が壊れていないか
- 左右リサイズ保存が壊れていないか
- スナップON/OFFの挙動が変わっていないか
