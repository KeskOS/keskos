#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf '[export-package-sources] error: %s\n' "$1" >&2
  exit 1
}

log() {
  printf '[export-package-sources] %s\n' "$1"
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
default_output="${repo_root}/../keskos-package-sources"
output_root="${1:-${default_output}}"
external_desktop_packages=(
  keskos-branding
  keskos-theme
  keskos-sddm-theme
  keskos-plymouth
  keskos-plasma-layout
  keskos-quickshell-hud
  keskos-kickoff
  keskos-workspace-switcher
  keskos-browser-startpage
  keskos-desktop-meta
)

case "${output_root}" in
  "${repo_root}"|"/"|"" )
    fail "Refusing to export into an unsafe destination: ${output_root}"
    ;;
esac

copy_path() {
  local relative_path="$1"
  local source_path="${repo_root}/${relative_path}"
  local parent_dir

  [[ -e "${source_path}" ]] || return 0

  parent_dir="$(dirname "${output_root}/${relative_path}")"
  mkdir -p "${parent_dir}"
  cp -a "${source_path}" "${parent_dir}/"
}

prune_generated_content() {
  rm -rf \
    "${output_root}/packages/kesk-settings-kcms/pkg" \
    "${output_root}/packages/kesk-settings-kcms/src" \
    "${output_root}/packages/kesk-welcome/pkg" \
    "${output_root}/packages/kesk-welcome/src"

  find "${output_root}" -type d -name .git -prune -exec rm -rf {} +
  find "${output_root}" -type d -name __pycache__ -prune -exec rm -rf {} +
  find "${output_root}" -type f \( -name '*.pkg.tar.zst' -o -name '*.pkg.tar.xz' -o -name '*.pyc' -o -name '*.pyo' \) -delete
}

prune_externally_managed_packages() {
  local package_name=""

  for package_name in "${external_desktop_packages[@]}"; do
    rm -rf "${output_root}/packages/${package_name}"
  done
}

write_readme() {
  cat >"${output_root}/README.md" <<EOF
# KeskOS Package Sources Export

This folder is a clean export of the local KeskOS package inputs.

Important:

- This export only contains ISO-local sources and compatibility package helpers that still live in the ISO repo.
- The standalone \`keskos-*\` package source of truth now lives in dedicated package repositories under the \`KeskOS\` GitHub organization.
- The \`url=\` field inside a PKGBUILD is package metadata only.
- Desktop shell and branding package sources are now managed separately in:
  - https://github.com/KeskOS/keskos-desktop
  - https://github.com/KeskOS/keskos-desktop-meta

Exported from:

- ${repo_root}

Included roots:

- airootfs/
- assets/
- browser-home/
- calamares/
- configs/
- desktop/
- docs/keskos-packages.md
- packages/
- scripts/
- README.md

Generated files like built package archives, temporary build directories, and Python cache files were removed from this export.
Externally managed desktop package repos were also pruned from \`packages/\`.
EOF
}

write_manifest() {
  cat >"${output_root}/PACKAGE-SOURCE-MAP.txt" <<'EOF'
The package sources in this export map broadly like this:

- Core package definitions: packages/
- Build helpers and validation: scripts/
- KeskOS tools/runtime scripts: airootfs/
- Browser start page: browser-home/
- Branding assets and wallpapers: assets/
- Desktop themes, widgets, launcher, look-and-feel, Quickshell, SDDM: configs/
- Calamares branding and module configs: calamares/
- Desktop launchers: desktop/
- Package documentation: docs/keskos-packages.md
- Desktop visual package sources: managed in KeskOS/keskos-desktop and not exported from this ISO repo snapshot
EOF
}

log "Preparing export folder: ${output_root}"
rm -rf "${output_root}"
mkdir -p "${output_root}"

copy_path "README.md"
copy_path "airootfs"
copy_path "assets"
copy_path "browser-home"
copy_path "calamares"
copy_path "configs"
copy_path "desktop"
copy_path "docs/keskos-packages.md"
copy_path "packages"
copy_path "scripts"

prune_generated_content
prune_externally_managed_packages
write_readme
write_manifest

log "Export complete"
printf '%s\n' "${output_root}"
