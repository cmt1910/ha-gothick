#!/usr/bin/env bash
set -euo pipefail

DIST_DIR="${1:-dist}"

log()  { printf "\033[1;34m[INFO]\033[0m  %s\n" "$*"; }
warn() { printf "\033[1;33m[WARN]\033[0m  %s\n" "$*"; }
err()  { printf "\033[1;31m[FAIL]\033[0m %s\n" "$*" >&2; }

if ! command -v uv >/dev/null 2>&1; then
    err "uv が見つかりません"
    exit 1
fi

if [[ ! -d "${DIST_DIR}" ]]; then
    err "dist ディレクトリが見つかりません: ${DIST_DIR}"
    exit 1
fi

shopt -s nullglob
fonts=("${DIST_DIR}"/HA-Gothick-*.ttf)
shopt -u nullglob

if [[ ${#fonts[@]} -eq 0 ]]; then
    err "検証対象のフォントが見つかりません: ${DIST_DIR}/HA-Gothick-*.ttf"
    exit 1
fi

EXIT_CODE=0

for ttf in "${fonts[@]}"; do
    log "検証中: $(basename "${ttf}")"
    if ! uv run python src/font_builder/validate.py "${ttf}"; then
        EXIT_CODE=1
    fi
done

if command -v fontbakery >/dev/null 2>&1 || uv run fontbakery --version >/dev/null 2>&1; then
    log "fontbakery check-universal を実行"
    uv run fontbakery check-universal "${fonts[@]}" -l WARN || warn "fontbakery が警告または失敗を返しました"
else
    log "fontbakery は未導入のためスキップ (uv sync --extra dev で有効化)"
fi

log "TTX テーブルダンプを build/ttx/ に出力"
mkdir -p build/ttx
for ttf in "${fonts[@]}"; do
    base="$(basename "${ttf}" .ttf)"
    uv run ttx -l "${ttf}" > "build/ttx/${base}_tables.txt" 2>&1 || EXIT_CODE=1
    uv run ttx -t OS/2 -o "build/ttx/${base}_OS2.ttx" "${ttf}" >/dev/null 2>&1 || EXIT_CODE=1
done

exit "${EXIT_CODE}"
