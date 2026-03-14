# HA-Gothick

Hack と BIZ UDゴシックを合成し、Nerd Fonts の Symbols Only グリフを統合した日本語対応等幅プログラミングフォントのビルド環境です。

## 構成

- 欧文: Hack
- 日本語: BIZ UDGothic
- アイコン: Nerd Fonts Symbols Only
- Python パッケージ管理: `uv`
- フォント加工: `FontForge`
- 自動ヒンティング: `ttfautohint`
- 実行環境: `Docker` (`linux/amd64`)

詳細仕様は [docs/spec.md](docs/spec.md) を参照してください。

## 前提ツール

- `docker`

ローカル実行はホストに `uv` / `fontforge` / `ttfautohint` を直接入れず、Docker コンテナ内で行います。Apple Silicon 環境でも CI と同じ結果になるよう、既定で `linux/amd64` イメージを使用します。

確認コマンド:

```bash
docker --version
```

利用可能な環境変数:

```bash
DOCKER_IMAGE=ha-gothick-build:latest
DOCKER_PLATFORM=linux/amd64
```

CI と同じ前処理だけを先に実行したい場合:

```bash
docker run --rm \
  --platform linux/amd64 \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp/ha-gothick-home \
  -e UV_CACHE_DIR=/work/.uv-cache \
  -v "$PWD:/work" \
  -w /work \
  ha-gothick-build:latest \
  bash ./setup_build_env.sh
```

この前処理では `uv sync --extra dev --python 3.12` を実行し、Hack / BIZ UDゴシック / Nerd Fonts Symbols Only を `sources/` に取得します。

## ソースフォント配置

`setup_build_env.sh` を使わず手動で進める場合は、以下のファイルを配置してからビルドしてください。

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
bash ./build.sh
```

単一ウェイトのみビルド:

```bash
bash ./build.sh --weight Regular
```

中間生成物を削除:

```bash
bash ./build.sh --clean
```

`build.sh` はホスト上では Docker イメージをビルドし、そのコンテナ内で実際のビルド処理を実行します。

## 検証

```bash
bash ./validate.sh
```

`validate.sh` は `uv` を利用して `src/font_builder/validate.py` と `fontbakery check-universal` を実行し、TTX ダンプを `build/ttx/` に出力します。ローカルでは `build.sh` と同じ Docker イメージ内での実行を推奨します。例えば次のように実行できます。

```bash
docker run --rm \
  --platform linux/amd64 \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp/ha-gothick-home \
  -e UV_CACHE_DIR=/work/.uv-cache \
  -v "$PWD:/work" \
  -w /work \
  ha-gothick-build:latest \
  bash -lc './validate.sh'
```

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

- `build.sh` はホスト側では Docker ラッパー、コンテナ内ではビルド本体として動作します。
- FontForge 依存スクリプトは `fontforge -script` で実行します。
- fontTools 依存スクリプトは `uv run python` で実行します。
- `uv run python` から `fontforge` モジュールは直接 import しない前提です。

## ライセンス

合成フォントの配布ライセンスは SIL Open Font License 1.1 を想定しています。上流フォントの権利情報は [LICENSE](LICENSE) を参照してください。
