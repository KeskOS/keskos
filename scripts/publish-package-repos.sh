#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[publish-package-repos] %s\n' "$*" >&2
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

usage() {
  cat <<'EOF'
Usage: publish-package-repos.sh [--org ORG] [--stage-root PATH] [--visibility public|private] [--no-push]

Stages each package under packages/<pkgname>/ as its own standalone git repository,
creates or updates matching GitHub repos, and writes a manifest of the resulting URLs.
EOF
}

org="KeskOS"
visibility="public"
push_changes=1
stage_root=""

while (($#)); do
  case "$1" in
    --org)
      org="${2:?missing value for --org}"
      shift 2
      ;;
    --stage-root)
      stage_root="${2:?missing value for --stage-root}"
      shift 2
      ;;
    --visibility)
      visibility="${2:?missing value for --visibility}"
      shift 2
      ;;
    --no-push)
      push_changes=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "${visibility}" != "public" && "${visibility}" != "private" ]]; then
  printf 'Invalid visibility: %s\n' "${visibility}" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
packages_root="${repo_root}/packages"
export_root="${repo_root}/../keskos-package-sources"

if [[ -z "${stage_root}" ]]; then
  stage_root="${export_root}/github-repos"
fi

manifest_md="${export_root}/GITHUB-REPOS.md"
manifest_txt="${export_root}/GITHUB-REPOS.txt"

mkdir -p "${stage_root}"
mkdir -p "${export_root}"

if ! command -v gh >/dev/null 2>&1; then
  printf 'gh is required but not installed.\n' >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  printf 'gh is installed but not authenticated.\n' >&2
  exit 1
fi

trim_generated_files() {
  local repo_dir="$1"

  rm -rf \
    "${repo_dir}/pkg" \
    "${repo_dir}/src" \
    "${repo_dir}/target" \
    "${repo_dir}/.github" \
    "${repo_dir}/.git"

  find "${repo_dir}" -mindepth 1 \
    \( -name '.DS_Store' \
    -o -name '*.pkg.tar.*' \
    -o -name '*.pkg.tar' \
    -o -name '*.sig' \
    -o -name '*.log' \
    -o -name '.makepkg' \
    -o -name '__pycache__' \) \
    -exec rm -rf {} +
}

clear_stage_dir() {
  local repo_dir="$1"
  mkdir -p "${repo_dir}"
  find "${repo_dir}" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
}

pkg_field() {
  local pkgbuild="$1"
  local field="$2"

  bash -c '
    set -e
    source "$1"
    name="$2"
    declaration=""
    if ! declaration="$(declare -p "$name" 2>/dev/null)"; then
      exit 0
    fi
    if [[ "$declaration" == declare\ -a* || "$declaration" == declare\ -A* ]]; then
      eval "printf \"%s\n\" \"\${${name}[0]-}\""
    else
      eval "printf \"%s\n\" \"\${${name}-}\""
    fi
  ' bash "${pkgbuild}" "${field}"
}

pkg_arches() {
  local pkgbuild="$1"

  bash -c '
    set -e
    source "$1"
    if declare -p arch >/dev/null 2>&1; then
      printf "%s\n" "${arch[*]}"
    fi
  ' bash "${pkgbuild}"
}

write_readme() {
  local repo_dir="$1"
  local pkgname="$2"
  local pkgdesc="$3"
  local pkgver="$4"
  local arch_list="$5"

  cat >"${repo_dir}/README.md" <<EOF
# ${pkgname}

${pkgdesc}

This repository contains the standalone Arch package source for \`${pkgname}\`.

## Contents

- \`PKGBUILD\`
- \`files/\` for packaged assets, scripts, themes, or source snapshots where needed

## Build

\`\`\`bash
makepkg -s --noconfirm
\`\`\`

## Package Metadata

- Version: \`${pkgver}\`
- Architectures: \`${arch_list:-unknown}\`

This repo is intended to be consumed by the KeskOS package build server and can also be built locally with standard Arch tooling.
EOF
}

write_gitignore() {
  local repo_dir="$1"

  cat >"${repo_dir}/.gitignore" <<'EOF'
pkg/
src/
target/
*.pkg.tar
*.pkg.tar.*
*.sig
EOF
}

publish_package_repo() {
  local package_dir="$1"
  local pkgname pkgdesc pkgver arch_list repo_dir remote_url
  local commit_message

  pkgname="$(basename "${package_dir}")"
  repo_dir="${stage_root}/${pkgname}"
  remote_url="https://github.com/${org}/${pkgname}.git"

  clear_stage_dir "${repo_dir}"
  cp -a "${package_dir}/." "${repo_dir}/"
  trim_generated_files "${repo_dir}"

  pkgdesc="$(pkg_field "${repo_dir}/PKGBUILD" pkgdesc)"
  pkgver="$(pkg_field "${repo_dir}/PKGBUILD" pkgver)"
  arch_list="$(pkg_arches "${repo_dir}/PKGBUILD")"

  if [[ ! -f "${repo_dir}/README.md" ]]; then
    write_readme "${repo_dir}" "${pkgname}" "${pkgdesc}" "${pkgver}" "${arch_list}"
  fi

  if [[ ! -f "${repo_dir}/.gitignore" ]]; then
    write_gitignore "${repo_dir}"
  fi

  if [[ ! -d "${repo_dir}/.git" ]]; then
    git -C "${repo_dir}" init -b main >/dev/null
  else
    git -C "${repo_dir}" branch -M main >/dev/null 2>&1 || true
  fi

  git -C "${repo_dir}" add -A
  if ! git -C "${repo_dir}" diff --cached --quiet; then
    if git -C "${repo_dir}" rev-parse --verify HEAD >/dev/null 2>&1; then
      commit_message="Update package source"
    else
      commit_message="Initial package source"
    fi
    git -C "${repo_dir}" commit -m "${commit_message}" >/dev/null
  fi

  if ! gh repo view "${org}/${pkgname}" >/dev/null 2>&1; then
    log "creating ${org}/${pkgname}"
    gh repo create "${org}/${pkgname}" "--${visibility}" --description "${pkgdesc}" --source "${repo_dir}" --remote origin >/dev/null
  fi

  if git -C "${repo_dir}" remote get-url origin >/dev/null 2>&1; then
    git -C "${repo_dir}" remote set-url origin "${remote_url}"
  else
    git -C "${repo_dir}" remote add origin "${remote_url}"
  fi

  if (( push_changes )); then
    log "pushing ${org}/${pkgname}"
    git -C "${repo_dir}" push -u origin main >/dev/null
  fi

  printf '| `%s` | `%s` |\n' "${pkgname}" "https://github.com/${org}/${pkgname}"
  printf '%s\n' "https://github.com/${org}/${pkgname}.git" >>"${manifest_txt}"
}

log "staging package repos in ${stage_root}"

cat >"${manifest_md}" <<EOF
# ${org} Package Source Repositories

These repositories are the standalone package sources for the KeskOS package build server.

| Package | Repository |
| --- | --- |
EOF

: >"${manifest_txt}"

while IFS= read -r package_dir; do
  pkgname="$(basename "${package_dir}")"
  if [[ "${pkgname}" == "_lib" ]]; then
    continue
  fi
  if is_externally_managed_package "${pkgname}"; then
    log "skipping ${pkgname}; source of truth lives in KeskOS/keskos-desktop or KeskOS/keskos-desktop-meta"
    continue
  fi

  publish_package_repo "${package_dir}" >>"${manifest_md}"
done < <(find "${packages_root}" -mindepth 1 -maxdepth 1 -type d | sort)

log "wrote ${manifest_md}"
log "wrote ${manifest_txt}"
log "published package repo sources for $(find "${packages_root}" -mindepth 1 -maxdepth 1 -type d ! -name '_lib' | wc -l) packages"
