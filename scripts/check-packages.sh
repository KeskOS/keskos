#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf '[check-packages] %s\n' "$1" >&2
}

log() {
  printf '[check-packages] %s\n' "$1"
}

metadata_lines() {
  local pkgbuild="$1"

  bash -c '
    set -e
    source "$1"

    first_value() {
      local name="$1"
      local declaration=""

      if ! declaration="$(declare -p "$name" 2>/dev/null)"; then
        printf "\n"
        return 0
      fi

      if [[ "$declaration" == declare\ -a* || "$declaration" == declare\ -A* ]]; then
        eval "printf \"%s\n\" \"\${${name}[0]-}\""
      else
        eval "printf \"%s\n\" \"\${${name}-}\""
      fi
    }

    joined_values() {
      local name="$1"
      if declare -p "$name" >/dev/null 2>&1; then
        eval "printf \"%s\n\" \"\${${name}[*]-}\""
      else
        printf "\n"
      fi
    }

    first_value pkgname
    first_value pkgver
    first_value pkgrel
    first_value pkgdesc
    joined_values arch
  ' bash "${pkgbuild}"
}

is_meta_package() {
  [[ "$1" == *-meta || "$1" == "kesk-settings-kcms" || "$1" == "kesk-welcome" ]]
}

package_body() {
  sed -n '/^package() {/,/^}/p' "$1"
}

install_logic_files() {
  local package_dir="$1"
  local file

  printf '%s\n' "${package_dir}/PKGBUILD"

  while IFS= read -r -d '' file; do
    printf '%s\n' "${file}"
  done < <(find "${package_dir}" -maxdepth 1 -type f -name '*.install' -print0 | sort -z)
}

main() {
  local repo_root packages_root pkgbuild package_dir package_name folder_name
  local pkgname pkgver pkgrel pkgdesc arch_value
  local failures=0
  local warnings=0
  local total=0
  local -a metadata=()
  local -a install_logic=()

  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  packages_root="${repo_root}/packages"

  while IFS= read -r pkgbuild; do
    total=$((total + 1))
    package_dir="$(dirname "${pkgbuild}")"
    folder_name="$(basename "${package_dir}")"
    mapfile -t metadata < <(metadata_lines "${pkgbuild}")
    mapfile -t install_logic < <(install_logic_files "${package_dir}")
    pkgname="${metadata[0]:-}"
    pkgver="${metadata[1]:-}"
    pkgrel="${metadata[2]:-}"
    pkgdesc="${metadata[3]:-}"
    arch_value="${metadata[4]:-}"

    if [[ -z "${pkgname}" ]]; then
      fail "${folder_name}: pkgname is missing"
      failures=$((failures + 1))
    elif [[ "${pkgname}" != "${folder_name}" ]]; then
      fail "${folder_name}: folder name does not match pkgname (${pkgname})"
      failures=$((failures + 1))
    fi

    if [[ -z "${pkgver}" ]]; then
      fail "${folder_name}: pkgver is missing"
      failures=$((failures + 1))
    fi

    if [[ -z "${pkgrel}" ]]; then
      fail "${folder_name}: pkgrel is missing"
      failures=$((failures + 1))
    fi

    if [[ -z "${pkgdesc}" ]]; then
      fail "${folder_name}: pkgdesc is missing"
      failures=$((failures + 1))
    fi

    if [[ -z "${arch_value}" ]]; then
      fail "${folder_name}: arch is missing"
      failures=$((failures + 1))
    fi

    if ! grep -Eq '^package\(\)[[:space:]]*\{' "${pkgbuild}"; then
      fail "${folder_name}: package() is missing"
      failures=$((failures + 1))
    fi

    if is_meta_package "${folder_name}"; then
      if package_body "${pkgbuild}" | rg -n '\b(install|cp|mkdir|ln|rsync|cat[[:space:]]*>)\b' >/dev/null; then
        fail "${folder_name}: meta or compatibility package should not install files"
        failures=$((failures + 1))
      fi
    fi

    if rg -n 'BEGIN (OPENSSH|RSA|EC|DSA|PGP) PRIVATE KEY|-----BEGIN .*PRIVATE KEY-----' "${package_dir}" >/dev/null; then
      fail "${folder_name}: possible private key material detected"
      failures=$((failures + 1))
    fi

    if rg -n '(rm -rf /|useradd|groupadd|systemctl enable|pacman -S|curl .*\| *sh)' "${install_logic[@]}" >/dev/null; then
      fail "${folder_name}: dangerous install or script behavior detected"
      failures=$((failures + 1))
    fi

    if rg -n '(/home/|~/.|/root/)' "${install_logic[@]}" >/dev/null; then
      fail "${folder_name}: package recipe appears to write to a user home directory"
      failures=$((failures + 1))
    fi

    if [[ "${arch_value}" == *"x86_64"* && "${folder_name}" != "keskos-settings" && "${folder_name}" != "keskos-welcome" ]]; then
      log "warning: ${folder_name} is architecture-limited; confirm that this is intentional"
      warnings=$((warnings + 1))
    fi
  done < <(find "${packages_root}" -mindepth 2 -maxdepth 2 -name PKGBUILD | sort)

  log "checked ${total} package definitions"
  log "warnings: ${warnings}"

  if (( failures > 0 )); then
    fail "failures: ${failures}"
    exit 1
  fi

  log "all package definitions passed the local validation checks"
}

main "$@"
