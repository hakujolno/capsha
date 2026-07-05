# Capsha

**Capture. Annotate. Share.**  
by trueWhite

X.comへの投稿準備を最短にする、Windows向けの軽量スクリーンショット注釈ツールです。起動するとすぐ範囲選択が始まり、撮影した画像は自動でクリップボードへ入ります。

UIは「Silent Professional」を軸にしたWindows 11／Fluent風ダークテーマです。弱い立体感と控えめなブルーを使い、画像が主役になる落ち着いた外観にしています。上段は主要操作、下段は選択中のツールに必要な設定だけを表示するコンテキスト型ツールバーです。UIフォントにはSegoe UI Variableを優先します。

## 必要環境

- Windows 10 / 11
- Python 3.11以上（3.12推奨）
- PySide6 6.7以上

## セットアップ

PowerShellでプロジェクトフォルダーを開き、仮想環境を作成します。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 実行

```powershell
python main.py
```

起動直後に画面全体が暗くなります。範囲をドラッグすると撮影・自動コピーされ、編集画面が開きます。撮影中・編集中は `Esc` で即終了し、テキスト入力中だけは入力キャンセルとして動作します。

Windowsの表示言語を起動時に判定し、日本語環境では日本語、それ以外では英語で表示します。外部の翻訳ライブラリや実行中の監視処理は使用しません。

編集画面では次の操作ができます。

- テキスト: 画像をクリックしてその場で直接入力。`Enter`または欄外クリックで確定、`Shift+Enter`で改行、`Esc`でキャンセル。空欄は自動破棄
- 四角 / 矢印 / モザイク: 画像上をドラッグ
- クイックキャプション: `①`ツールでクリックするたびに①〜⑳を連続配置し、その後は21、22…と連番。`Esc`で配置を解除
- 保存: 注釈入りPNGを書き出し
- 保存ショートカット: `Ctrl+S`で保存（初回のみ保存先を指定）、`Ctrl+Shift+S`で名前を付けて保存
- コピー: 編集後の画像をクリップボードへ再コピー
- 𝕏へ: 最新の編集状態をPNG画像へ合成して自動コピーした後、`https://x.com/compose/post` を開く。投稿欄では `Ctrl+V` で貼り付け
- Undo / Redo: Ctrl+Z / Ctrl+Y（追加とテキスト移動に対応）
- コピー: Ctrl+C
- 色チップ・最近の色・線幅・太字: 上部ツールバーから指定
- 四角の塗り: 枠線のみ／塗りありと、0〜100%の透明度を指定
- 選択ツール: 注釈の移動、`Delete`で削除、`Ctrl+D`で複製。テキストはダブルクリックで再編集
- 図形: 角丸、線透明度、実線／破線／点線。`Shift`ドラッグで正方形
- 表示: `Ctrl`+マウスホイールでズーム、`Space`+ドラッグで移動、グリッド、中央フィット
- テキスト: フォント、太字、斜体、アウトラインのON/OFF、文字色とは独立したアウトライン色（初期値は黒）
- テキストサイズ: 8〜240pxを内部管理し、四隅ハンドルから視覚的に変更。半透明背景のON/OFFにも対応
- 選択ハンドル: 四角・モザイク・テキストの四隅、矢印の端点をドラッグしてリサイズ
- テキスト操作: 四隅のハンドルから連続リサイズ。ダブルクリックで再編集、`Delete`で削除、`Ctrl+D`で複製
- 軽量プレビュー: 編集中は元画像と注釈を別々に描画し、PNG全体の合成は保存・コピー時のみ実行
- 画質: HiDPI画面の物理ピクセルを元解像度のまま保持。縮小は編集表示だけに使い、保存・コピー・𝕏では元解像度へ注釈を再描画
- ズーム: 右上に実倍率を表示し、表示メニューから100%／フィットを選択
- 通知: 保存・コピー完了時にキャンバス下部へ短時間のトーストを表示
- ウィンドウ: 画像寸法に依存しない最小サイズを確保し、小画像でも保存・コピー・𝕏へボタンを常時表示。終了はタイトルバーの×または`Esc`
- 保存名: `capsha_YYYYMMDD_HHMMSS.png` を自動提案
- 保存先: 前回使用したフォルダーを記憶
- コピー: Windowsクリップボードへ画像と`image/png`データを設定

## ディレクトリ構成

```text
Capsha/
├─ main.py                 # エントリーポイント
├─ capsha.spec              # PyInstaller one-file設定
├─ requirements.txt
├─ README.md
├─ packaging/
│  └─ windows_version_info.txt # exeのWindowsバージョン情報
├─ scripts/
│  ├─ build_release.ps1     # リリースビルド
│  └─ generate_icon.py      # SVGからマルチサイズICOを生成
└─ capsha/
   ├─ assets/              # 差し替え可能なロゴと軽量UI素材
   ├─ branding.py          # ロゴ読込
   ├─ app.py               # アプリの起動と画面遷移
   ├─ capture.py           # 画面キャプチャと範囲選択
   ├─ editor.py            # 編集ウィンドウと各アクション
   ├─ i18n.py              # 日本語／英語の軽量文字列辞書と言語判定
   ├─ canvas.py            # 注釈キャンバスと画像描画
   └─ annotations.py       # 注釈データ型
```

## タスクバーから素早く起動

exe化したCapshaをWindowsのタスクバーへ固定すると、左からの位置に応じて `Win + 1` などで起動できます。Capsha自身はグローバルホットキーを登録しません。

## ロゴの差し替え

`capsha/assets` 内の `logo.svg` を差し替えるだけで左上のロゴへ反映されます。PNGまたはICOを使う場合は既存のSVGを取り除き、同じフォルダーへ `logo.png` または `logo.ico` を1つ置いてください。起動時に1回だけ読み込み、監視処理は行いません。

## リリースビルド（PyInstaller）

仮想環境を作成して`requirements.txt`をインストールしたあと、プロジェクトルートで次を実行します。

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

このスクリプトは次を自動で行います。

1. `logo.svg`から16〜256pxを含む`capsha.ico`を生成
2. `capsha.spec`を使ってクリーンビルド
3. ロゴ、SVG、UI素材、Windowsバージョン情報をexeへ同梱
4. QML、Quick、WebEngine、PDF、仮想キーボードなど未使用のQt部品を除外

生成後の構成は次のとおりです。

```text
build/                 # PyInstallerの一時ファイル（配布不要）
dist/
└─ Capsha.exe          # 配布ファイル
```

`dist/Capsha.exe`単体で配布できます。PythonやPySide6を配布先へ別途インストールする必要はありません。

specを直接実行する場合は次のコマンドでもビルドできます。

```powershell
python .\scripts\generate_icon.py
python -m PyInstaller --noconfirm --clean .\capsha.spec
```

現在のビルドはone-file／GUIモードで、コンソール画面を表示しません。exeにはCapshaアイコン、製品名、ファイルバージョンが設定されます。
