#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"

log()  { printf "\033[1;34m[INFO]\033[0m  %s\n" "$*"; }
err()  { printf "\033[1;31m[ERROR]\033[0m %s\n" "$*" >&2; }

require_commands() {
    local missing=()
    local command
    for command in uv curl unzip tar find; do
        command -v "${command}" >/dev/null 2>&1 || missing+=("${command}")
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        err "以下のコマンドが不足しています: ${missing[*]}"
        exit 1
    fi
}

prepare_source_dirs() {
    mkdir -p \
        "${PROJECT_ROOT}/sources/hack" \
        "${PROJECT_ROOT}/sources/bizud" \
        "${PROJECT_ROOT}/sources/nerd"
}

setup_python_deps() {
    log "uv sync --extra dev --python ${PYTHON_VERSION} — Python 依存パッケージの同期"
    (
        cd "${PROJECT_ROOT}"
        uv sync --extra dev --python "${PYTHON_VERSION}"
    )
}

download_hack_fonts() {
    local hack_zip="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/Hack-v3.003-ttf.zip"
    local hack_dir="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/hack-fonts"

    log "Hack フォントを取得"
    curl -fL https://github.com/source-foundry/Hack/releases/download/v3.003/Hack-v3.003-ttf.zip -o "${hack_zip}"
    rm -rf "${hack_dir}"
    unzip -q "${hack_zip}" -d "${hack_dir}"
    cp "$(find "${hack_dir}" -type f -name 'Hack-Regular.ttf' | head -n 1)" \
        "${PROJECT_ROOT}/sources/hack/Hack-Regular.ttf"
    cp "$(find "${hack_dir}" -type f -name 'Hack-Bold.ttf' | head -n 1)" \
        "${PROJECT_ROOT}/sources/hack/Hack-Bold.ttf"
}

download_bizud_fonts() {
    local bizud_zip="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/morisawa-biz-ud-gothic-main.zip"
    local bizud_dir="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/bizud-fonts"

    log "BIZ UDゴシックを取得"
    curl -fL \
        https://codeload.github.com/googlefonts/morisawa-biz-ud-gothic/zip/refs/heads/main \
        -o "${bizud_zip}"
    rm -rf "${bizud_dir}"
    unzip -q "${bizud_zip}" -d "${bizud_dir}"
    cp "$(find "${bizud_dir}" -type f -path '*/fonts/ttf/BIZUDGothic-Regular.ttf' | head -n 1)" \
        "${PROJECT_ROOT}/sources/bizud/BIZUDGothic-Regular.ttf"
    cp "$(find "${bizud_dir}" -type f -path '*/fonts/ttf/BIZUDGothic-Bold.ttf' | head -n 1)" \
        "${PROJECT_ROOT}/sources/bizud/BIZUDGothic-Bold.ttf"
}

download_nerd_font() {
    local nerd_archive="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/NerdFontsSymbolsOnly.tar.xz"
    local nerd_dir="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/nerd-fonts"

    log "Nerd Fonts Symbols Only を取得"
    curl -fL \
        https://github.com/ryanoasis/nerd-fonts/releases/latest/download/NerdFontsSymbolsOnly.tar.xz \
        -o "${nerd_archive}"
    rm -rf "${nerd_dir}"
    mkdir -p "${nerd_dir}"
    tar -xJf "${nerd_archive}" -C "${nerd_dir}"
    cp "${nerd_dir}/SymbolsNerdFont-Regular.ttf" \
        "${PROJECT_ROOT}/sources/nerd/SymbolsNerdFont-Regular.ttf"
}

main() {
    require_commands
    prepare_source_dirs
    setup_python_deps
    download_hack_fonts
    download_bizud_fonts
    download_nerd_font
    log "ビルド環境の準備完了"
}

main "$@"
