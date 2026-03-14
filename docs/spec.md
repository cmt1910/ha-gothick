# spec.md

## 1. 概要

本仕様書は、欧文プログラミングフォント **Hack** と日本語フォント **BIZ UDゴシック** を合成し、さらに **Nerd Fonts** グリフをパッチして、日本語対応の等幅プログラミングフォント**HA-Gothick**を生成するためのビルドパイプライン全体を定義する。

### 1.1 目的

- ターミナル・エディタ上で欧文と日本語が自然に共存する等幅フォントを自動生成する
- Nerd Fonts グリフ（Powerline、Font Awesome、Devicons 等）を統合し、開発環境でアイコン表示を可能にする
- ソースフォントの更新に追従可能な再現性のあるビルドプロセスを確立する
- CI/CD による自動ビルド・リリースを可能にする

### 1.2 使用フォント

| 役割 | フォント名 | ライセンス | 使用ウェイト | UPM |
|---|---|---|---|---|
| 欧文 | Hack | Modified SIL OFL 1.1 + Bitstream Vera License | Regular, Bold | 2048 |
| 日本語 | BIZ UDゴシック (BIZ UDGothic) | SIL OFL 1.1 | Regular, Bold | 1000 |
| アイコン | Nerd Fonts (Symbols Only) | SIL OFL 1.1 (グリフ) / MIT (patcher) | — | — |

**ライセンス互換性:** Hack は Modified SIL OFL 1.1 に加え Bitstream Vera License を含むデュアルライセンスだが、いずれも合成・改変・再配布を許可している。BIZ UDゴシックは SIL OFL 1.1。Nerd Fonts のグリフは SIL OFL 1.1。三者の合成フォントは SIL OFL 1.1 で配布可能。ただし Hack の Reserved Font Name "Hack" は合成フォントに使用できないため、別名を付ける必要がある。

**Hack のメトリクス（参考値）:**

```text
UPM:             2048
CapHeight:       1493
xHeight:         1120
TypoAscender:    1901
TypoDescender:   -483
WinAscent:       1901
WinDescent:      483
TypoLineGap:     0
hhea Ascent:     1901
hhea Descent:    -483
hhea LineGap:    0
```

### 1.3 技術スタック

| カテゴリ | ツール | 用途 |
|---|---|---|
| 実行基盤 | **Docker** | ローカル / CI のビルド環境固定 (`linux/amd64`) |
| パッケージ管理 | **uv** | Python プロジェクト管理・依存解決・仮想環境 |
| テーブル操作 | **fontTools** (uv 経由で管理) | name / OS/2 / hhea 等のメタデータ編集、TTX ダンプ、サブセット化 |
| グリフ操作 | **FontForge** (system Python bindings) | フォントの読み込み、スケーリング、マージ、アウトライン最適化 |
| ヒンティング | **ttfautohint** | TrueType 自動ヒンティング |

補助ツール（fontTools に付属、または検証用）:

| ツール | 用途 |
|---|---|
| pyftsubset (fontTools 付属) | 不要グリフの除去・サブセット化 |
| ttx (fontTools 付属) | フォントテーブルの XML ダンプ・検証 |
| fontbakery (任意) | OpenType 仕様準拠チェック |

### 1.4 プロジェクト初期化

```bash
# 依存パッケージを追加
uv add fonttools
uv add pyyaml

# 開発用依存
uv add --dev fontbakery

# ローカル / CI では Docker イメージ内に依存を閉じ込める
# Docker イメージは Linux/amd64 でビルドする
```

実行方針:

- ローカルと CI のビルド・検証は Docker コンテナ内で実行する
- Docker プラットフォームは `linux/amd64` を既定とし、Apple Silicon でも CI と同一条件に揃える
- FontForge 依存スクリプト (`adjust_hack.py`, `adjust_bizud.py`, `merge.py`, `patch_nerd.py`, `optimize.py`) は `fontforge -script` で実行する
- fontTools / PyYAML 依存スクリプト (`patch_tables.py`, `validate.py`) は `uv run python` で実行する
- `python3-fontforge` はシステム Python に入るため、`uv run python` からは直接 import しない前提とする

### 1.5 ディレクトリ構成

```text
font-builder/
├── pyproject.toml            # uv プロジェクト定義・依存管理
├── uv.lock                   # ロックファイル
├── config/
│   └── config.yaml           # ビルドパラメータ定義
├── sources/
│   ├── hack/                 # Hack フォントファイル
│   │   ├── Hack-Regular.ttf
│   │   └── Hack-Bold.ttf
│   ├── bizud/                # BIZ UDゴシック フォントファイル
│   │   ├── BIZUDGothic-Regular.ttf
│   │   └── BIZUDGothic-Bold.ttf
│   └── nerd/                 # Nerd Fonts Symbols Only
│       └── SymbolsNerdFont-Regular.ttf
├── src/
│   └── font_builder/
│       ├── __init__.py
│       ├── build.py          # メインビルドスクリプト
│       ├── adjust_hack.py    # Hack フォント加工
│       ├── adjust_bizud.py   # BIZ UDゴシック加工
│       ├── merge.py          # フォント合成
│       ├── patch_nerd.py     # Nerd Fonts グリフパッチ
│       ├── optimize.py       # アウトライン最適化
│       ├── patch_tables.py   # メタデータ調整 (fontTools)
│       └── validate.py       # 検証スクリプト
├── build/                    # 中間生成物
├── dist/                     # 最終成果物
├── Dockerfile                # ビルド用 Docker イメージ定義
├── .dockerignore             # Docker ビルド除外設定
├── tests/
│   └── rendering/            # 表示テスト用サンプルテキスト
├── build.sh                  # ビルドスクリプト (エントリポイント)
├── validate.sh               # 検証スクリプト (エントリポイント)
├── .github/workflows/
│   └── build.yml
├── LICENSE
├── README.md
└── spec.md                   # 本ドキュメント
```

---

## 2. 設計パラメータ

### 2.1 メトリクス定義

以下の値は `config/config.yaml` で一元管理する。

```yaml
font:
  family_name: "HA-Gothick"
  version: "1.0.0"
  copyright: "Copyright 2026 Your Name"
  license: "SIL Open Font License 1.1"
  license_url: "https://openfontlicense.org"
  vendor_url: "https://github.com/yourname/ha-gothick"

# Hack の UPM (2048) に統一する設計
# BIZ UDゴシック (UPM 1000) は 2048 にスケーリングして統合
metrics:
  upm: 2048
  half_width: 1233              # Hack のグリフ幅に準拠
  full_width: 2466              # half_width × 2（厳密に2倍）
  ascender: 1556
  descender: -492
  line_gap: 0
  typo_ascender: 1901
  typo_descender: -483
  typo_line_gap: 0
  win_ascent: 1901
  win_descent: 483              # 正の値（符号はテーブル書き込み時に処理）
  x_height: 1120
  cap_height: 1493
  is_fixed_pitch: true

sources:
  hack:
    dir: "sources/hack"
    original_upm: 2048
  bizud:
    dir: "sources/bizud"
    original_upm: 1000
  nerd:
    dir: "sources/nerd"
    file: "SymbolsNerdFont-Regular.ttf"

weights:
  - name: "Regular"
    hack: "Hack-Regular.ttf"
    bizud: "BIZUDGothic-Regular.ttf"
  - name: "Bold"
    hack: "Hack-Bold.ttf"
    bizud: "BIZUDGothic-Bold.ttf"

nerd_fonts:
  include_sets:
    - powerline           # Powerline 基本記号
    - powerline_extra     # Powerline Extra
    - font_awesome        # Font Awesome
    - devicons            # Devicons
    - octicons            # Octicons
    - font_logos          # Font Logos (旧 Font Linux)
    - material_design     # Material Design Icons
    - weather             # Weather Icons
    - codicons            # VS Code Codicons
  exclude_sets:
    - pomicons            # 商用ライセンスのため除外
```

### 2.2 半角:全角幅比

**厳守事項:** `full_width` は `half_width` の正確に 2 倍でなければならない。これはプログラミング用等幅フォントの根幹要件である。

### 2.3 ライセンス要件

合成フォントは SIL Open Font License 1.1 で配布する。以下の制約を遵守する:

- Hack の Reserved Font Name "Hack" を合成フォント名に含めないこと
- BIZ UDゴシックの著作権表示を LICENSE に含めること
- Nerd Fonts のグリフソース情報とリンクを LICENSE に記載すること

---

## 3. フェーズ定義

### フェーズ 1: 素材フォントの取得と検証

#### 入力

- Hack フォントファイル（GitHub Releases から取得）
- BIZ UDゴシック フォントファイル（Google Fonts から取得）
- Nerd Fonts Symbols Only フォントファイル（GitHub Releases から取得）

#### 処理

1. **ソースフォントのダウンロード** — 各フォントの最新リリースを取得し `sources/` に配置する
2. **ライセンス確認** — 各フォントの LICENSE ファイルを `sources/` に同梱し、合成・改変・再配布が許可されていることを確認する
3. **基本メトリクスの記録** — fontTools を使って各フォントの UPM、Ascender、Descender、平均グリフ幅を記録する

```bash
# fontTools で Hack のメトリクスを確認
uv run python -c "
from fontTools.ttLib import TTFont
font = TTFont('sources/hack/Hack-Regular.ttf')
print('UPM:', font['head'].unitsPerEm)
print('xHeight:', font['OS/2'].sxHeight)
print('CapHeight:', font['OS/2'].sCapHeight)
"
```

1. **ウェイト対応の確認** — 本プロジェクトの出力ウェイトは Hack / BIZ UDゴシックともに `Regular` と `Bold` のみを対象とする

#### 出力

- `sources/` ディレクトリに配置されたフォントファイル群
- 各フォントのメトリクス記録
- `config.yaml` の `sources` セクションへの反映

#### 判定基準

- Hack: Modified SIL OFL 1.1 + Bitstream Vera License であること
- BIZ UDゴシック: SIL OFL 1.1 であること
- Nerd Fonts Symbols: SIL OFL 1.1 であること

---

### フェーズ 2: Hack フォントの加工

**スクリプト:** `src/font_builder/adjust_hack.py`

#### 入力

- Hack ソースフォント（UPM: 2048）
- `config.yaml` のメトリクス定義

#### 処理

##### 2.1 フォントの読み込みと検証

```python
import fontforge
hack = fontforge.open("sources/hack/Hack-Regular.ttf")
assert hack.em == 2048  # Hack の UPM は設計値と同じ
```

Hack の UPM は 2048 で、設計値の `upm: 2048` と一致するため、UPM のスケーリングは不要。

##### 2.2 グリフ幅の確認と正規化

Hack は等幅フォントのため、すべてのグリフ幅は原則統一されている。以下を確認する:

```
対象: U+0020 ~ U+007E (Basic Latin)
      U+00A0 ~ U+00FF (Latin-1 Supplement)
      その他 Latin Extended 範囲
```

確認手順:

1. 全グリフの advance width を走査
2. `half_width` (1233) と異なる幅のグリフをリスト化
3. 差異がある場合のみアウトラインのスケーリングと中央揃えを実施

Hack は既にプログラミング用に設計されているため、大幅な修正は不要な想定。

##### 2.3 垂直メトリクスの確認

Hack の元のメトリクスをそのまま継承する設計のため、垂直方向の加工は原則不要。ただし以下を確認する:

- アウトラインの上端・下端が `win_ascent` (1901) / `win_descent` (483) の範囲を超えるグリフの有無
- 超過するグリフがある場合はリスト化し、対応を判断する

##### 2.4 Hack 固有の特徴の保持

Hack はプログラミング用途に最適化された以下の特徴を持つ。これらが加工で損なわれないことを確認する:

| 特徴 | 確認項目 |
|---|---|
| `0` のスラッシュ付きゼロ | 維持されていること |
| `1` / `l` / `I` の明確な区別 | 各グリフ形状が保持されていること |
| Powerline グリフ内蔵 | Nerd Fonts パッチで上書き予定のため影響なし |
| 半太字句読点 | 句読点の太さが維持されていること |

#### 出力

- 加工済み Hack フォント（中間ファイル `build/hack_adjusted.sfd`）

#### 検証項目

- 全グリフの `advance width` が `half_width` (1233) に一致すること
- グリフの視覚的品質が維持されていること

---

### フェーズ 3: BIZ UDゴシックの加工

**スクリプト:** `src/font_builder/adjust_bizud.py`

#### 入力

- BIZ UDゴシック ソースフォント（UPM: 1000）
- `config.yaml` のメトリクス定義

#### 処理

##### 3.1 UPM の統一

BIZ UDゴシックの UPM (1000) を Hack に合わせて 2048 にスケーリングする。

```python
bizud = fontforge.open("sources/bizud/BIZUDGothic-Regular.ttf")
bizud.em = 2048  # FontForge が全アウトラインを自動スケーリング
```

スケーリング係数: 2048 / 1000 = 2.048

##### 3.2 全角グリフのスケーリング

UPM 統一後、全角グリフの advance width を `full_width` (2466) に調整する。

対象 Unicode 範囲:

```
U+3000 ~ U+303F  CJK記号・句読点
U+3040 ~ U+309F  ひらがな
U+30A0 ~ U+30FF  カタカナ
U+4E00 ~ U+9FFF  CJK統合漢字
U+F900 ~ U+FAFF  CJK互換漢字
U+FF01 ~ U+FF60  全角英数字・記号
U+FFE0 ~ U+FFE6  全角通貨記号等
```

処理:

1. UPM スケーリング後のグリフ幅と `full_width` の比率を計算
2. 縦横均等スケーリングを適用（アスペクト比を維持）
3. グリフを `full_width` の枠内で中央揃え
4. `advance width` を `full_width` に強制設定

##### 3.3 半角カナ・半角記号の処理

対象:

```
U+FF65 ~ U+FF9F  半角カタカナ
U+FFE8 ~ U+FFEE  半角記号
```

これらのグリフは `half_width` (1233) にスケーリングし、`advance width` を `half_width` に設定する。

##### 3.4 ベースライン・垂直位置の調整

BIZ UDゴシックは日本語フォントとして仮想ボディの中央に字面が配置される設計。Hack のベースラインと自然に揃うよう、以下の手順で垂直オフセットを計算・適用する:

1. Hack 側の `x_height` (1120) の中央位置を算出
2. BIZ UDゴシックの字面中央位置を算出（UPM スケーリング後の値を使用）
3. 差分を `y_offset` としてすべての日本語グリフに `translate(0, y_offset)` を適用

オフセット値は `config.yaml` でオーバーライド可能とする。

##### 3.5 欧文範囲グリフの除去

Hack 側でカバーする範囲のグリフを BIZ UDゴシックから削除し、マージ時の衝突を防ぐ:

```
削除対象:
U+0000 ~ U+00FF  Basic Latin + Latin-1 Supplement
U+0100 ~ U+024F  Latin Extended-A/B
```

ただし以下はフェーズ 4 で BIZ UDゴシック側のグリフを優先採用するため、削除対象から除外する:

```
保持対象:
U+00A5  ¥ (円記号 — 日本語フォントのデザインを優先)
U+203E  ‾ (オーバーライン)
```

#### 出力

- 加工済み BIZ UDゴシック フォント（中間ファイル `build/bizud_adjusted.sfd`）

#### 検証項目

- 全角グリフの `advance width` が `full_width` (2466) に一致すること
- 半角カナの `advance width` が `half_width` (1233) に一致すること
- 欧文範囲のグリフが正しく除去されていること（保持対象を除く）

---

### フェーズ 4: フォント合成（マージ）

**スクリプト:** `src/font_builder/merge.py`

#### 入力

- 加工済み Hack フォント (`build/hack_adjusted.sfd`)
- 加工済み BIZ UDゴシック フォント (`build/bizud_adjusted.sfd`)

#### 処理

##### 4.1 マージ実行

```python
base = fontforge.open("build/hack_adjusted.sfd")
base.mergeFonts("build/bizud_adjusted.sfd")

# 例外コードポイントのみ BIZ UDゴシック側を優先採用
for codepoint in (0x00A5, 0x203E):
    copy_glyph_from_bizud(base, "build/bizud_adjusted.sfd", codepoint)
```

Hack をベースとし、BIZ UDゴシックのグリフを追加統合する。既存グリフは上書きされないため、フェーズ 3.5 での除去処理を前提としつつ、`U+00A5` / `U+203E` はマージ後に明示的に BIZ UDゴシック由来へ置換する。

##### 4.2 グリフ優先度の解決

以下の範囲について、どちらのフォントのグリフを採用するか明示的に制御する:

| Unicode 範囲 | 採用元 | 理由 |
|---|---|---|
| U+0020 ~ U+007E | Hack | ASCII は Hack のデザインを維持 |
| U+00A5 (¥) | BIZ UDゴシック | 日本語環境での慣例 |
| U+203E (‾) | BIZ UDゴシック | 日本語環境での慣例 |
| U+2500 ~ U+257F (罫線) | Hack | プログラミング用途で半角幅が自然 |
| U+FF01 ~ U+FF5E (全角英数) | BIZ UDゴシック | 全角幅を維持 |
| U+E0A0 ~ U+E0D4 (Powerline) | Nerd Fonts (フェーズ 5 で明示置換) | 統一的な Nerd Fonts アイコンを使用 |

##### 4.3 スペース文字の幅設定

```
U+0020 (Space)        → half_width  (1233)
U+00A0 (NBSP)         → half_width  (1233)
U+3000 (全角スペース)  → full_width  (2466)
U+2002 (En Space)     → half_width  (1233)
U+2003 (Em Space)     → full_width  (2466)
```

#### 出力

- マージ済みフォント (`build/merged.ttf`)

#### 検証項目

- 合計グリフ数が想定範囲内であること
- コードポイントの重複がないこと
- ASCII 範囲のグリフが Hack 由来であること
- CJK 範囲のグリフが BIZ UDゴシック由来であること

---

### フェーズ 5: Nerd Fonts グリフのパッチ

**スクリプト:** `src/font_builder/patch_nerd.py`

#### 入力

- マージ済みフォント (`build/merged.ttf`)
- Nerd Fonts Symbols Only フォント (`sources/nerd/SymbolsNerdFont-Regular.ttf`)
- `config.yaml` の `nerd_fonts` セクション

#### 処理

##### 5.1 パッチ方式

本プロジェクトでは `SymbolsNerdFont-Regular.ttf` を直接読み込み、`patch_nerd.py` で必要なグリフだけを選択的にマージする。これにより、Powerline 範囲のみを Nerd Fonts 由来に明示置換し、それ以外の既存グリフは保持できる。

```python
merged = fontforge.open("build/merged.ttf")
nerd = fontforge.open("sources/nerd/SymbolsNerdFont-Regular.ttf")

# 必要な範囲のグリフのみを選択的にマージ
for glyph in nerd.glyphs():
    codepoint = glyph.unicode
    if is_target_nerd_glyph(codepoint):
        # Powerline 範囲は置換、それ以外は未使用コードポイントへの追加のみ許可
        if codepoint in POWERLINE_CODEPOINTS or not merged_has_glyph(merged, codepoint):
            # グリフを half_width にスケーリング
            scale = half_width / glyph.width if glyph.width > 0 else 1.0
            glyph.transform(psMat.scale(scale, scale))
            glyph.width = half_width
            # マージ先に挿入
            paste_glyph(merged, nerd, codepoint)
```

Nerd Fonts 公式 `font-patcher` は参考実装として扱う。`--careful` を付けると Powerline を置換できず、外すと意図しない上書き範囲が広がるため、本仕様の標準フローには採用しない。

##### 5.2 対象グリフセットと Unicode 範囲

```
Powerline:           U+E0A0 ~ U+E0A3, U+E0B0 ~ U+E0D4
Powerline Extra:     U+E0A0 ~ U+E0A3, U+E0B0 ~ U+E0D4 (拡張分)
Font Awesome:        U+E200 ~ U+E2FF (Nerd Fonts PUA 内配置)
Devicons:            U+E700 ~ U+E7FF
Octicons:            U+F400 ~ U+F4FF
Font Logos:          U+F300 ~ U+F3FF
Material Design:     U+F0001 ~ U+F1AF0 (Supplementary PUA)
Weather:             U+E300 ~ U+E3FF
Codicons:            U+EA60 ~ U+EC00
```

注意: Pomicons (U+E000 ~ U+E00A) は商用ライセンスのため除外する。

##### 5.3 Nerd Fonts グリフの幅調整

等幅フォントとして、Nerd Fonts グリフはすべて `half_width` (1233) に収める:

- ダブルワイズグリフ → `half_width` にスケーリング（`patch_nerd.py` 内で明示処理）
- グリフが半角幅に収まるよう中央揃え

#### 出力

- Nerd Fonts パッチ済みフォント (`build/nerd_patched.ttf`)

#### 検証項目

- Powerline 記号（U+E0A0〜U+E0D4）が存在すること
- 全 Nerd Fonts グリフの advance width が `half_width` であること
- Powerline 範囲（U+E0A0〜U+E0D4）のみ Nerd Fonts 由来に置換されていること
- Powerline 範囲以外の既存 Hack / BIZ UDゴシック グリフが上書きされていないこと
- Pomicons が含まれていないこと

---

### フェーズ 6: メタデータ・テーブル調整

**スクリプト:** `src/font_builder/patch_tables.py`

#### 入力

- Nerd Fonts パッチ済みフォント (`build/nerd_patched.ttf`)
- `config.yaml` のメタデータ定義

#### 処理

fontTools (`TTFont`) を使用して各テーブルを編集する。

```bash
# uv 経由で実行
uv run python src/font_builder/patch_tables.py
```

##### 6.1 name テーブル

| nameID | 内容 | 値 |
|---|---|---|
| 0 | Copyright | "Copyright 2026 Your Name. Hack (c) Christopher Simpkins. BIZ UDGothic (c) Morisawa Inc." |
| 1 | Font Family | "HA-Gothick" |
| 2 | Subfamily | "Regular" / "Bold" |
| 4 | Full Name | "HA-Gothick Regular" / "HA-Gothick Bold" |
| 5 | Version | "Version 1.0.0" |
| 6 | PostScript Name | "HA-Gothick-Regular" / "HA-Gothick-Bold" |
| 11 | Vendor URL | "<https://github.com/yourname/ha-gothick>" |
| 13 | License | "This Font Software is licensed under the SIL OFL 1.1" |
| 14 | License URL | "<https://openfontlicense.org>" |

platformID 1 (Mac) と platformID 3 (Windows) の両方に設定する。

```python
from fontTools.ttLib import TTFont

font = TTFont("build/nerd_patched.ttf")
name_table = font["name"]

# 既存エントリをクリアして新規設定
entries = {
    0: config["font"]["copyright"],
    1: config["font"]["family_name"],
    # ... 以下同様
}

for name_id, value in entries.items():
    name_table.setName(value, name_id, 3, 1, 0x0409)  # Windows
    name_table.setName(value, name_id, 1, 0, 0)         # Mac
```

##### 6.2 OS/2 テーブル

```python
os2 = font["OS/2"]
os2.sTypoAscender  = 1901
os2.sTypoDescender = -483
os2.sTypoLineGap   = 0
os2.usWinAscent    = 1901
os2.usWinDescent   = 483
os2.sxHeight       = 1120
os2.sCapHeight     = 1493
os2.xAvgCharWidth  = average_non_zero_widths(font["hmtx"])
os2.panose.bProportion = 9         # Monospaced
os2.fsSelection    |= (1 << 6)     # USE_TYPO_METRICS フラグを設定

# Unicode 範囲ビットフラグ — 実際のグリフ収録範囲に基づいて設定
# Code Page 範囲ビットフラグ — 同上
```

##### 6.3 hhea テーブル

```python
hhea = font["hhea"]
hhea.ascent   = 1901
hhea.descent  = -483
hhea.lineGap  = 0
```

OS/2 と hhea のメトリクスを整合させることで、Windows / macOS 間の行間差異を防ぐ。

##### 6.4 head テーブル

```python
head = font["head"]
# macStyle: 0 = Regular, 1 = Bold
# unitsPerEm が 2048 であることを確認
assert head.unitsPerEm == 2048
```

##### 6.5 post テーブル

```python
post = font["post"]
post.isFixedPitch = 1  # 等幅フォントであることを宣言
post.formatType = 2.0
```

##### 6.6 cmap テーブル検証

全グリフのコードポイントマッピングを走査し、以下を確認する:

- マッピングの欠落がないこと
- 意図しない重複マッピングがないこと
- U+00AD (Soft Hyphen) を最終成果物から除去すること
- Format 4 (BMP) と Format 12 (Full Unicode) の両テーブルが存在すること
- Nerd Fonts の Supplementary PUA 範囲が Format 12 でカバーされていること
- GSUB の ligature に対する GDEF caret 情報が生成されていること

#### 出力

- メタデータ調整済みフォント (`build/patched.ttf`)

---

### フェーズ 7: ヒンティングと最適化

#### 入力

- メタデータ調整済みフォント (`build/patched.ttf`)

#### 処理

##### 7.1 アウトライン最適化

FontForge スクリプト `src/font_builder/optimize.py` を使用して以下を実行:

1. **オーバーラップ除去** — `removeOverlap()` で重複パスを統合
2. **パス方向の統一** — TrueType: 外郭は時計回り、内郭は反時計回り
3. **輪郭正規化** — `canonicalContours()` / `canonicalStart()` で輪郭順序と開始点を安定化
4. **重複ポイント除去** — `round()` と `simplify()` で冗長なポイント・重複セグメントを削減
5. **極値ポイントの追加** — カーブの極値位置にポイントを配置（ヒンティング品質向上）

##### 7.2 自動ヒンティング (ttfautohint)

```bash
ttfautohint \
  --stem-width-mode=nnn \
  --increase-x-height=14 \
  --no-info \
  --fallback-script=latn \
  build/optimized.ttf \
  build/hinted.ttf
```

パラメータ:

- `--stem-width-mode=nnn` — 各サイズでステム幅をスナップしない（日本語グリフとの相性を考慮）
- `--increase-x-height=14` — 14ppem 以下で x-height を 1px 引き上げ
- `--fallback-script=latn` — 未認識グリフ（日本語・Nerd Fonts 含む）に Latin ヒントをフォールバック適用

注意: ttfautohint は Hack の欧文グリフに対して最も効果的。BIZ UDゴシックの日本語グリフおよび Nerd Fonts グリフに対する効果は限定的で、レンダリング品質は主に OS 側のラスタライザに依存する。

##### 7.3 サブセット化（任意）

配布サイズ削減のためにグリフを絞る場合:

```bash
uv run pyftsubset build/hinted.ttf \
  --unicodes="U+0000-00FF,U+0100-024F,U+2500-257F,U+3000-303F,U+3040-309F,U+30A0-30FF,U+4E00-9FFF,U+FF00-FFEF,U+E0A0-E0D4,U+E200-EC00,U+F0001-F1AF0" \
  --layout-features='*' \
  --name-IDs='*' \
  --output-file="build/subset.ttf"
```

#### 出力

- アウトライン最適化済みフォント (`build/optimized.ttf`)
- 最終フォントファイル (`dist/HA-Gothick-Regular.ttf`)

---

### フェーズ 8: 検証・テスト

**スクリプト:** `src/font_builder/validate.py`

#### 8.1 構造検証（自動）

```bash
# fontTools による TTX ダンプ・検証
uv run ttx -l dist/HA-Gothick-Regular.ttf   # テーブル一覧
uv run ttx -t OS/2 dist/HA-Gothick-Regular.ttf  # OS/2 テーブル詳細

# fontbakery による包括的チェック（任意）
uv run fontbakery check-universal dist/HA-Gothick-Regular.ttf
```

自動チェック項目:

| チェック項目 | 期待値 |
|---|---|
| `post.isFixedPitch` | `1` |
| `post.formatType` | `2.0` |
| `OS/2.panose.bProportion` | `9` (Monospaced) |
| `OS/2.xAvgCharWidth` | 非ゼロ幅グリフの平均値 |
| `OS/2.sTypoAscender` | `1901` |
| `OS/2.sTypoDescender` | `-483` |
| `OS/2.sTypoLineGap` | `0` |
| `head.unitsPerEm` | `2048` |
| 全 ASCII グリフの width | `1233` (half_width) |
| 全 CJK グリフの width | `2466` (full_width) |
| 全 Nerd Fonts グリフの width | `1233` (half_width) |
| `hhea.ascent` | `1901` |
| `hhea.descent` | `-483` |
| `hhea.lineGap` | `0` |
| Powerline グリフ (U+E0A0) の存在 | `True` |
| Pomicons (U+E000) の不在 | `True` |
| Soft Hyphen (U+00AD) の不在 | `True` |
| GDEF ligature caret | `True` |

既知の保留事項:

- `chws` / `vchw` feature は未実装。必要になった段階で `chws_tool` 導入を検討する。
- `alt_caron` と `contour_count` は自動チェックだけでは設計差と不具合を分離できないため、最終的に手動 QA を行う。

#### 8.2 表示テスト（手動）

テスト用サンプルテキスト (`tests/rendering/sample.txt`):

```
ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz
0123456789 0O 1lI `'" {}()[] <>
あいうえおかきくけこさしすせそたちつてと
アイウエオカキクケコサシスセソタチツテト
一二三四五六七八九十百千万億兆
ﾊﾝｶｸｶﾅ  （全角英数ＡＢＣＤ１２３４）
─│┌┐└┘├┤┬┴┼  ═║╔╗╚╝╠╣╦╩╬
→ ← ↑ ↓ ● ○ ■ □ ▲ △
if (x == 0) { return "hello"; }  // コメント
fn main() -> Result<(), Box<dyn Error>> {}
λ α β γ δ ε ∀ ∃ ∈ ∉ ⊂ ⊃ ∪ ∩
      (Nerd Fonts: Powerline / devicons / etc.)
```

テスト環境マトリクス:

| OS | アプリケーション | フォントサイズ |
|---|---|---|
| Windows 10/11 | VSCode, Windows Terminal | 9, 10, 12, 14, 16, 18 pt |
| macOS | VSCode, Terminal.app, iTerm2 | 同上 |
| Linux (Ubuntu) | VSCode, GNOME Terminal | 同上 |
| ブラウザ | Chrome, Firefox | 同上 |

確認項目:

- 半角文字2つ分 = 全角文字1つ分の幅が厳密に一致すること
- 行間が適切であること（文字の上下が切れていないこと）
- アンチエイリアスが自然であること
- Hack 由来の `0O`, `1lI`, `''"` が明確に判別できること
- BIZ UDゴシック由来の日本語文字が読みやすいこと
- 罫線文字が隣接セルと正しく接続すること
- Nerd Fonts の Powerline 記号が途切れなく表示されること
- Nerd Fonts のアイコン（devicons 等）が正しく表示されること

#### 8.3 回帰テスト

ソースフォント更新時に前バージョンとの差分を自動比較する:

- グリフ数の増減
- メトリクス値の変動
- ファイルサイズの変動（10% 以上の変動で警告）

---

### フェーズ 9: ビルド自動化とリリース

#### 9.1 ビルドスクリプト (`build.sh`)

`build.sh` は二段構成とする。

- ホスト実行時:
  Docker イメージを `--platform linux/amd64` でビルドし、コンテナ内で同じ `build.sh` を再実行する
- コンテナ内実行時:
  既存の FontForge / `uv` / `ttfautohint` ベースのビルド本体を実行する

主要な環境変数:

- `DOCKER_IMAGE`
  使用するイメージ名。既定値は `ha-gothick-build:latest`
- `DOCKER_PLATFORM`
  Docker プラットフォーム。既定値は `linux/amd64`
- `HA_GOTHICK_BUILD_IN_CONTAINER`
  コンテナ内実行フラグ。ホストからの直接指定は不要

ホスト側の実行イメージ:

```bash
docker build --platform linux/amd64 -t ha-gothick-build:latest .
docker run --rm \
  --platform linux/amd64 \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp/ha-gothick-home \
  -e UV_CACHE_DIR=/work/.uv-cache \
  -e HA_GOTHICK_BUILD_IN_CONTAINER=1 \
  -v "$PWD:/work" \
  -w /work \
  ha-gothick-build:latest \
  bash ./build.sh
```

#### 9.2 検証スクリプト (`validate.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# validate.sh — ビルド成果物の検証
# ============================================================

DIST_DIR="${1:-dist}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log()  { printf "\033[1;34m[INFO]\033[0m  %s\n" "$*"; }
err()  { printf "\033[1;31m[FAIL]\033[0m %s\n" "$*" >&2; }

EXIT_CODE=0

# フォントファイルの存在チェック
for ttf in "${DIST_DIR}"/HA-Gothick-*.ttf; do
    if [[ ! -f "${ttf}" ]]; then
        err "フォントファイルが見つかりません: ${ttf}"
        EXIT_CODE=1
        continue
    fi
    log "検証中: $(basename "${ttf}")"
    uv run python src/font_builder/validate.py "${ttf}"
done

# fontbakery による包括的チェック（任意）
if command -v fontbakery >/dev/null 2>&1 || uv run fontbakery --version >/dev/null 2>&1; then
    log "fontbakery check-universal を実行"
    uv run fontbakery check-universal "${DIST_DIR}"/HA-Gothick-*.ttf \
        --checkrunner-log-level WARN || true
fi

# TTX テーブルダンプ（参照用）
log "TTX テーブルダンプを build/ttx/ に出力"
mkdir -p build/ttx
for ttf in "${DIST_DIR}"/HA-Gothick-*.ttf; do
    uv run ttx -l "${ttf}" > "build/ttx/$(basename "${ttf}" .ttf)_tables.txt" 2>&1
    uv run ttx -t OS/2 -o "build/ttx/$(basename "${ttf}" .ttf)_OS2.ttx" "${ttf}" 2>&1
done

exit ${EXIT_CODE}
```

#### 9.3 ローカル実行方針

本プロジェクトのローカル実行は Docker 前提とする。ホストに直接必要なのは `docker` のみで、FontForge / `ttfautohint` / `uv` は Docker イメージ内に閉じ込める。

- ローカル実行と GitHub Actions の差分を減らすため、`linux/amd64` を既定とする
- `setup_build_env.sh` はソースフォント取得と `uv sync --extra dev --python 3.12` を行う
- `build.sh` はホスト側で Docker イメージをビルドし、コンテナ内でビルド本体を実行する
- `validate.sh` は生成済み成果物に対して `src/font_builder/validate.py`、`fontbakery`、`ttx` を実行する

```bash
# 前処理
docker run --rm \
  --platform linux/amd64 \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp/ha-gothick-home \
  -e UV_CACHE_DIR=/work/.uv-cache \
  -v "$PWD:/work" \
  -w /work \
  ha-gothick-build:latest \
  bash ./setup_build_env.sh

# ビルド
bash ./build.sh

# 検証
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

#### 9.4 GitHub Actions ワークフロー

```yaml
# .github/workflows/build.yml
name: Build Font

on:
  push:
    tags: ["v*"]
  workflow_dispatch:

env:
  DOCKER_PLATFORM: linux/amd64

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: |
          docker build --platform "${DOCKER_PLATFORM}" -t ha-gothick-build-ci .

      - name: Build fonts
        run: |
          docker run --rm \
            --platform "${DOCKER_PLATFORM}" \
            --user "$(id -u):$(id -g)" \
            -e HOME=/tmp/ha-gothick-home \
            -e UV_CACHE_DIR=/work/.uv-cache \
            -v "${GITHUB_WORKSPACE}:/work" \
            -w /work \
            ha-gothick-build-ci \
            bash ./setup_build_env.sh

          docker run --rm \
            --platform "${DOCKER_PLATFORM}" \
            --user "$(id -u):$(id -g)" \
            -e HOME=/tmp/ha-gothick-home \
            -e UV_CACHE_DIR=/work/.uv-cache \
            -e HA_GOTHICK_BUILD_IN_CONTAINER=1 \
            -v "${GITHUB_WORKSPACE}:/work" \
            -w /work \
            ha-gothick-build-ci \
            bash ./build.sh

      - name: Validate fonts
        run: |
          docker run --rm \
            --platform "${DOCKER_PLATFORM}" \
            --user "$(id -u):$(id -g)" \
            -e HOME=/tmp/ha-gothick-home \
            -e UV_CACHE_DIR=/work/.uv-cache \
            -v "${GITHUB_WORKSPACE}:/work" \
            -w /work \
            ha-gothick-build-ci \
            bash ./validate.sh

      - name: Package release assets
        if: startsWith(github.ref, 'refs/tags/')
        run: |
          mkdir -p release
          zip -j "release/ha-gothick-${GITHUB_REF_NAME}.zip" \
            dist/*.ttf \
            dist/LICENSE.txt \
            dist/README.md

      - uses: softprops/action-gh-release@v2
        if: startsWith(github.ref, 'refs/tags/')
        with:
          files: release/ha-gothick-${{ github.ref_name }}.zip
```

`env.DOCKER_PLATFORM` は `linux/amd64` を指定する。

#### 9.5 リリース成果物

```text
release/
└── ha-gothick-v1.zip
```

---

## 4. エラーハンドリング方針

| エラー種別 | 対応 |
|---|---|
| BIZ UDゴシックの UPM スケーリング誤差 | 丸め処理を記録、座標の最大誤差が 1 unit 以内であることを確認 |
| グリフ幅が目標値に収束しない | 警告ログ + 強制設定 |
| マージ時のコードポイント衝突 | フェーズ 4.2 の優先度テーブルに基づき解決、想定外の衝突はエラー停止 |
| Nerd Fonts patcher 失敗 | 方式 B（自前マージ）にフォールバック |
| ttfautohint 失敗 | ヒンティングなし版を出力（警告付き） |
| fontbakery FAIL 項目 | ビルド失敗とせず、レポートを出力して手動判断 |
| uv sync 失敗 | ロックファイルの整合性を確認、`uv lock` で再生成 |

---

## 6. 参考資料

- [Hack — A typeface designed for source code](https://sourcefoundry.org/hack/)
- [Hack GitHub Repository](https://github.com/source-foundry/Hack)
- [BIZ UDGothic — Google Fonts](https://fonts.google.com/specimen/BIZ+UDGothic)
- [BIZ UDGothic GitHub Repository](https://github.com/googlefonts/morisawa-biz-ud-gothic)
- [Nerd Fonts — Iconic font aggregator & patcher](https://www.nerdfonts.com/)
- [Nerd Fonts GitHub Repository](https://github.com/ryanoasis/nerd-fonts)
- [FontForge Python Scripting](https://fontforge.org/docs/scripting/python.html)
- [fontTools Documentation](https://fonttools.readthedocs.io/)
- [uv — Python Package Manager](https://docs.astral.sh/uv/)
- [ttfautohint Documentation](https://freetype.org/ttfautohint/doc/)
- [OpenType Specification (Microsoft)](https://learn.microsoft.com/typography/opentype/spec/)
- [SIL Open Font License 1.1](https://openfontlicense.org/)
- [HackGen Build Process (参考実装)](https://github.com/yuru7/HackGen)
- [PlemolJP Build Process (参考実装)](https://github.com/yuru7/PlemolJP)
