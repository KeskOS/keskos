#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf '[build-all-packages] error: %s\n' "$1" >&2
  exit 1
}

log() {
  printf '[build-all-packages] %s\n' "$1"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

is_externally_managed_package() {
  case "$1" in
    keskos-branding|keskos-theme|keskos-sddm-theme|keskos-plymouth|keskos-plasma-layout|keskos-quickshell-hud|keskos-kickoff|keskos-workspace-switcher|keskos-browser-startpage|keskos-desktop-meta)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

package_build_args() {
  local package_name="$1"
  local -a args=(--syncdeps --noconfirm --cleanbuild --clean)

  case "${package_name}" in
    *-meta|kesk-settings-kcms|kesk-welcome)
      args+=(--nodeps)
      ;;
  esac

  printf '%s\n' "${args[@]}"
}

ordered_package_dirs() {
  local packages_root="$1"
  local -a preferred=(
    keskos-release
    keskos-keyring
    keskos-mirrorlist
    keskos-branding
    keskos-theme
    keskos-tools
    keskos-settings
    keskos-welcome
    keskos-kickoff
    keskos-workspace-switcher
    keskos-quickshell-hud
    keskos-plasma-layout
    keskos-browser-startpage
    keskos-sddm-theme
    keskos-plymouth
    keskos-calamares-branding
    keskos-installer-debug-log
    keskos-core-meta
    keskos-desktop-meta
    keskos-browsers-meta
    keskos-gaming-meta
    keskos-social-meta
    keskos-dev-meta
    keskos-creator-meta
    keskos-office-meta
    keskos-system-tools-meta
    keskos-hardware-meta
    keskos-nvidia-meta
    keskos-all-meta
    kesk-settings-kcms
    kesk-welcome
  )
  local -A seen=()
  local name=""

  for name in "${preferred[@]}"; do
    if [[ -f "${packages_root}/${name}/PKGBUILD" ]]; then
      if is_externally_managed_package "${name}"; then
        continue
      fi
      printf '%s\n' "${packages_root}/${name}"
      seen["${name}"]=1
    fi
  done

  while IFS= read -r pkgbuild; do
    name="$(basename "$(dirname "${pkgbuild}")")"
    if [[ -n "${seen[${name}]:-}" ]]; then
      continue
    fi
    if is_externally_managed_package "${name}"; then
      continue
    fi
    printf '%s\n' "$(dirname "${pkgbuild}")"
  done < <(find "${packages_root}" -mindepth 2 -maxdepth 2 -name PKGBUILD | sort)
}

main() {
  local repo_root packages_root output_root package_dir package_name
  local -a built_files=()
  local -a makepkg_args=()
  local -a packagelist_args=()
  local build_count=0

  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  packages_root="${repo_root}/packages"
  output_root="${KESKOS_PACKAGE_OUTPUT_DIR:-${repo_root}/out/packages}"

  [[ -d "${packages_root}" ]] || fail "Packages root not found: ${packages_root}"

  require_command makepkg
  mkdir -p "${output_root}"

  while IFS= read -r package_dir; do
    package_name="$(basename "${package_dir}")"
    mapfile -t makepkg_args < <(package_build_args "${package_name}")

    log "Building ${package_name}"
    (
      cd "${package_dir}"
      PKGDEST="${output_root}" makepkg "${makepkg_args[@]}"
    ) || fail "Build failed for ${package_name}"

    packagelist_args=(--packagelist)
    if [[ "${package_name}" == *-meta || "${package_name}" == "kesk-settings-kcms" || "${package_name}" == "kesk-welcome" ]]; then
      packagelist_args+=(--nodeps)
    fi

    while IFS= read -r built_file; do
      [[ -n "${built_file}" ]] || continue
      built_files+=("${built_file}")
    done < <(
      cd "${package_dir}"
      PKGDEST="${output_root}" makepkg "${packagelist_args[@]}"
    )

    build_count=$((build_count + 1))
  done < <(ordered_package_dirs "${packages_root}")

  log "Built ${build_count} package directories"
  log "Output directory: ${output_root}"

  if (( ${#built_files[@]} > 0 )); then
    printf '%s\n' "${built_files[@]}" | sort -u
  fi
}

main "$@"
