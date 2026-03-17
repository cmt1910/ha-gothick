#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="${SCRIPT_DIR}/config/config.yaml"
DOCKER_IMAGE="${DOCKER_IMAGE:-ha-gothick-build:latest}"
DOCKER_PLATFORM="${DOCKER_PLATFORM:-linux/amd64}"
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"

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

Environment:
  DOCKER_IMAGE      利用する Docker イメージ名 (デフォルト: ha-gothick-build:latest)
  DOCKER_PLATFORM   Docker プラットフォーム (デフォルト: linux/amd64)
EOF
    exit 0
}

check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        err "docker が見つかりません"
        exit 1
    fi
}

run_in_docker() {
    check_docker

    log "Docker イメージをビルド: ${DOCKER_IMAGE}"
    docker build --platform "${DOCKER_PLATFORM}" -t "${DOCKER_IMAGE}" "${SCRIPT_DIR}"

    log "Docker コンテナ内でビルドを実行"
    docker run --rm \
        --platform "${DOCKER_PLATFORM}" \
        --user "$(id -u):$(id -g)" \
        -e HOME=/tmp/ha-gothick-home \
        -e UV_CACHE_DIR=/work/.uv-cache \
        -e PYTHON_VERSION="${PYTHON_VERSION}" \
        -e HA_GOTHICK_BUILD_IN_CONTAINER=1 \
        -v "${SCRIPT_DIR}:/work" \
        -w /work \
        "${DOCKER_IMAGE}" \
        bash ./build.sh "$@"
}


TARGET_WEIGHT=""
DO_CLEAN=false
ORIGINAL_ARGS=("$@")

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

if [[ "${HA_GOTHICK_BUILD_IN_CONTAINER:-0}" != "1" ]]; then
    if [[ ${#ORIGINAL_ARGS[@]} -gt 0 ]]; then
        run_in_docker "${ORIGINAL_ARGS[@]}"
    else
        run_in_docker
    fi
    exit 0
fi

log "uv sync --extra dev --python ${PYTHON_VERSION} — Python 依存パッケージの同期"
uv sync --extra dev --python "${PYTHON_VERSION}"

BUILD_ARGS=(--config "${CONFIG}")
[[ -n "${TARGET_WEIGHT}" ]] && BUILD_ARGS+=(--weight "${TARGET_WEIGHT}")
uv run python -m font_builder.build "${BUILD_ARGS[@]}"
