# SeikanTool デザインシステム設計書

## デザイン哲学

> AIっぽくない、工場現場で使う人間的な温かみのあるUI

- 冷たいブルー・グレーを避け、アンバー・クリーム・テラコッタ系を基調とする
- 余白を十分にとり、詰め込みすぎない
- アイコン＋テキストで迷わせない
- エラーや警告は「怖い赤」ではなく「注意を促す暖色」で表現する
- フォントウェイトは 400 と 500 を基本にする

## カラーパレット

### ベースカラー

| 用途 | HEX |
|---|---|
| ページ背景 | `#FFFBF5` |
| サイドバー背景 | `#FDF6EC` |
| カード背景 | `#FFFFFF` |
| KPI背景 | `#FDF6EC` |
| インプット背景 | `#FDF8F2` |

### ボーダー

| 用途 | HEX |
|---|---|
| 標準ボーダー | `#F0D9B8` |
| 強調ボーダー | `#EFC98A` |
| セクション区切り | `#F0D9B8` |

### テキスト

| 用途 | HEX |
|---|---|
| 見出し・主要テキスト | `#412402` |
| 本文・ラベル | `#633806` |
| 補助テキスト | `#854F0B` |
| ヒント | `#C4986A` |

## アクセントカラー

| 機能 | 背景 | ボーダー | テキスト |
|---|---|---|---|
| 主操作 | `#FAEEDA` | `#C4986A` | `#633806` |
| 成功 | `#EAF3DE` | `#8DB87A` | `#27500A` |
| 警告 | `#FAECE7` | `#D4996E` | `#712B13` |
| エラー | `#FAECE7` | `#D4996E` | `#993C1D` |
| 情報 | `#E6F1FB` | `#85B7EB` | `#0C447C` |

## サイドバー

```css
.sidebar {
  background: #FDF6EC;
  border-right: 1px solid #F0D9B8;
}

.sb-brand-icon {
  background: #BA7517;
  border-radius: 10px;
}

.sb-brand-name {
  color: #412402;
  font-size: 15px;
  font-weight: 500;
}

.sb-brand-sub {
  color: #854F0B;
  font-size: 10px;
}

.sb-link {
  color: #633806;
  border-left: 3px solid transparent;
  border-radius: 8px;
}

.sb-link:hover {
  background: #FAE8CC;
  color: #412402;
}

.sb-link.sb-active {
  background: #FAEEDA;
  border-left-color: #BA7517;
  color: #412402;
  font-weight: 500;
}
```

## 工程カラー

| 工程名 | 背景 | ボーダー | テキスト |
|---|---|---|---|
| プレス | `#AFA9EC` | `#534AB7` | `#3C3489` |
| バレル | `#F4C0D1` | `#993556` | `#72243E` |
| めっき | `#B5D4F4` | `#185FA5` | `#0C447C` |
| 外観検査 | `#FAC775` | `#BA7517` | `#633806` |
| 出荷 | `#C0DD97` | `#3B6D11` | `#27500A` |
| 未定義工程 | `#D3D1C7` | `#5F5E5A` | `#444441` |

## ボタン

```css
.btn-warm {
  background: #FAEEDA;
  border: 1px solid #C4986A;
  color: #633806;
}

.btn-success-warm {
  background: #EAF3DE;
  border: 1px solid #8DB87A;
  color: #27500A;
}

.btn-warn-warm {
  background: #FAECE7;
  border: 1px solid #D4996E;
  color: #712B13;
}
```

## バッジ

```css
.badge-quality.ok {
  background: #EAF3DE;
  color: #27500A;
  border: 1px solid #8DB87A;
}

.badge-quality.ng {
  background: #FAECE7;
  color: #712B13;
  border: 1px solid #D4996E;
}

.badge-quality.warn {
  background: #FAEEDA;
  color: #633806;
  border: 1px solid #C4986A;
}

.badge-quality.none {
  background: #F1EFE8;
  color: #444441;
  border: 1px solid #B4B2A9;
}
```

## 今後のルール

1. 背景は `#FFFBF5` / `#FFFFFF` を基本にする
2. テキストは `#412402` / `#633806` / `#854F0B`
3. ボーダーは `#F0D9B8`
4. ボタンは warm / success-warm / warn-warm
5. 工程カラーはこの設計書の表を使う
6. Bootstrap Icons を使う
