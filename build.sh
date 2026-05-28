#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${REPO_ROOT}/out"
SAFE_BUILD_ROOT="${KESKOS_SAFE_BUILD_ROOT:-/tmp/keskos-build-${UID}}"
WORK_ROOT="${SAFE_BUILD_ROOT}/work"
STAGE_DIR="${WORK_ROOT}/profile"
ARCHISO_WORK_DIR="${WORK_ROOT}/archiso"
LOCAL_REPO_DIR="${WORK_ROOT}/localrepo/x86_64"
GENERATED_PACMAN_CONF="${STAGE_DIR}/pacman.conf"
GENERATED_MIRRORLIST="${STAGE_DIR}/pacman-mirrorlist"
LOCAL_BUILD_PACMAN_CONF="${WORK_ROOT}/local-build-pacman.conf"
LOCAL_BUILD_MIRRORLIST="${WORK_ROOT}/local-build-mirrorlist"
LOCAL_BUILD_PACMAN_WRAPPER="${WORK_ROOT}/local-build-pacman"
PACMAN_SYNC_DB_PATH="${WORK_ROOT}/pacman-sync-db"
PACMAN_SYNC_CACHE_DIR="${WORK_ROOT}/pacman-sync-cache"
AUR_BUILD_ROOT="${SAFE_BUILD_ROOT}/aur"
REPO_BUILD_ROOT="${SAFE_BUILD_ROOT}/repo-packages"
AUR_PKGDEST="${SAFE_BUILD_ROOT}/pkgdest"
GNUPG_BUILD_HOME="${SAFE_BUILD_ROOT}/gnupg"
SOURCE_DATE="${SOURCE_DATE_EPOCH:-$(date +%s)}"
ISO_VERSION="${KESKOS_ISO_VERSION:-$(date --date="@${SOURCE_DATE}" +%Y.%m.%d)}"
REPO_CHECK_SCRIPT="${REPO_ROOT}/scripts/check-keskos-repo-packages.sh"
REQUIRED_PACKAGE_LIST="${REPO_ROOT}/config/keskos-required-packages.txt"
BUILD_MODE="${KESKOS_BUILD_MODE:-release}"
CHECK_ONLY="${KESKOS_BUILD_CHECK_ONLY:-0}"
LOCAL_PACKAGE_ROOT="${KESKOS_LOCAL_PACKAGE_ROOT:-${REPO_ROOT}/packages}"
LOCAL_REPO_SOURCE_DIR="${KESKOS_LOCAL_REPO_SOURCE_DIR:-}"
REPO_PACKAGES=()
LOCAL_PACKAGES=()
BROWSER_AUR_PACKAGES=(librewolf-bin zen-browser-bin brave-bin)
AUR_PACKAGES=()
SKIP_PGP_FALLBACK_PACKAGES=("${BROWSER_AUR_PACKAGES[@]}")
BUILD_SYSTEMSETTINGS_OVERRIDE=0
BUILD_CALAMARES_OVERRIDE=0
BUILD_BROWSER_PKGS=0
SKIP_REPO_CHECK="${KESKOS_SKIP_REPO_CHECK:-0}"

log() {
  printf '[keskos-build] %s\n' "$1"
}

warn() {
  printf '[keskos-build] warning: %s\n' "$1" >&2
}

fail() {
  printf '[keskos-build] error: %s\n' "$1" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: ./build.sh [--check] [--skip-repo-check]

Options:
  --check            Validate inputs, package resolution, and staging, then
                     exit before mkarchiso.
  --skip-repo-check  Skip the KeskOS package availability preflight.

Environment:
  KESKOS_BUILD_MODE=release|local-dev
                               Select the ISO build mode. Defaults to release.
  KESKOS_BUILD_CHECK_ONLY=1    Same as --check.
  KESKOS_BUILD_SYSTEMSETTINGS_OVERRIDE=1
                               In local-dev mode, build a patched systemsettings
                               package into [keskos-local].
  KESKOS_BUILD_CALAMARES_OVERRIDE=1
                               In local-dev mode, build a patched calamares
                               package into [keskos-local].
  KESKOS_BUILD_BROWSER_PKGS=1  In local-dev mode, also build LibreWolf, Zen,
                               and Brave into [keskos-local].
  KESKOS_LOCAL_PACKAGES="pkg1 pkg2"
                               In local-dev mode, build extra local package
                               overrides from KESKOS_LOCAL_PACKAGE_ROOT.
  KESKOS_LOCAL_PACKAGE_ROOT=/path/to/packages
                               Root directory for local package override trees.
  KESKOS_LOCAL_REPO_SOURCE_DIR=/path/to/pkgdir
                               Import prebuilt .pkg.tar.* overrides into
                               [keskos-local] before mkarchiso.
EOF
}

parse_args() {
  while (($#)); do
    case "$1" in
      --check)
        CHECK_ONLY=1
        ;;
      --skip-repo-check)
        SKIP_REPO_CHECK=1
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        fail "Unknown argument: $1"
        ;;
    esac
    shift
  done
}

append_sudo_env_if_set() {
  local -n env_ref="$1"
  local var_name="$2"
  local value="${!var_name-}"

  if [[ -n "$value" ]]; then
    env_ref+=("${var_name}=${value}")
  fi
}

build_sudo_env() {
  local -n env_ref="$1"
  local variable_name=""

  for variable_name in \
    TMPDIR TMP TEMP \
    http_proxy https_proxy ftp_proxy rsync_proxy no_proxy all_proxy \
    HTTP_PROXY HTTPS_PROXY FTP_PROXY RSYNC_PROXY NO_PROXY ALL_PROXY \
    RES_OPTIONS LOCALDOMAIN \
    SSL_CERT_FILE SSL_CERT_DIR CURL_CA_BUNDLE
  do
    append_sudo_env_if_set env_ref "$variable_name"
  done
}

array_contains() {
  local needle="$1"
  shift || true
  local item

  for item in "$@"; do
    if [[ "$item" == "$needle" ]]; then
      return 0
    fi
  done

  return 1
}

env_flag_enabled() {
  case "${1,,}" in
    1|true|yes|on)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

validate_build_mode() {
  case "${BUILD_MODE}" in
    release|local-dev)
      ;;
    *)
      fail "Unsupported KESKOS_BUILD_MODE: ${BUILD_MODE}. Use release or local-dev."
      ;;
  esac
}

parse_local_package_list() {
  local raw_value="${KESKOS_LOCAL_PACKAGES:-}"

  if [[ -z "${raw_value//[[:space:],]/}" ]]; then
    return 0
  fi

  # Support either whitespace-separated or comma-separated package lists.
  read -r -a LOCAL_PACKAGES <<<"${raw_value//,/ }"
}

local_builds_requested() {
  if (( BUILD_SYSTEMSETTINGS_OVERRIDE || BUILD_CALAMARES_OVERRIDE || BUILD_BROWSER_PKGS )); then
    return 0
  fi

  (( ${#LOCAL_PACKAGES[@]} > 0 ))
}

local_repo_overrides_requested() {
  local_builds_requested || [[ -n "${LOCAL_REPO_SOURCE_DIR}" ]]
}

configure_optional_builds() {
  local browser_flag="${KESKOS_BUILD_BROWSER_PKGS:-0}"
  local systemsettings_flag="${KESKOS_BUILD_SYSTEMSETTINGS_OVERRIDE:-0}"
  local calamares_flag="${KESKOS_BUILD_CALAMARES_OVERRIDE:-0}"

  validate_build_mode
  parse_local_package_list

  if [[ "${BUILD_MODE}" == "release" ]]; then
    if env_flag_enabled "${browser_flag}" || env_flag_enabled "${systemsettings_flag}" || env_flag_enabled "${calamares_flag}" || [[ ${#LOCAL_PACKAGES[@]} -gt 0 ]] || [[ -n "${LOCAL_REPO_SOURCE_DIR}" ]]; then
      fail "Release mode does not allow local package builds or [keskos-local] overrides. Use KESKOS_BUILD_MODE=local-dev for override testing."
    fi
    return 0
  fi

  if env_flag_enabled "${systemsettings_flag}"; then
    BUILD_SYSTEMSETTINGS_OVERRIDE=1
    REPO_PACKAGES+=(systemsettings)
  fi

  if env_flag_enabled "${calamares_flag}"; then
    BUILD_CALAMARES_OVERRIDE=1
    AUR_PACKAGES+=(calamares)
  fi

  if env_flag_enabled "${browser_flag}"; then
    BUILD_BROWSER_PKGS=1
    AUR_PACKAGES+=("${BROWSER_AUR_PACKAGES[@]}")
  fi
}

print_build_mode_summary() {
  local priority="[keskos] -> [core] -> [extra]"

  if [[ "${BUILD_MODE}" == "local-dev" ]]; then
    priority="[keskos-local] -> ${priority}"
  fi

  log "Build mode: ${BUILD_MODE}"
  log "Package source priority: ${priority}"

  if [[ "${BUILD_MODE}" == "release" ]]; then
    log "Local package builds: disabled"
    log "Local package repo overrides: disabled"
    log "Browser package builds: disabled"
    return 0
  fi

  if (( BUILD_SYSTEMSETTINGS_OVERRIDE || BUILD_CALAMARES_OVERRIDE || BUILD_BROWSER_PKGS || ${#LOCAL_PACKAGES[@]} > 0 )); then
    log "Local package builds are enabled for this run."
  else
    log "Local package builds are disabled for this local-dev run."
  fi

  if (( BUILD_SYSTEMSETTINGS_OVERRIDE )); then
    log "Local override enabled: patched systemsettings"
  fi

  if (( BUILD_CALAMARES_OVERRIDE )); then
    log "Local override enabled: patched calamares"
  fi

  if (( BUILD_BROWSER_PKGS )); then
    log "Local override enabled: browser AUR packages (${BROWSER_AUR_PACKAGES[*]})"
  else
    log "Browser package builds: disabled"
  fi

  if (( ${#LOCAL_PACKAGES[@]} > 0 )); then
    log "Local package builds requested from ${LOCAL_PACKAGE_ROOT}: ${LOCAL_PACKAGES[*]}"
  fi

  if [[ -n "${LOCAL_REPO_SOURCE_DIR}" ]]; then
    log "Prebuilt local override import directory: ${LOCAL_REPO_SOURCE_DIR}"
  fi

  if (( CHECK_ONLY )); then
    log "Check-only mode: mkarchiso and optional local override builds will be skipped."
  fi
}

cleanup_safe_build_root() {
  if [[ -e "$SAFE_BUILD_ROOT" ]]; then
    log "Cleaning previous temporary build root..."
    sudo rm -rf "$SAFE_BUILD_ROOT"
  fi
}

restore_build_root_ownership() {
  if [[ -e "$SAFE_BUILD_ROOT" ]]; then
    sudo chown -R "$(id -u):$(id -g)" "$SAFE_BUILD_ROOT" 2>/dev/null || true
  fi
}

require_command() {
  local command_name="$1"
  local package_hint="${2:-$1}"
  command -v "$command_name" >/dev/null 2>&1 || fail "Missing required command: ${command_name}. Install it with: sudo pacman -S --needed ${package_hint}"
}

check_arch_host() {
  [[ -f /etc/os-release ]] || fail "This build script must be run on Arch Linux."
  # shellcheck disable=SC1091
  . /etc/os-release
  [[ "${ID:-}" == "arch" || "${ID_LIKE:-}" == *arch* ]] || fail "This build script must be run on Arch Linux."
  command -v pacman >/dev/null 2>&1 || fail "pacman was not found. This build script must be run on Arch Linux."
}

check_dependencies() {
  local deps=(
    "mkarchiso:archiso"
    "grub-install:grub"
    "syslinux:syslinux"
    "awk:gawk"
    "sed:sed"
    "install:coreutils"
    "python3:python"
    "sudo:sudo"
  )
  local local_repo_deps=(
    "repo-add:pacman-contrib"
  )
  local local_makepkg_deps=(
    "makepkg:base-devel"
  )
  local local_vcs_deps=(
    "git:git"
    "patch:patch"
    "gpg:gnupg"
  )
  local local_browser_deps=(
    "curl:curl"
    "bsdtar:libarchive"
  )
  local dep
  local command_name
  local package_hint

  for dep in "${deps[@]}"; do
    command_name="${dep%%:*}"
    package_hint="${dep#*:}"
    require_command "$command_name" "$package_hint"
  done

  if local_repo_overrides_requested; then
    for dep in "${local_repo_deps[@]}"; do
      command_name="${dep%%:*}"
      package_hint="${dep#*:}"
      require_command "$command_name" "$package_hint"
    done
  fi

  if local_builds_requested; then
    for dep in "${local_makepkg_deps[@]}"; do
      command_name="${dep%%:*}"
      package_hint="${dep#*:}"
      require_command "$command_name" "$package_hint"
    done
  fi

  if (( BUILD_SYSTEMSETTINGS_OVERRIDE || BUILD_CALAMARES_OVERRIDE || BUILD_BROWSER_PKGS )); then
    for dep in "${local_vcs_deps[@]}"; do
      command_name="${dep%%:*}"
      package_hint="${dep#*:}"
      require_command "$command_name" "$package_hint"
    done
  fi

  if (( BUILD_BROWSER_PKGS )); then
    for dep in "${local_browser_deps[@]}"; do
      command_name="${dep%%:*}"
      package_hint="${dep#*:}"
      require_command "$command_name" "$package_hint"
    done
  fi
}

validate_repo_inputs() {
  local required_path=""
  local required_paths=(
    "${REPO_ROOT}/packages.x86_64"
    "${REPO_ROOT}/pacman.conf"
    "${REPO_ROOT}/profiledef.sh"
    "${REPO_ROOT}/airootfs"
    "${REPO_ROOT}/calamares"
    "${REPO_CHECK_SCRIPT}"
    "${REQUIRED_PACKAGE_LIST}"
  )

  for required_path in "${required_paths[@]}"; do
    [[ -e "${required_path}" ]] || fail "Required repo input is missing: ${required_path}"
  done
}

validate_packages_seed() {
  local seed_file="${REPO_ROOT}/packages.x86_64"
  local required_package=""
  local forbidden_package=""
  local required_packages=(
    "keskos-release"
    "keskos-keyring"
    "keskos-mirrorlist"
    "keskos-tools"
    "keskos-branding"
    "keskos-theme"
    "keskos-settings"
    "keskos-welcome"
    "keskos-browser-startpage"
    "keskos-core-meta"
    "keskos-desktop-meta"
    "keskos-system-tools-meta"
    "networkmanager"
    "plasma-nm"
    "xdg-utils"
    "calamares"
  )
  local forbidden_packages=(
    "brave-bin"
    "librewolf-bin"
    "zen-browser-bin"
    "keskos-browsers-meta"
  )

  [[ -f "${seed_file}" ]] || fail "ISO seed list is missing: ${seed_file}"

  for required_package in "${required_packages[@]}"; do
    grep -Fxq "${required_package}" "${seed_file}" || fail "packages.x86_64 is missing required package: ${required_package}"
  done

  for forbidden_package in "${forbidden_packages[@]}"; do
    if grep -Fxq "${forbidden_package}" "${seed_file}"; then
      fail "packages.x86_64 still contains a package that should not be preinstalled: ${forbidden_package}"
    fi
  done
}

validate_local_override_sources() {
  local package_name=""

  for package_name in "${LOCAL_PACKAGES[@]}"; do
    [[ -f "${LOCAL_PACKAGE_ROOT}/${package_name}/PKGBUILD" ]] || fail "Requested local override package is missing: ${LOCAL_PACKAGE_ROOT}/${package_name}/PKGBUILD"
  done
}

run_keskos_repo_preflight() {
  if (( SKIP_REPO_CHECK )); then
    warn "Skipping the KeskOS package availability preflight."
    return 0
  fi

  [[ -x "${REPO_CHECK_SCRIPT}" ]] || fail "Preflight helper is missing or not executable: ${REPO_CHECK_SCRIPT}"
  log "Checking that required KeskOS packages are available from downloads.keskos.org..."
  "${REPO_CHECK_SCRIPT}"
}

prepare_workdirs() {
  mkdir -p "$OUT_DIR"
  cleanup_safe_build_root
  mkdir -p "$STAGE_DIR" "$ARCHISO_WORK_DIR"
  mkdir -p "$LOCAL_REPO_DIR"
  mkdir -p "$AUR_BUILD_ROOT" "$REPO_BUILD_ROOT" "$AUR_PKGDEST"
  mkdir -p "$PACMAN_SYNC_DB_PATH" "$PACMAN_SYNC_CACHE_DIR"
  mkdir -p "$GNUPG_BUILD_HOME"
  chmod 700 "$GNUPG_BUILD_HOME"

  log "Using temporary build root: ${SAFE_BUILD_ROOT}"
  if [[ "$REPO_ROOT" == *" "* ]]; then
    log "Repo path contains spaces; staging Archiso and AUR builds outside the repo to avoid makepkg/CMake and chroot path issues."
  fi
}

init_build_keyring() {
  GNUPGHOME="$GNUPG_BUILD_HOME" gpg --batch --list-keys >/dev/null 2>&1 || true
}

pkgbuild_validpgpkeys() {
  local package_dir="$1"
  (
    cd "$package_dir"
    bash -c 'set -euo pipefail; source ./PKGBUILD >/dev/null 2>&1; for key in "${validpgpkeys[@]:-}"; do printf "%s\n" "$key"; done'
  )
}

import_pkgbuild_keys() {
  local package_name="$1"
  local package_dir="$2"
  local -a keys=()
  local -a keyservers=(
    "hkps://keys.openpgp.org"
    "hkps://keyserver.ubuntu.com"
  )
  local key=""
  local keyserver=""
  local imported=0

  mapfile -t keys < <(pkgbuild_validpgpkeys "$package_dir" 2>/dev/null || true)
  if (( ${#keys[@]} == 0 )); then
    return 0
  fi

  init_build_keyring

  for key in "${keys[@]}"; do
    [[ -n "$key" ]] || continue
    if GNUPGHOME="$GNUPG_BUILD_HOME" gpg --batch --list-keys "$key" >/dev/null 2>&1; then
      continue
    fi

    imported=0
    for keyserver in "${keyservers[@]}"; do
      if GNUPGHOME="$GNUPG_BUILD_HOME" gpg --batch --keyserver "$keyserver" --recv-keys "$key" >/dev/null 2>&1; then
        log "Imported PGP key ${key} for ${package_name} from ${keyserver}."
        imported=1
        break
      fi
    done

    if (( imported == 0 )); then
      warn "Could not import PGP key ${key} for ${package_name}; build may require a later retry or skippgpcheck fallback."
    fi
  done
}

copy_package_archives_to_local_repo() {
  local package_name="$1"
  local source_dir="$2"
  local -a built_files=()

  mapfile -t built_files < <(
    find "${source_dir}" -maxdepth 1 -type f \
      \( -name "${package_name}-*.pkg.tar.zst" -o -name "${package_name}-*.pkg.tar.xz" -o -name "${package_name}-*.pkg.tar" \) \
      | sort
  )

  (( ${#built_files[@]} > 0 )) || fail "No built package archive was found for ${package_name} in ${source_dir}"
  cp -f "${built_files[@]}" "${LOCAL_REPO_DIR}/"
}

zen_latest_release_tag() {
  local asset_name="$1"
  local location=""

  location="$(
    curl -fsSI "https://github.com/zen-browser/desktop/releases/latest/download/${asset_name}" \
      | tr -d '\r' \
      | awk -F': ' 'tolower($1) == "location" { print $2; exit }'
  )"

  [[ -n "$location" ]] || fail "Could not resolve the latest Zen Browser release redirect for ${asset_name}."

  printf '%s\n' "$location" | sed -E 's#^.*/releases/download/([^/]+)/.*#\1#'
}

zen_release_sha256() {
  local url="$1"
  curl -fsSL "$url" | sha256sum | awk '{print $1}'
}

patch_zen_browser_pkgbuild() {
  local package_dir="$1"
  local latest_tag=""
  local x86_url=""
  local aarch64_url=""
  local x86_sha=""
  local aarch64_sha=""

  latest_tag="$(zen_latest_release_tag "zen.linux-x86_64.tar.xz")"
  x86_url="https://github.com/zen-browser/desktop/releases/download/${latest_tag}/zen.linux-x86_64.tar.xz"
  aarch64_url="https://github.com/zen-browser/desktop/releases/download/${latest_tag}/zen.linux-aarch64.tar.xz"

  log "Patching zen-browser-bin PKGBUILD to use live Zen release ${latest_tag}."

  x86_sha="$(zen_release_sha256 "$x86_url")"
  aarch64_sha="$(zen_release_sha256 "$aarch64_url")"

  python3 - "$package_dir/PKGBUILD" "$latest_tag" "$x86_url" "$aarch64_url" "$x86_sha" "$aarch64_sha" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
latest_tag = sys.argv[2]
x86_url = sys.argv[3]
aarch64_url = sys.argv[4]
x86_sha = sys.argv[5]
aarch64_sha = sys.argv[6]

text = path.read_text(encoding="utf-8")

patterns = {
    r'^pkgver=.*$': f'pkgver={latest_tag}',
    r'^source_x86_64=\(.*\)$': f'source_x86_64=("zen-browser-$pkgver-$pkgrel-x86_64.tar.xz::{x86_url}")',
    r'^source_aarch64=\(.*\)$': f'source_aarch64=("zen-browser-$pkgver-$pkgrel-aarch64.tar.xz::{aarch64_url}")',
    r"^sha256sums_x86_64=\('.*'\)$": f"sha256sums_x86_64=('{x86_sha}')",
    r"^sha256sums_aarch64=\('.*'\)$": f"sha256sums_aarch64=('{aarch64_sha}')",
}

for pattern, replacement in patterns.items():
    text, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if count != 1:
        raise SystemExit(f"Failed to patch zen-browser-bin PKGBUILD pattern: {pattern}")

path.write_text(text, encoding="utf-8")
PY
}

patch_systemsettings_pkgbuild() {
  local package_dir="$1"

  log "Patching Arch systemsettings packaging to apply KeskOS sidebar QML overrides..."

  mkdir -p "${package_dir}/keskos_systemsettings_qml"
  install -m 755 "${REPO_ROOT}/patches/systemsettings/keskos_systemsettings_ui.py" \
    "${package_dir}/keskos_systemsettings_ui.py"
  install -m 644 "${REPO_ROOT}/patches/systemsettings/keskos_systemsettings_qml/CategoriesPage.qml" \
    "${package_dir}/keskos_systemsettings_qml/CategoriesPage.qml"
  install -m 644 "${REPO_ROOT}/patches/systemsettings/keskos_systemsettings_qml/CategoryItem.qml" \
    "${package_dir}/keskos_systemsettings_qml/CategoryItem.qml"
  install -m 644 "${REPO_ROOT}/patches/systemsettings/keskos_systemsettings_qml/HamburgerMenuButton.qml" \
    "${package_dir}/keskos_systemsettings_qml/HamburgerMenuButton.qml"
  install -m 644 "${REPO_ROOT}/patches/systemsettings/keskos_systemsettings_qml/SubCategoryPage.qml" \
    "${package_dir}/keskos_systemsettings_qml/SubCategoryPage.qml"

  python3 - "$package_dir/PKGBUILD" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
prepare_snippet = """prepare() {\n  python3 \"$startdir/keskos_systemsettings_ui.py\" \"$srcdir/$pkgname-$pkgver\"\n}\n\n"""

if prepare_snippet in text:
    path.write_text(text, encoding="utf-8")
    raise SystemExit(0)

if re.search(r"^prepare\(\)\s*\{", text, flags=re.MULTILINE):
    raise SystemExit("systemsettings PKGBUILD already defines prepare(); update patch_systemsettings_pkgbuild before continuing.")

text, count = re.subn(r"^pkgrel=(.+)$", lambda match: f"pkgrel={match.group(1)}.1", text, count=1, flags=re.MULTILINE)
if count != 1:
    raise SystemExit("Failed to bump systemsettings pkgrel in PKGBUILD.")

marker = "build() {\n"
if marker not in text:
    raise SystemExit("Failed to locate build() in systemsettings PKGBUILD.")
text = text.replace(marker, prepare_snippet + marker, 1)

path.write_text(text, encoding="utf-8")
PY
}

build_repo_package() {
  local package_name="$1"
  local package_dir="${REPO_BUILD_ROOT}/${package_name}"
  local package_repo_url="https://gitlab.archlinux.org/archlinux/packaging/packages/${package_name}.git"

  if [[ ! -d "$package_dir/.git" ]]; then
    log "Cloning Arch package ${package_name}..."
    git clone --depth 1 "$package_repo_url" "$package_dir"
  else
    log "Refreshing Arch package ${package_name}..."
    git -C "$package_dir" fetch origin
    git -C "$package_dir" reset --hard origin/main
  fi

  if [[ "$package_name" == "systemsettings" ]]; then
    patch_systemsettings_pkgbuild "$package_dir"
  fi

  log "Building ${package_name} for the local ISO repository..."
  (
    cd "$package_dir"
    import_pkgbuild_keys "$package_name" "$package_dir"
    GNUPGHOME="$GNUPG_BUILD_HOME" PKGDEST="${AUR_PKGDEST}" \
      makepkg --syncdeps --needed --noconfirm --cleanbuild --clean
  )

  copy_package_archives_to_local_repo "$package_name" "$AUR_PKGDEST"
}

build_aur_package() {
  local package_name="$1"
  local package_dir="${AUR_BUILD_ROOT}/${package_name}"

  if [[ ! -d "$package_dir/.git" ]]; then
    log "Cloning AUR package ${package_name}..."
    git clone "https://aur.archlinux.org/${package_name}.git" "$package_dir"
  else
    log "Refreshing AUR package ${package_name}..."
    git -C "$package_dir" fetch origin
    git -C "$package_dir" reset --hard origin/master
  fi

  if [[ "$package_name" == "calamares" ]]; then
    log "Patching AUR calamares PKGBUILD to apply KeskOS UI polish and compatibility fixes..."
    install -m 644 "${REPO_ROOT}/calamares/patches/keskos_calamares_ui.py" \
      "${package_dir}/keskos_calamares_ui.py"
    python3 - "$package_dir/PKGBUILD" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
for needle in (
    "    packagechooser\n",
    "    packagechooserq\n",
):
    text = text.replace(needle, "")
marker = '  local _cmake_options=(\n'
snippet = """  python3 \"$startdir/keskos_calamares_ui.py\" \"$_pkgsrc_dir\"\n\n"""
if snippet not in text:
    text = text.replace(marker, snippet + marker, 1)
path.write_text(text, encoding="utf-8")
PY
  fi

  if [[ "$package_name" == "zen-browser-bin" ]]; then
    patch_zen_browser_pkgbuild "$package_dir"
  fi

  log "Building ${package_name} for the local ISO repository..."
  (
    cd "$package_dir"
    import_pkgbuild_keys "$package_name" "$package_dir"
    if ! GNUPGHOME="$GNUPG_BUILD_HOME" PKGDEST="${AUR_PKGDEST}" \
      makepkg --syncdeps --needed --noconfirm --cleanbuild --clean; then
      if array_contains "$package_name" "${SKIP_PGP_FALLBACK_PACKAGES[@]}"; then
        warn "Retrying ${package_name} with --skippgpcheck after key import failed."
        GNUPGHOME="$GNUPG_BUILD_HOME" PKGDEST="${AUR_PKGDEST}" \
          makepkg --syncdeps --needed --noconfirm --cleanbuild --clean --skippgpcheck
      else
        return 1
      fi
    fi
  )

  copy_package_archives_to_local_repo "$package_name" "$AUR_PKGDEST"
}

build_local_package() {
  local package_name="$1"
  local source_dir="${LOCAL_PACKAGE_ROOT}/${package_name}"
  local build_dir="${SAFE_BUILD_ROOT}/local-packages/${package_name}"
  local -a makepkg_env=()

  [[ -f "${source_dir}/PKGBUILD" ]] || fail "Local package source was not found: ${source_dir}"

  rm -rf "$build_dir"
  mkdir -p "$(dirname "$build_dir")"
  cp -a "$source_dir" "$build_dir"

  if local_repo_has_packages; then
    refresh_local_repo
    generate_local_build_pacman_conf
    sync_local_build_repo
    makepkg_env+=("PACMAN=${LOCAL_BUILD_PACMAN_WRAPPER}")
  fi

  log "Building local package ${package_name}..."
  (
    cd "$build_dir"
    env PKGDEST="${AUR_PKGDEST}" "${makepkg_env[@]}" \
      makepkg --syncdeps --needed --noconfirm --cleanbuild --clean --rmdeps
  )

  copy_package_archives_to_local_repo "$package_name" "$AUR_PKGDEST"
  refresh_local_repo
}

refresh_local_repo() {
  local -a repo_packages=()

  mapfile -t repo_packages < <(
    find "${LOCAL_REPO_DIR}" -maxdepth 1 -type f \
      \( -name '*.pkg.tar.zst' -o -name '*.pkg.tar.xz' -o -name '*.pkg.tar' \) \
      | sort
  )

  if (( ${#repo_packages[@]} == 0 )); then
    rm -f "${LOCAL_REPO_DIR}"/keskos-local.db* "${LOCAL_REPO_DIR}"/keskos-local.files*
    return 0
  fi

  log "Refreshing the local pacman repository..."
  rm -f "${LOCAL_REPO_DIR}"/keskos-local.db* "${LOCAL_REPO_DIR}"/keskos-local.files*
  repo-add "${LOCAL_REPO_DIR}/keskos-local.db.tar.gz" "${repo_packages[@]}"
}

local_repo_has_packages() {
  compgen -G "${LOCAL_REPO_DIR}/*.pkg.tar.zst" >/dev/null || \
    compgen -G "${LOCAL_REPO_DIR}/*.pkg.tar.xz" >/dev/null || \
    compgen -G "${LOCAL_REPO_DIR}/*.pkg.tar" >/dev/null
}

import_local_repo_packages() {
  local -a imported_files=()

  [[ -n "${LOCAL_REPO_SOURCE_DIR}" ]] || return 0
  [[ -d "${LOCAL_REPO_SOURCE_DIR}" ]] || fail "Local repo import directory was not found: ${LOCAL_REPO_SOURCE_DIR}"

  mapfile -t imported_files < <(
    find "${LOCAL_REPO_SOURCE_DIR}" -maxdepth 1 -type f \
      \( -name '*.pkg.tar.zst' -o -name '*.pkg.tar.xz' -o -name '*.pkg.tar' \) \
      | sort
  )

  if (( ${#imported_files[@]} == 0 )); then
    warn "No prebuilt package archives were found in ${LOCAL_REPO_SOURCE_DIR}"
    return 0
  fi

  log "Importing prebuilt local override packages from ${LOCAL_REPO_SOURCE_DIR}..."
  cp -f "${imported_files[@]}" "${LOCAL_REPO_DIR}/"
  refresh_local_repo
}

write_generated_pacman_conf() {
  local output_path="$1"
  local mirrorlist_output="$2"
  local local_repo_uri=""
  local enable_local_repo=0
  local mirrorlist_source="${KESKOS_OVERRIDE_MIRRORLIST:-/etc/pacman.d/mirrorlist}"

  [[ -f "$mirrorlist_source" ]] || fail "Pacman mirrorlist source was not found: ${mirrorlist_source}"
  grep -Eq '^[[:space:]]*Server[[:space:]]*=' "$mirrorlist_source" || fail "Pacman mirrorlist source has no usable Server entries: ${mirrorlist_source}"

  install -m 644 "$mirrorlist_source" "${mirrorlist_output}"
  if local_repo_has_packages; then
    enable_local_repo=1
    local_repo_uri="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve().as_uri())' "${LOCAL_REPO_DIR}")"
  fi

  python3 - "${REPO_ROOT}/pacman.conf" "${output_path}" "${local_repo_uri}" "${mirrorlist_output}" "${enable_local_repo}" <<'PY'
from pathlib import Path
import sys

template_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
local_repo_uri = sys.argv[3]
mirrorlist_path = sys.argv[4]
enable_local_repo = sys.argv[5] == "1"

lines = template_path.read_text(encoding="utf-8").splitlines(keepends=True)
output_lines = []
skipping_local_repo = False

for line in lines:
    stripped = line.strip()
    if stripped == "[keskos-local]" and not enable_local_repo:
        skipping_local_repo = True
        continue
    if skipping_local_repo and stripped.startswith("[") and stripped.endswith("]"):
        skipping_local_repo = False
    if skipping_local_repo:
        continue
    if enable_local_repo:
        line = line.replace("__KESKOS_LOCAL_REPO_URI__", local_repo_uri)
    output_lines.append(line.replace("/etc/pacman.d/mirrorlist", mirrorlist_path))

output_path.write_text("".join(output_lines), encoding="utf-8")
PY
}

generate_local_build_pacman_conf() {
  log "Generating a pacman.conf for local package dependency resolution..."
  write_generated_pacman_conf "${LOCAL_BUILD_PACMAN_CONF}" "${LOCAL_BUILD_MIRRORLIST}"
  cat >"${LOCAL_BUILD_PACMAN_WRAPPER}" <<EOF
#!/usr/bin/env bash
exec /usr/bin/pacman --config "${LOCAL_BUILD_PACMAN_CONF}" "\$@"
EOF
  chmod +x "${LOCAL_BUILD_PACMAN_WRAPPER}"
}

sync_local_build_repo() {
  local -a sudo_env=()

  build_sudo_env sudo_env
  log "Syncing local package dependency repositories..."
  sudo env "${sudo_env[@]}" "${LOCAL_BUILD_PACMAN_WRAPPER}" -Sy --noconfirm
}

generate_pacman_conf() {
  if local_repo_has_packages; then
    log "Generating a profile-local pacman.conf that prefers [keskos-local] overrides before [keskos]..."
  else
    log "Generating a profile-local pacman.conf that consumes the published KeskOS pacman repo..."
  fi
  write_generated_pacman_conf "${GENERATED_PACMAN_CONF}" "${GENERATED_MIRRORLIST}"
}

validate_generated_pacman_conf() {
  [[ -f "${GENERATED_PACMAN_CONF}" ]] || fail "Generated pacman.conf is missing: ${GENERATED_PACMAN_CONF}"
  [[ -s "${GENERATED_PACMAN_CONF}" ]] || fail "Generated pacman.conf is empty: ${GENERATED_PACMAN_CONF}"
  [[ -f "${GENERATED_MIRRORLIST}" ]] || fail "Generated pacman mirrorlist is missing: ${GENERATED_MIRRORLIST}"
  [[ -s "${GENERATED_MIRRORLIST}" ]] || fail "Generated pacman mirrorlist is empty: ${GENERATED_MIRRORLIST}"

  python3 - "${GENERATED_PACMAN_CONF}" <<'PY'
from pathlib import Path
import sys

config_path = Path(sys.argv[1])
text = config_path.read_text(encoding="utf-8")
include_paths: list[str] = []

for raw_line in text.splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#"):
        continue
    if line.lower().startswith("include"):
        _, _, include_value = line.partition("=")
        include_value = include_value.strip()
        if not include_value:
            raise SystemExit(f"Generated pacman.conf has an empty Include directive: {config_path}")
        include_paths.append(include_value)

for include_path in include_paths:
    if not Path(include_path).is_file():
        raise SystemExit(f"Generated pacman.conf references a missing Include path: {include_path}")
PY
}

preflight_repo_sync() {
  local -a sudo_env=()
  local attempt=1
  local max_attempts="${KESKOS_PACMAN_SYNC_ATTEMPTS:-3}"

  validate_generated_pacman_conf
  build_sudo_env sudo_env
  sudo mkdir -p "$PACMAN_SYNC_DB_PATH" "$PACMAN_SYNC_CACHE_DIR"

  while (( attempt <= max_attempts )); do
    log "Preflighting pacman repository sync (attempt ${attempt}/${max_attempts})..."
    if sudo env "${sudo_env[@]}" pacman \
      --config "${GENERATED_PACMAN_CONF}" \
      --dbpath "${PACMAN_SYNC_DB_PATH}" \
      --cachedir "${PACMAN_SYNC_CACHE_DIR}" \
      -Sy --noconfirm; then
      log "Pacman repository sync preflight succeeded."
      return 0
    fi

    if (( attempt == max_attempts )); then
      fail "Pacman repository sync failed after ${max_attempts} attempts. On WSL, check DNS resolution, proxy settings, and mirror reachability."
    fi

    warn "Pacman repository sync preflight failed. Retrying in 5 seconds..."
    sleep 5
    attempt=$((attempt + 1))
  done
}

validate_required_packages_in_generated_conf() {
  local package_name=""
  local -a packages=()
  local -a missing=()
  local -a sudo_env=()

  [[ -f "${REQUIRED_PACKAGE_LIST}" ]] || fail "Required package list was not found: ${REQUIRED_PACKAGE_LIST}"

  mapfile -t packages < <(awk '
    /^[[:space:]]*#/ { next }
    /^[[:space:]]*$/ { next }
    { print $1 }
  ' "${REQUIRED_PACKAGE_LIST}")

  (( ${#packages[@]} > 0 )) || fail "No required packages were found in ${REQUIRED_PACKAGE_LIST}"

  build_sudo_env sudo_env
  log "Validating required KeskOS packages through the generated pacman.conf..."

  for package_name in "${packages[@]}"; do
    if ! sudo env "${sudo_env[@]}" pacman \
      --config "${GENERATED_PACMAN_CONF}" \
      --dbpath "${PACMAN_SYNC_DB_PATH}" \
      -Si "${package_name}" >/dev/null 2>&1; then
      missing+=("${package_name}")
    fi
  done

  if (( ${#missing[@]} > 0 )); then
    printf '[keskos-build] missing required package in generated pacman configuration: %s\n' "${missing[@]}" >&2
    fail "Required KeskOS packages could not be resolved through the generated pacman.conf"
  fi
}

stage_profile_basics() {
  log "Staging the Archiso profile..."
  cp -a "${REPO_ROOT}/airootfs" "${STAGE_DIR}/"
  cp -a "${REPO_ROOT}/grub" "${STAGE_DIR}/"
  cp -a "${REPO_ROOT}/syslinux" "${STAGE_DIR}/"
  cp -a "${REPO_ROOT}/efiboot" "${STAGE_DIR}/"
  install -m 644 "${REPO_ROOT}/profiledef.sh" "${STAGE_DIR}/profiledef.sh"
  install -m 644 "${REPO_ROOT}/packages.x86_64" "${STAGE_DIR}/packages.x86_64"
  install -d -m 1777 "${STAGE_DIR}/airootfs/tmp" "${STAGE_DIR}/airootfs/var/tmp"

  python3 - "${STAGE_DIR}/airootfs/etc/os-release" "${ISO_VERSION}" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
iso_version = sys.argv[2].strip() or "rolling"
lines = []
seen = set()

for raw_line in path.read_text(encoding="utf-8").splitlines():
    if raw_line.startswith("BUILD_ID="):
        lines.append(f'BUILD_ID="{iso_version}"')
        seen.add("BUILD_ID")
    elif raw_line.startswith("IMAGE_BUILD_DATE="):
        lines.append(f'IMAGE_BUILD_DATE="{iso_version}"')
        seen.add("IMAGE_BUILD_DATE")
    else:
        lines.append(raw_line)

for key, value in (
    ("BUILD_ID", iso_version),
    ("IMAGE_BUILD_DATE", iso_version),
):
    if key not in seen:
        lines.append(f'{key}="{value}"')

path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
}

prune_packaged_live_overlays() {
  local root="${STAGE_DIR}/airootfs"
  # These paths are supplied by published `keskos-*` packages and should not be
  # copied from the ISO repo into the staged airootfs unless we intentionally
  # need a temporary local override.
  local -a migrated_paths=(
    "etc/xdg/autostart/dunst.desktop"
    "etc/xdg/autostart/keskos-first-run.desktop"
    "etc/xdg/autostart/keskos-quickshell.desktop"
    "etc/skel/.config/autostart/keskos-display-watch.desktop"
    "etc/skel/.config/autostart/keskos-first-run.desktop"
    "etc/skel/.config/autostart/keskos-quickshell.desktop"
    "etc/skel/.config/dunst/dunstrc"
    "etc/skel/Desktop/Install KeskOS.desktop"
    "usr/bin/kesk"
    "usr/bin/kesk-apply-theme"
    "usr/bin/kesk-hide-kcms"
    "usr/bin/kesk-list-kcms"
    "usr/bin/kesk-restore-kcms"
    "usr/bin/kesk-theme-status"
    "usr/bin/keskos-first-run"
    "usr/bin/keskos-fix-launcher"
    "usr/bin/keskos-launcher-switch"
    "usr/bin/keskos-reset-panel"
    "usr/bin/keskos-shell"
    "usr/lib/calamares/modules/keskoschoices"
    "usr/lib/kesk"
    "usr/lib/keskos-first-run"
    "usr/lib/keskos-installer/apply-install-choices.sh"
    "usr/local/bin/keskos-about"
    "usr/local/bin/keskos-configure-user"
    "usr/local/bin/keskos-display-watch"
    "usr/local/bin/keskos-open-installer"
    "usr/local/bin/keskos-open-installer-log"
    "usr/local/bin/keskos-postinstall-root"
    "usr/local/bin/keskos-prepare-target-root"
    "usr/local/bin/keskos-quickshell-data"
    "usr/local/bin/keskos-select-resolution"
    "usr/local/bin/keskos-session-start"
    "usr/local/bin/keskos-shell"
    "usr/local/bin/keskos-start-quickshell"
    "usr/local/bin/keskos-terminal-shell"
    "usr/local/bin/keskos-wallpaper-apply"
    "usr/local/bin/keskos-workspace"
    "usr/share/applications/install-keskos-debug.desktop"
    "usr/share/applications/install-keskos.desktop"
    "usr/share/applications/keskos-first-run.desktop"
    "usr/share/keskos/browser-themes"
    "usr/share/keskos/first-run/browser-theme"
    "usr/share/keskos/installer/package-manifest.json"
    "usr/share/polkit-1/actions/org.keskos.settings.policy"
  )
  local relative_path=""

  log "Pruning staged airootfs files that are now provided by KeskOS packages..."

  for relative_path in "${migrated_paths[@]}"; do
    rm -rf "${root}/${relative_path}"
  done
}

stage_boot_branding() {
  log "Adjusting the profile version metadata..."
  sed -i "s/__KESKOS_ISO_VERSION__/${ISO_VERSION}/g" "${STAGE_DIR}/profiledef.sh"
}

run_mkarchiso() {
  local -a sudo_env=()
  local returncode=0
  validate_generated_pacman_conf
  log "Building the KeskOS ISO with mkarchiso..."
  build_sudo_env sudo_env
  if sudo env "${sudo_env[@]}" mkarchiso \
    -v \
    -C "${GENERATED_PACMAN_CONF}" \
    -w "${ARCHISO_WORK_DIR}" \
    -o "${OUT_DIR}" \
    "${STAGE_DIR}"; then
    returncode=0
  else
    returncode=$?
  fi
  restore_build_root_ownership
  return "$returncode"
}

main() {
  local package_name=""

  parse_args "$@"
  configure_optional_builds
  check_arch_host
  validate_repo_inputs
  validate_packages_seed
  validate_local_override_sources
  check_dependencies
  if (( EUID == 0 )); then
    fail "Run build.sh as a regular user. The script will call sudo only for mkarchiso."
  fi

  print_build_mode_summary

  run_keskos_repo_preflight
  prepare_workdirs
  trap restore_build_root_ownership EXIT
  import_local_repo_packages

  if (( CHECK_ONLY )) && local_builds_requested; then
    log "Check-only mode: skipping local override builds."
  else
    for package_name in "${REPO_PACKAGES[@]}"; do
      build_repo_package "$package_name"
    done

    for package_name in "${LOCAL_PACKAGES[@]}"; do
      build_local_package "$package_name"
    done

    for package_name in "${AUR_PACKAGES[@]}"; do
      build_aur_package "$package_name"
    done
  fi

  if local_repo_has_packages; then
    refresh_local_repo
  else
    log "No local package overrides were staged for this build."
  fi
  generate_pacman_conf
  preflight_repo_sync
  validate_required_packages_in_generated_conf
  stage_profile_basics
  prune_packaged_live_overlays
  stage_boot_branding

  if (( CHECK_ONLY )); then
    log "Check-only validation complete."
    trap - EXIT
    restore_build_root_ownership
    return 0
  fi

  run_mkarchiso
  trap - EXIT
  restore_build_root_ownership

  log "KeskOS ISO build complete."
  log "Output directory: ${OUT_DIR}"
}

main "$@"
