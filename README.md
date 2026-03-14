# HA-Gothick

Hack と BIZ UDゴシックを合成し、Nerd Fonts の Symbols Only グリフを統合した日本語対応等幅プログラミングフォントのビルド環境です。

## 構成

- 欧文: Hack
- 日本語: BIZ UDGothic
- アイコン: Nerd Fonts Symbols Only
- Python パッケージ管理: `uv`
- フォント加工: `FontForge`
- 自動ヒンティング: `ttfautohint`

詳細仕様は [docs/spec.md](docs/spec.md) を参照してください。

## 前提ツール

- `uv`
- `fontforge`
- `ttfautohint`

macOS:

```bash
brew install fontforge ttfautohint
uv sync
```

Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y fontforge python3-fontforge ttfautohint
uv sync
```

`fontbakery` を含む追加検証も使う場合:

```bash
uv sync --extra dev
```

CI と同じ手順で依存同期とソースフォント取得を行う場合:

```bash
bash ./setup_build_env.sh
```

## ソースフォント配置

以下のファイルを配置してからビルドしてください。

```text
sources/
├── hack/
│   ├── Hack-Regular.ttf
│   └── Hack-Bold.ttf
├── bizud/
│   ├── BIZUDGothic-Regular.ttf
│   └── BIZUDGothic-Bold.ttf
└── nerd/
    └── SymbolsNerdFont-Regular.ttf
```

設定値は [config/config.yaml](config/config.yaml) で管理します。

## ビルド

全ウェイトをビルド:

```bash
bash build.sh
```

単一ウェイトのみビルド:

```bash
bash build.sh --weight Regular
```

中間生成物を削除:

```bash
bash build.sh --clean
```

## 検証

```bash
bash validate.sh
```

`uv sync --extra dev` 済みなら `fontbakery check-universal` も実行します。TTX ダンプは `build/ttx/` に出力されます。

## 出力

ビルド成功時の成果物:

```text
dist/
├── HA-Gothick-Regular.ttf
├── HA-Gothick-Bold.ttf
├── LICENSE.txt
└── README.md
```

## 開発メモ

- FontForge 依存スクリプトは `fontforge -script` で実行します。
- fontTools 依存スクリプトは `uv run python` で実行します。
- `uv run python` から `fontforge` モジュールは直接 import しない前提です。

## ライセンス

合成フォントの配布ライセンスは SIL Open Font License 1.1 を想定しています。上流フォントの権利情報は [LICENSE](LICENSE) を参照してください。
