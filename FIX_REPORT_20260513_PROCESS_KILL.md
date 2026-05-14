# Fix4: プロセスキル機構追加

## 対応内容

ユーザー要望により、Flask再起動時のポート競合対策としてプロセスキル機構を追加しました。

## 変更ファイル

- 追加: `launcher.py`
- 追加: `run_no_kill.bat`
- 更新: `run.bat`
- 更新: `app.py`
- 追加: `PROCESS_KILL_README.md`

## 実装概要

`launcher.py` が起動前に `netstat -ano -p tcp` を実行し、5000番ポートをLISTENINGしているPIDを検出します。
検出したPIDに対して `taskkill /PID <PID> /F /T` を実行し、ポート解放後に `app.py` を起動します。

`app.py` は `SEIKAN_HOST` / `SEIKAN_PORT` 環境変数を読むように変更しました。
また、デバッグ時のリローダーによる二重プロセス化を避けるため、`use_reloader=False` を指定しています。

## 確認ポイント

1. `run.bat` で起動する
2. ブラウザで `http://127.0.0.1:5000` が開く
3. 起動中にもう一度 `run.bat` を実行する
4. 前回プロセスがkillされ、新しいプロセスで起動する
5. `run_no_kill.bat` では既存プロセスをkillしない

## 既知の注意点

5000番ポートをSeikanTool以外のアプリが使っている場合、そのプロセスも終了対象になります。
通常運用では問題ありませんが、心配な場合は `run_no_kill.bat` を使用してください。
