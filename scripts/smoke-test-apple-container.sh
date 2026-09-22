#!/bin/sh

set -u

SCRIPT_DIR=$(
    unset CDPATH
    cd -- "$(dirname -- "$0")" || exit
    pwd
)
LAUNCHER=${APPLE_CONTAINER_LAUNCHER:-"$SCRIPT_DIR/apple-container.sh"}
CONTAINER_CLI=${CONTAINER_CLI:-container}
CONTAINER_NAME=${APPLE_CONTAINER_NAME:-tix-apple-smoke-$$}
IMAGE_NAME=${APPLE_CONTAINER_IMAGE:-tix:apple-smoke}
HEALTH_URL=http://127.0.0.1:8000/health
DASHBOARD_URL=http://127.0.0.1:8000/
HEALTH_TIMEOUT_SECONDS=${APPLE_CONTAINER_HEALTH_TIMEOUT_SECONDS:-60}
HEALTH_INTERVAL_SECONDS=${APPLE_CONTAINER_HEALTH_INTERVAL_SECONDS:-2}
DATA_DIR=
container_started=0

fail() {
    printf 'ERROR [%s]: %s\n' "$1" "$2" >&2
    exit 1
}

case "$HEALTH_TIMEOUT_SECONDS" in
    ''|*[!0-9]*) fail health "APPLE_CONTAINER_HEALTH_TIMEOUT_SECONDS must be a positive integer" ;;
esac
case "$HEALTH_INTERVAL_SECONDS" in
    ''|*[!0-9]*) fail health "APPLE_CONTAINER_HEALTH_INTERVAL_SECONDS must be a positive integer" ;;
esac
if [ "$HEALTH_TIMEOUT_SECONDS" -lt 1 ]; then
    fail health "APPLE_CONTAINER_HEALTH_TIMEOUT_SECONDS must be greater than zero"
fi
if [ "$HEALTH_INTERVAL_SECONDS" -lt 1 ]; then
    fail health "APPLE_CONTAINER_HEALTH_INTERVAL_SECONDS must be greater than zero"
fi

cleanup() {
    original_status=$?
    cleanup_failed=0

    if [ "$container_started" -eq 1 ]; then
        if ! CONTAINER_CLI="$CONTAINER_CLI" \
            APPLE_CONTAINER_NAME="$CONTAINER_NAME" \
            APPLE_CONTAINER_IMAGE="$IMAGE_NAME" \
            "$LAUNCHER" cleanup; then
            printf '%s\n' "ERROR [cleanup]: failed to remove test container $CONTAINER_NAME" >&2
            cleanup_failed=1
        fi
    fi

    if [ -n "$DATA_DIR" ] && [ -d "$DATA_DIR" ]; then
        if ! rm -rf "$DATA_DIR"; then
            printf '%s\n' "ERROR [cleanup]: failed to remove temporary data directory $DATA_DIR" >&2
            cleanup_failed=1
        fi
    fi

    if [ "$cleanup_failed" -ne 0 ] && [ "$original_status" -eq 0 ]; then
        original_status=1
    fi
    exit "$original_status"
}

trap 'exit 130' INT TERM
trap cleanup EXIT

if ! DATA_DIR=$(mktemp -d "${TMPDIR:-/tmp}/tix-apple-smoke.XXXXXX"); then
    fail startup "failed to create isolated temporary data directory"
fi

if ! CONTAINER_CLI="$CONTAINER_CLI" \
    APPLE_CONTAINER_IMAGE="$IMAGE_NAME" \
    "$LAUNCHER" build; then
    fail build "Apple container image build failed"
fi

container_started=1
if ! CONTAINER_CLI="$CONTAINER_CLI" \
    APPLE_CONTAINER_NAME="$CONTAINER_NAME" \
    APPLE_CONTAINER_IMAGE="$IMAGE_NAME" \
    APPLE_CONTAINER_DATA_DIR="$DATA_DIR" \
    "$LAUNCHER" start; then
    fail startup "Apple container startup failed"
fi

health_deadline=$(( $(date +%s) + HEALTH_TIMEOUT_SECONDS ))
health_status=000
while :; do
    health_remaining=$(( health_deadline - $(date +%s) ))
    if [ "$health_remaining" -le 0 ]; then
        fail health "${HEALTH_URL} did not return a 2xx response within ${HEALTH_TIMEOUT_SECONDS}s (last HTTP status: ${health_status})"
    fi
    health_status=$(curl --silent --show-error --output /dev/null \
        --write-out '%{http_code}' \
        --max-time "$health_remaining" "$HEALTH_URL" 2>/dev/null) || health_status=000
    case "$health_status" in
        2??)
            break
            ;;
    esac
    health_remaining=$(( health_deadline - $(date +%s) ))
    if [ "$health_remaining" -le 0 ]; then
        fail health "${HEALTH_URL} did not return a 2xx response within ${HEALTH_TIMEOUT_SECONDS}s (last HTTP status: ${health_status})"
    fi
    sleep_seconds=$HEALTH_INTERVAL_SECONDS
    if [ "$sleep_seconds" -gt "$health_remaining" ]; then
        sleep_seconds=$health_remaining
    fi
    sleep "$sleep_seconds"
done

dashboard_status=$(curl --silent --show-error --output /dev/null \
    --write-out '%{http_code}' --max-time "$HEALTH_TIMEOUT_SECONDS" "$DASHBOARD_URL" 2>/dev/null) ||
    dashboard_status=000
case "$dashboard_status" in
    2??)
        ;;
    *)
        fail dashboard "dashboard request failed: ${DASHBOARD_URL} (HTTP status: ${dashboard_status})"
        ;;
esac

printf '%s\n' "Apple container smoke test passed"

