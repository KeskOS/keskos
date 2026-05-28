#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failures=0
warnings=0

pass() {
  printf '[check-repo-cleanliness] PASS: %s\n' "$1"
}

warn() {
  printf '[check-repo-cleanliness] WARN: %s\n' "$1"
  warnings=$((warnings + 1))
}

fail_check() {
  printf '[check-repo-cleanliness] FAIL: %s\n' "$1" >&2
  failures=$((failures + 1))
}

dir_has_entries() {
  local dir_path="$1"
  find "${dir_path}" -mindepth 1 -maxdepth 1 | read -r _
}

check_required_files() {
  local required_path=""
  local required_paths=(
    "${REPO_ROOT}/build.sh"
    "${REPO_ROOT}/packages.x86_64"
    "${REPO_ROOT}/pacman.conf"
    "${REPO_ROOT}/profiledef.sh"
    "${REPO_ROOT}/README.md"
    "${REPO_ROOT}/config/keskos-required-packages.txt"
    "${REPO_ROOT}/airootfs/etc/pacman.d/keskos.conf"
    "${REPO_ROOT}/docs/branding-strategy.md"
    "${REPO_ROOT}/docs/repo-cleanup-report.md"
    "${REPO_ROOT}/scripts/check-branding.sh"
    "${REPO_ROOT}/scripts/check-keskos-repo-packages.sh"
  )

  for required_path in "${required_paths[@]}"; do
    if [[ -e "${required_path}" ]]; then
      pass "required path exists: ${required_path#${REPO_ROOT}/}"
    else
      fail_check "required path is missing: ${required_path#${REPO_ROOT}/}"
    fi
  done
}

check_packages_seed() {
  local seed_file="${REPO_ROOT}/packages.x86_64"
  local required_package=""
  local forbidden_package=""
  local required_packages=(
    "keskos-release"
    "keskos-branding"
    "keskos-settings"
    "keskos-welcome"
    "keskos-tools"
    "keskos-theme"
    "keskos-browser-startpage"
  )
  local forbidden_packages=(
    "brave-bin"
    "librewolf-bin"
    "zen-browser-bin"
    "keskos-browsers-meta"
  )

  [[ -f "${seed_file}" ]] || {
    fail_check "packages.x86_64 is missing"
    return 0
  }

  for required_package in "${required_packages[@]}"; do
    if grep -Fxq "${required_package}" "${seed_file}"; then
      pass "packages.x86_64 contains ${required_package}"
    else
      fail_check "packages.x86_64 is missing ${required_package}"
    fi
  done

  for forbidden_package in "${forbidden_packages[@]}"; do
    if grep -Fxq "${forbidden_package}" "${seed_file}"; then
      fail_check "packages.x86_64 still contains ${forbidden_package}"
    else
      pass "packages.x86_64 does not contain ${forbidden_package}"
    fi
  done
}

check_duplicate_local_sources() {
  local -a duplicate_dirs=()

  if [[ -d "${REPO_ROOT}/apps/kesk-welcome" ]]; then
    fail_check "duplicate app source still exists: apps/kesk-welcome"
  else
    pass "duplicate app source apps/kesk-welcome is absent"
  fi

  if [[ -d "${REPO_ROOT}/packages" ]]; then
    mapfile -t duplicate_dirs < <(
      find "${REPO_ROOT}/packages" -mindepth 1 -maxdepth 1 -type d -name 'keskos-*' | sort
    )
  fi

  if (( ${#duplicate_dirs[@]} > 0 )); then
    printf '[check-repo-cleanliness] FAIL: duplicate package export dirs remain:\n' >&2
    printf '  %s\n' "${duplicate_dirs[@]#${REPO_ROOT}/}" >&2
    failures=$((failures + 1))
  else
    pass "duplicate packages/keskos-* export dirs are absent"
  fi
}

check_generated_artifacts() {
  local dir_path=""
  local -a stale_entries=()
  local -a stale_dirs=()

  mapfile -t stale_entries < <(
    find "${REPO_ROOT}" -path "${REPO_ROOT}/.git" -prune -o \
      \( -type f \( -name '*.pkg.tar.zst' -o -name '*.pkg.tar.zst.sig' -o -name '*.pkg.tar.xz' -o -name '*.pkg.tar' -o -name '*.iso' -o -name '*.iso.sig' -o -name '*.db' -o -name '*.db.tar.gz' -o -name '*.files' -o -name '*.files.tar.gz' -o -name '*.pyc' \) -print \)
  )
  mapfile -t stale_dirs < <(
    find "${REPO_ROOT}" -path "${REPO_ROOT}/.git" -prune -o \
      \( -type d \( -name pkg -o -name src -o -name target -o -name localrepo -o -name repo-output -o -name __pycache__ -o -name node_modules \) -print \)
  )

  if (( ${#stale_entries[@]} > 0 )); then
    printf '[check-repo-cleanliness] FAIL: generated artifact files remain:\n' >&2
    printf '  %s\n' "${stale_entries[@]#${REPO_ROOT}/}" >&2
    failures=$((failures + 1))
  else
    pass "no generated artifact files were found"
  fi

  if (( ${#stale_dirs[@]} > 0 )); then
    printf '[check-repo-cleanliness] FAIL: generated build/cache directories remain:\n' >&2
    printf '  %s\n' "${stale_dirs[@]#${REPO_ROOT}/}" >&2
    failures=$((failures + 1))
  else
    pass "no generated build/cache directories were found"
  fi

  for dir_path in "${REPO_ROOT}/out" "${REPO_ROOT}/work" "${REPO_ROOT}/cache" "${REPO_ROOT}/localrepo" "${REPO_ROOT}/repo-output" "${REPO_ROOT}/.cache"; do
    if [[ -d "${dir_path}" ]]; then
      if dir_has_entries "${dir_path}"; then
        fail_check "generated output directory is not empty: ${dir_path#${REPO_ROOT}/}"
      else
        warn "generated output directory exists but is empty: ${dir_path#${REPO_ROOT}/}"
      fi
    fi
  done
}

check_build_script() {
  if bash -n "${REPO_ROOT}/build.sh"; then
    pass "build.sh passes bash -n"
  else
    fail_check "build.sh failed bash -n"
  fi

  if grep -Fq 'BUILD_MODE="${KESKOS_BUILD_MODE:-release}"' "${REPO_ROOT}/build.sh"; then
    pass "build.sh defaults to release mode"
  else
    fail_check "build.sh no longer defaults to release mode"
  fi

  if grep -Fq -- '--check' "${REPO_ROOT}/build.sh"; then
    pass "build.sh exposes a check-only path"
  else
    fail_check "build.sh is missing --check support"
  fi

  if command -v shellcheck >/dev/null 2>&1; then
    if shellcheck "${REPO_ROOT}/build.sh"; then
      pass "build.sh passes shellcheck"
    else
      fail_check "build.sh failed shellcheck"
    fi
  else
    warn "shellcheck is not installed; skipped shellcheck build.sh"
  fi
}

check_branding_checks() {
  if bash -n "${REPO_ROOT}/scripts/check-branding.sh"; then
    pass "scripts/check-branding.sh passes bash -n"
  else
    fail_check "scripts/check-branding.sh failed bash -n"
  fi

  if "${REPO_ROOT}/scripts/check-branding.sh"; then
    pass "scripts/check-branding.sh passed"
  else
    fail_check "scripts/check-branding.sh failed"
  fi
}

main() {
  check_required_files
  check_packages_seed
  check_duplicate_local_sources
  check_generated_artifacts
  check_build_script
  check_branding_checks

  printf '[check-repo-cleanliness] Summary: %d failure(s), %d warning(s)\n' "${failures}" "${warnings}"
  (( failures == 0 ))
}

main "$@"
