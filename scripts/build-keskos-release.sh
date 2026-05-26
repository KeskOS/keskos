#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf '[build-keskos-release] error: %s\n' "$1" >&2
  exit 1
}

log() {
  printf '[build-keskos-release] %s\n' "$1"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_DIR="${REPO_ROOT}/packages/keskos-release"

[[ -f "${PACKAGE_DIR}/PKGBUILD" ]] || fail "PKGBUILD not found at ${PACKAGE_DIR}/PKGBUILD"
require_command makepkg

PACKAGE_PATH="$(
  cd "${PACKAGE_DIR}"
  PKGDEST="${PACKAGE_DIR}" makepkg --packagelist | head -n 1
)"

[[ -n "${PACKAGE_PATH}" ]] || fail "Unable to resolve the output package path from makepkg."

log "Building keskos-release in ${PACKAGE_DIR}"
(
  cd "${PACKAGE_DIR}"
  PKGDEST="${PACKAGE_DIR}" makepkg --syncdeps --needed --noconfirm --cleanbuild --clean
)

printf '%s\n' "${PACKAGE_PATH}"
