#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_ROOT="${REPO_ROOT}/../keskos-package-sources/github-repos"
failures=0
warnings=0

pass() {
  printf '[check-branding] PASS: %s\n' "$1"
}

warn_check() {
  printf '[check-branding] WARN: %s\n' "$1"
  warnings=$((warnings + 1))
}

fail_check() {
  printf '[check-branding] FAIL: %s\n' "$1" >&2
  failures=$((failures + 1))
}

require_path() {
  local path="$1"
  if [[ -e "$path" ]]; then
    pass "required path exists: ${path#${REPO_ROOT}/}"
  else
    fail_check "required path is missing: ${path#${REPO_ROOT}/}"
  fi
}

allowed_match_path() {
  local path="$1"

  case "$path" in
    "${REPO_ROOT}/README.md"|\
    "${REPO_ROOT}/CHANGELOG.md"|\
    "${REPO_ROOT}/docs/"*|\
    "${REPO_ROOT}/airootfs/etc/os-release"|\
    "${PACKAGE_ROOT}/keskos-release/PKGBUILD"|\
    "${PACKAGE_ROOT}/keskos-release/README.md")
      return 0
      ;;
  esac

  return 1
}

check_release_metadata_sources() {
  local release_repo="${PACKAGE_ROOT}/keskos-release"

  require_path "${release_repo}/PKGBUILD"
  require_path "${release_repo}/files/usr/lib/keskos/branding.py"
  require_path "${release_repo}/files/usr/lib/keskos/branding.sh"

  if grep -Fq 'branding.json' "${release_repo}/PKGBUILD" && grep -Fq '/etc/keskos-release' "${release_repo}/PKGBUILD"; then
    pass "keskos-release PKGBUILD generates both /etc/keskos-release and branding.json"
  else
    fail_check "keskos-release PKGBUILD no longer generates the central branding files"
  fi
}

check_tooling_hooks() {
  local tools_repo="${PACKAGE_ROOT}/keskos-tools"
  local hook_path="${tools_repo}/files/airootfs/usr/share/libalpm/hooks/keskos-branding-refresh.hook"
  local command_path="${tools_repo}/files/airootfs/usr/lib/kesk/commands/refresh-branding"

  require_path "${hook_path}"
  require_path "${command_path}"

  if grep -Fq 'kesk refresh-branding' "${hook_path}"; then
    pass "branding refresh hook calls kesk refresh-branding"
  else
    fail_check "branding refresh hook does not call kesk refresh-branding"
  fi
}

scan_hardcoded_branding() {
  local -a search_roots=()
  local -a raw_matches=()
  local -a filtered_matches=()
  local line=""
  local path=""

  search_roots+=("${REPO_ROOT}/airootfs" "${REPO_ROOT}/calamares" "${REPO_ROOT}/configs" "${REPO_ROOT}/desktop")

  for candidate in \
    "${PACKAGE_ROOT}/keskos-tools" \
    "${PACKAGE_ROOT}/keskos-settings" \
    "${PACKAGE_ROOT}/keskos-welcome" \
    "${PACKAGE_ROOT}/keskos-calamares-branding" \
    "${PACKAGE_ROOT}/keskos-desktop/packages/keskos-theme" \
    "${PACKAGE_ROOT}/keskos-desktop/packages/keskos-quickshell-hud" \
    "${PACKAGE_ROOT}/keskos-desktop/packages/keskos-browser-startpage" \
    "${PACKAGE_ROOT}/keskos-desktop/packages/keskos-sddm-theme"
  do
    [[ -d "${candidate}" ]] && search_roots+=("${candidate}")
  done

  mapfile -t raw_matches < <(
    rg -n --color never \
      --glob '!**/.git/**' \
      --glob '!**/target/**' \
      --glob '!**/*.pkg.tar.zst' \
      --glob '!**/*.png' \
      --glob '!**/*.jpg' \
      --glob '!**/*.svg' \
      'KeskOS // Layer 4|Layer 4|S\.P\.L\.I\.T\.|KeskOS S\.P\.L\.I\.T\. Edition|K42-OPS TERMINAL' \
      "${search_roots[@]}"
  )

  for line in "${raw_matches[@]}"; do
    path="${line%%:*}"
    if allowed_match_path "${path}"; then
      continue
    fi
    filtered_matches+=("${line}")
  done

  if (( ${#filtered_matches[@]} > 0 )); then
    printf '[check-branding] FAIL: hardcoded branding/version strings remain in runtime or package-source files:\n' >&2
    printf '  %s\n' "${filtered_matches[@]}" >&2
    failures=$((failures + 1))
  else
    pass "no disallowed hardcoded Layer 4 / old edition branding strings were found"
  fi
}

check_runtime_references() {
  local tools_repo="${PACKAGE_ROOT}/keskos-tools"
  local settings_repo="${PACKAGE_ROOT}/keskos-settings"
  local welcome_repo="${PACKAGE_ROOT}/keskos-welcome"

  if rg -n --color never 'load_branding|branding\.py|refresh-branding' \
    "${tools_repo}/files/airootfs/usr/lib/kesk" \
    "${settings_repo}/files/kcm-src" \
    "${welcome_repo}/files" >/dev/null; then
    pass "runtime consumers reference the central branding metadata path"
  else
    fail_check "runtime consumers do not appear to reference the central branding metadata path"
  fi
}

main() {
  check_release_metadata_sources
  check_tooling_hooks
  scan_hardcoded_branding
  check_runtime_references

  printf '[check-branding] Summary: %d failure(s), %d warning(s)\n' "${failures}" "${warnings}"
  (( failures == 0 ))
}

main "$@"
