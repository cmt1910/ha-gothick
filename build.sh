#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="${SCRIPT_DIR}/config/config.yaml"
WEIGHTS=("Regular" "Bold")
FONTBAKERY_SIZE_LIMIT=9000000

log()  { printf "\033[1;34m[INFO]\033[0m  %s\n" "$*"; }
warn() { printf "\033[1;33m[WARN]\033[0m  %s\n" "$*"; }
err()  { printf "\033[1;31m[ERROR]\033[0m %s\n" "$*" >&2; }

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --weight <name>   単一ウェイトのみビルド (Regular|Bold)
  --config <path>   config.yaml のパスを指定 (デフォルト: config/config.yaml)
  --clean           build/ と dist/ を削除して終了
  --help            このヘルプを表示
EOF
    exit 0
}

check_deps() {
    local missing=()
    command -v uv >/dev/null 2>&1 || missing+=("uv")
    command -v fontforge >/dev/null 2>&1 || missing+=("fontforge")
    command -v ttfautohint >/dev/null 2>&1 || missing+=("ttfautohint")
    if [[ ${#missing[@]} -gt 0 ]]; then
        err "以下の依存ツールが見つかりません: ${missing[*]}"
        err "uv          — https://docs.astral.sh/uv/"
        err "fontforge   — macOS: brew install fontforge / Ubuntu: sudo apt install fontforge python3-fontforge"
        err "ttfautohint — macOS: brew install ttfautohint / Ubuntu: sudo apt install ttfautohint"
        exit 1
    fi
}

check_required_files() {
    local required=(
        "${CONFIG}"
        "${SCRIPT_DIR}/README.md"
        "${SCRIPT_DIR}/LICENSE"
        "${SCRIPT_DIR}/src/font_builder/adjust_hack.py"
        "${SCRIPT_DIR}/src/font_builder/adjust_bizud.py"
        "${SCRIPT_DIR}/src/font_builder/merge.py"
        "${SCRIPT_DIR}/src/font_builder/patch_nerd.py"
        "${SCRIPT_DIR}/src/font_builder/patch_tables.py"
        "${SCRIPT_DIR}/src/font_builder/optimize.py"
    )

    local missing=()
    local file
    for file in "${required[@]}"; do
        [[ -f "${file}" ]] || missing+=("${file}")
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        err "必要ファイルが不足しています:"
        printf '  - %s\n' "${missing[@]}" >&2
        exit 1
    fi
}

build_weight() {
    local weight="$1"
    local optimized="build/optimized-${weight}.ttf"
    local hinted="build/hinted-${weight}.ttf"
    local final_input="${hinted}"

    log "=== Building weight: ${weight} ==="

    log "[Phase 2] Hack フォント加工 (${weight})"
    fontforge -script src/font_builder/adjust_hack.py --weight "${weight}" --config "${CONFIG}"

    log "[Phase 3] BIZ UDゴシック加工 (${weight})"
    fontforge -script src/font_builder/adjust_bizud.py --weight "${weight}" --config "${CONFIG}"

    log "[Phase 4] フォント合成 (${weight})"
    fontforge -script src/font_builder/merge.py --weight "${weight}" --config "${CONFIG}"

    log "[Phase 5] Nerd Fonts パッチ (${weight})"
    fontforge -script src/font_builder/patch_nerd.py --weight "${weight}" --config "${CONFIG}"

    log "[Phase 6] メタデータ調整 (${weight})"
    uv run python src/font_builder/patch_tables.py --weight "${weight}" --config "${CONFIG}"

    log "[Phase 7.1] アウトライン最適化 (${weight})"
    fontforge -script src/font_builder/optimize.py --weight "${weight}" --config "${CONFIG}"

    log "[Phase 7.2] ヒンティング (${weight})"
    if ttfautohint \
        --stem-width-mode=nnn \
        --increase-x-height=14 \
        --no-info \
        --fallback-script=latn \
        "${optimized}" "${hinted}" 2>/dev/null; then
        log "ttfautohint 成功"
    else
        warn "ttfautohint 失敗 — ヒンティングなし版を使用"
        cp "${optimized}" "${hinted}"
    fi

    if [[ $(stat -f%z "${hinted}") -gt ${FONTBAKERY_SIZE_LIMIT} ]]; then
        warn "ヒンティング後サイズが ${FONTBAKERY_SIZE_LIMIT} bytes を超過 — ヒンティングなし版を使用"
        final_input="${optimized}"
    fi

    mkdir -p dist
    log "[Phase 7.3] 最終メタデータ再適用 (${weight})"
    uv run python src/font_builder/patch_tables.py \
        --weight "${weight}" \
        --config "${CONFIG}" \
        --input "${final_input}" \
        --output "dist/HA-Gothick-${weight}.ttf"
    cp LICENSE "dist/LICENSE.txt"
    cp README.md "dist/README.md"
    log "=== Done: dist/HA-Gothick-${weight}.ttf ==="
}

TARGET_WEIGHT=""
DO_CLEAN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --weight)
            TARGET_WEIGHT="$2"
            shift 2
            ;;
        --config)
            CONFIG="$2"
            shift 2
            ;;
        --clean)
            DO_CLEAN=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            err "不明なオプション: $1"
            usage
            ;;
    esac
done

if $DO_CLEAN; then
    log "build/ と dist/ を削除"
    rm -rf build/ dist/
    exit 0
fi

check_deps
check_required_files

log "uv sync --extra dev — Python 依存パッケージの同期"
uv sync --extra dev

mkdir -p build dist

if [[ -n "${TARGET_WEIGHT}" ]]; then
    case "${TARGET_WEIGHT}" in
        Regular|Bold) ;;
        *)
            err "--weight には Regular か Bold を指定してください"
            exit 1
            ;;
    esac
    build_weight "${TARGET_WEIGHT}"
else
    for weight in "${WEIGHTS[@]}"; do
        build_weight "${weight}"
    done
fi

log "ビルド完了"
