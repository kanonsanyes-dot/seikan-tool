# SeikanTool プロセスキル機構

## 目的

Flaskを何度も起動すると、前回のPythonプロセスが残って `127.0.0.1:5000` を掴んだままになることがあります。
この状態だと再起動時にポート競合が起きるため、`run.bat` 実行時に5000番ポートを使用している既存プロセスを自動終了する仕組みを追加しました。

## 追加ファイル

- `launcher.py`
- `run.bat`
- `run_no_kill.bat`

## 通常起動

```bat
run.bat
```

動作：

1. `.venv` がなければ作成
2. `requirements.txt` をインストール
3. `netstat -ano -p tcp` で5000番ポートのLISTENINGプロセスを確認
4. 見つかったPIDを `taskkill /PID <PID> /F /T` で終了
5. Flaskを起動
6. ブラウザで `http://127.0.0.1:5000` を開く

## キルなし起動

他アプリが5000番ポートを使っていて終了したくない場合はこちら。

```bat
run_no_kill.bat
```

## 手動起動

```bat
.venv\Scripts\activate
python launcher.py --open-browser
```

既存プロセスを終了したくない場合：

```bat
python launcher.py --no-kill --open-browser
```

## 注意

この仕組みは「5000番ポートをLISTENINGしているプロセス」を終了します。
通常は前回起動したSeikanToolのPythonプロセスですが、別アプリが5000番を使っている場合も終了対象になります。
その場合は `run_no_kill.bat` を使ってください。

## 直接 `app.py` を実行する場合

```bat
python app.py
```

上記のように `app.py` を直接実行した場合、Flask自体は起動しますが、`launcher.py` のプロセスキル機構は使われません。

つまり、以下は実行されません。

- 5000番ポートを使用中の既存プロセス確認
- 既存プロセスの自動終了
- ブラウザ自動起動
- `launcher.py` 側で指定する `SEIKAN_HOST` / `SEIKAN_PORT` の明示セット

ただし `app.py` にはデフォルト値として `127.0.0.1:5000` へフォールバックする処理があるため、従来どおり手動起動は可能です。

プロセス競合を避けたい通常運用では、基本的に `run.bat` または `python launcher.py --open-browser` を使用してください。

## デバッグ確認項目

- `run.bat` を2回連続で実行しても起動できること
- 前回のPythonプロセスが残っていても自動終了されること
- `run_no_kill.bat` では既存プロセスを終了しないこと
- ブラウザが `http://127.0.0.1:5000` で開くこと
- `app.py` 単体起動時も `SEIKAN_PORT` 環境変数でポート変更できること
