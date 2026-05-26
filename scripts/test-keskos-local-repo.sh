#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf '[test-keskos-local-repo] error: %s\n' "$1" >&2
  exit 1
}

log() {
  printf '[test-keskos-local-repo] %s\n' "$1"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

usage() {
  cat <<'EOF'
Usage: ./scripts/test-keskos-local-repo.sh [--install]

Default behavior:
- builds `keskos-release`
- creates a temporary local pacman repository under /tmp/keskos-local-repo
- prints a file:// repo snippet for manual testing

Optional:
- `--install` refreshes pacman with a temporary config and installs `keskos-release`
EOF
}

INSTALL_PACKAGE=0
if (( $# > 1 )); then
  usage
  exit 1
fi

if (( $# == 1 )); then
  case "$1" in
    --install)
      INSTALL_PACKAGE=1
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage
      exit 1
      ;;
  esac
fi

require_command repo-add
require_command ln
require_command mktemp

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_HELPER="${REPO_ROOT}/scripts/build-keskos-release.sh"
[[ -x "${BUILD_HELPER}" ]] || fail "Build helper is missing or not executable: ${BUILD_HELPER}"

PACKAGE_PATH="$("${BUILD_HELPER}")"
[[ -f "${PACKAGE_PATH}" ]] || fail "Built package not found: ${PACKAGE_PATH}"

ARCHITECTURE="$(uname -m)"
LOCAL_REPO_ROOT="${KESKOS_LOCAL_REPO_ROOT:-/tmp/keskos-local-repo}"
REPO_DIR="${LOCAL_REPO_ROOT}/keskos/os/${ARCHITECTURE}"

case "${REPO_DIR}" in
  /tmp/keskos-local-repo/*|${LOCAL_REPO_ROOT}/*)
    ;;
  *)
    fail "Refusing to use an unexpected repo directory: ${REPO_DIR}"
    ;;
esac

rm -rf "${REPO_DIR}"
mkdir -p "${REPO_DIR}"
cp -f "${PACKAGE_PATH}" "${REPO_DIR}/"

(
  cd "${REPO_DIR}"
  repo-add keskos.db.tar.gz ./*.pkg.tar.zst
  ln -sf keskos.db.tar.gz keskos.db
  ln -sf keskos.files.tar.gz keskos.files
)

cat <<EOF
[keskos-local]
SigLevel = Optional TrustAll
Server = file://${LOCAL_REPO_ROOT}/\$repo/os/\$arch
EOF

if (( INSTALL_PACKAGE == 0 )); then
  log "Local repo prepared at ${REPO_DIR}"
  log "Add the printed snippet to a temporary pacman.conf in a test VM when you are ready."
  exit 0
fi

require_command pacman
require_command sudo

TEMP_CONF="$(mktemp)"
trap 'rm -f "${TEMP_CONF}"' EXIT
cp /etc/pacman.conf "${TEMP_CONF}"

if ! grep -q '^\[keskos-local\]$' "${TEMP_CONF}"; then
  cat >>"${TEMP_CONF}" <<EOF

[keskos-local]
SigLevel = Optional TrustAll
Server = file://${LOCAL_REPO_ROOT}/\$repo/os/\$arch
EOF
fi

log "Refreshing pacman databases with a temporary config"
sudo pacman -Syy --config "${TEMP_CONF}"
log "Installing keskos-release from the local test repo"
sudo pacman -S --needed --config "${TEMP_CONF}" keskos-release
