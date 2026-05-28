#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf '[build-keskos-release] error: %s\n' "$1" >&2
  exit 1
}

log() {
  printf '[build-keskos-release] %s\n' "$1" >&2
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_DIR="${KESKOS_RELEASE_REPO_DIR:-}"

if [[ -z "${PACKAGE_DIR}" ]]; then
  for candidate in \
    "${REPO_ROOT}/../keskos-package-sources/github-repos/keskos-release" \
    "${REPO_ROOT}/../keskos-release"
  do
    if [[ -f "${candidate}/PKGBUILD" ]]; then
      PACKAGE_DIR="${candidate}"
      break
    fi
  done
fi

[[ -n "${PACKAGE_DIR}" ]] || fail "Could not locate the standalone keskos-release package repo. Set KESKOS_RELEASE_REPO_DIR=/path/to/keskos-release."
[[ -f "${PACKAGE_DIR}/PKGBUILD" ]] || fail "PKGBUILD not found at ${PACKAGE_DIR}/PKGBUILD"
require_command makepkg

mapfile -t package_paths < <(
  cd "${PACKAGE_DIR}"
  PKGDEST="${PACKAGE_DIR}" makepkg --packagelist
)

PACKAGE_PATH="${package_paths[0]:-}"

[[ -n "${PACKAGE_PATH}" ]] || fail "Unable to resolve the output package path from makepkg."

log "Building keskos-release in ${PACKAGE_DIR}"
(
  cd "${PACKAGE_DIR}"
  PKGDEST="${PACKAGE_DIR}" makepkg --syncdeps --needed --noconfirm --cleanbuild --clean >&2
)

printf '%s\n' "${PACKAGE_PATH}"
