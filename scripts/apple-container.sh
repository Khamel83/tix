#!/bin/sh

set -u

SCRIPT_DIR=$(
    unset CDPATH
    cd -- "$(dirname -- "$0")" || exit
    pwd
)
REPO_ROOT=$(
    cd -- "$SCRIPT_DIR/.." || exit
    pwd
)
CONTAINER_CLI=${CONTAINER_CLI:-container}
IMAGE_NAME=${APPLE_CONTAINER_IMAGE:-tix:apple-local}
CONTAINER_NAME=${APPLE_CONTAINER_NAME:-tix-apple-local}

usage() {
    printf '%s\n' "Usage: $0 {build|start|cleanup}" >&2
    exit 2
}

ensure_system() {
    if ! "$CONTAINER_CLI" system start >/dev/null 2>&1; then
        printf '%s\n' "ERROR [startup]: failed to start the Apple container system" >&2
        return 1
    fi
}

build_image() {
    if ! ensure_system; then
        return 1
    fi
    if ! "$CONTAINER_CLI" build --tag "$IMAGE_NAME" "$REPO_ROOT"; then
        printf '%s\n' "ERROR [build]: failed to build image $IMAGE_NAME" >&2
        return 1
    fi
}

start_container() {
    data_dir=${APPLE_CONTAINER_DATA_DIR:-}
    if [ -z "$data_dir" ]; then
        printf '%s\n' "ERROR [startup]: APPLE_CONTAINER_DATA_DIR must name the host data directory" >&2
        return 1
    fi
    if [ ! -d "$data_dir" ]; then
        printf '%s\n' "ERROR [startup]: data directory does not exist: $data_dir" >&2
        return 1
    fi
    if ! "$CONTAINER_CLI" run \
        --detach \
        --name "$CONTAINER_NAME" \
        --publish 127.0.0.1:8000:8000 \
        --volume "$data_dir:/data" \
        "$IMAGE_NAME"; then
        printf '%s\n' "ERROR [startup]: failed to start container $CONTAINER_NAME" >&2
        return 1
    fi
}

cleanup_container() {
    if ! "$CONTAINER_CLI" rm --force "$CONTAINER_NAME" >/dev/null 2>&1; then
        printf '%s\n' "ERROR [cleanup]: failed to remove container $CONTAINER_NAME" >&2
        return 1
    fi
}

command=${1:-}
case "$command" in
    build)
        [ "$#" -eq 1 ] || usage
        build_image
        ;;
    start)
        [ "$#" -eq 1 ] || usage
        start_container
        ;;
    cleanup)
        [ "$#" -eq 1 ] || usage
        cleanup_container
        ;;
    *)
        usage
        ;;
esac
