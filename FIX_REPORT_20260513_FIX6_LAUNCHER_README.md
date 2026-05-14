# Fix6: launcher.py / app.py 直接起動時の注意追記

## 修正内容

`PROCESS_KILL_README.md` に、`python app.py` を直接実行した場合の注意事項を追記しました。

## 追記した要点

- `python app.py` でもFlaskは起動可能
- ただし `launcher.py` のプロセスキル機構は使われない
- 5000番ポートの既存プロセス自動終了は行われない
- ブラウザ自動起動も行われない
- `SEIKAN_HOST` / `SEIKAN_PORT` が未設定の場合は `127.0.0.1:5000` にフォールバックする
- 通常運用では `run.bat` または `python launcher.py --open-browser` を推奨

## 影響範囲

コード変更なし。ドキュメント追記のみ。

## 確認ポイント

- `run.bat` では従来どおりプロセスキル機構が動くこと
- `python app.py` では従来どおり手動起動できること
- README上で両者の違いが明確に説明されていること
