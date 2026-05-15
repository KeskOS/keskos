#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${REPO_ROOT}/out"
SAFE_BUILD_ROOT="/tmp/keskos-build-${UID}"
WORK_ROOT="${SAFE_BUILD_ROOT}/work"
STAGE_DIR="${WORK_ROOT}/profile"
ARCHISO_WORK_DIR="${WORK_ROOT}/archiso"
LOCAL_REPO_DIR="${WORK_ROOT}/localrepo/x86_64"
GENERATED_PACMAN_CONF="${WORK_ROOT}/pacman.conf"
AUR_BUILD_ROOT="${SAFE_BUILD_ROOT}/aur"
AUR_PKGDEST="${SAFE_BUILD_ROOT}/pkgdest"
GNUPG_BUILD_HOME="${SAFE_BUILD_ROOT}/gnupg"
SOURCE_DATE="${SOURCE_DATE_EPOCH:-$(date +%s)}"
ISO_VERSION="${KESKOS_ISO_VERSION:-$(date --date="@${SOURCE_DATE}" +%Y.%m.%d)}"
AUR_PACKAGES=(calamares librewolf-bin zen-browser-bin brave-bin)
SKIP_PGP_FALLBACK_PACKAGES=(librewolf-bin zen-browser-bin brave-bin)

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
    "makepkg:base-devel"
    "repo-add:pacman-contrib"
    "grub-install:grub"
    "syslinux:syslinux"
    "curl:curl"
    "git:git"
    "awk:gawk"
    "sed:sed"
    "install:coreutils"
    "bsdtar:libarchive"
    "patch:patch"
    "gpg:gnupg"
    "python3:python"
    "sudo:sudo"
  )
  local dep
  local command_name
  local package_hint

  for dep in "${deps[@]}"; do
    command_name="${dep%%:*}"
    package_hint="${dep#*:}"
    require_command "$command_name" "$package_hint"
  done
}

prepare_workdirs() {
  mkdir -p "$OUT_DIR"
  cleanup_safe_build_root
  mkdir -p "$STAGE_DIR" "$ARCHISO_WORK_DIR"
  mkdir -p "$LOCAL_REPO_DIR"
  mkdir -p "$AUR_BUILD_ROOT" "$AUR_PKGDEST"
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
      warn "Could not import PGP key ${key} for ${package_name}; build may require the browser-package fallback."
    fi
  done
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
    log "Patching AUR calamares PKGBUILD to keep packagechooser modules enabled and apply KeskOS UI polish..."
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

  find "$AUR_PKGDEST" -maxdepth 1 -type f -name "${package_name}-*.pkg.tar.*" -exec cp -f {} "$LOCAL_REPO_DIR/" \;
}

refresh_local_repo() {
  log "Refreshing the local pacman repository..."
  rm -f "${LOCAL_REPO_DIR}"/keskos-local.db* "${LOCAL_REPO_DIR}"/keskos-local.files*
  repo-add "${LOCAL_REPO_DIR}/keskos-local.db.tar.gz" "${LOCAL_REPO_DIR}"/*.pkg.tar.*
}

generate_pacman_conf() {
  local local_repo_uri=""
  log "Generating a pacman.conf that points at the local Calamares repository..."
  local_repo_uri="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve().as_uri())' "${LOCAL_REPO_DIR}")"
  sed "s|__KESKOS_LOCAL_REPO_URI__|${local_repo_uri}|g" \
    "${REPO_ROOT}/pacman.conf" >"${GENERATED_PACMAN_CONF}"
}

stage_profile_basics() {
  log "Staging the Archiso profile..."
  cp -a "${REPO_ROOT}/airootfs" "${STAGE_DIR}/"
  cp -a "${REPO_ROOT}/grub" "${STAGE_DIR}/"
  cp -a "${REPO_ROOT}/syslinux" "${STAGE_DIR}/"
  cp -a "${REPO_ROOT}/efiboot" "${STAGE_DIR}/"
  install -m 644 "${REPO_ROOT}/profiledef.sh" "${STAGE_DIR}/profiledef.sh"
  install -m 644 "${REPO_ROOT}/packages.x86_64" "${STAGE_DIR}/packages.x86_64"
}

stage_source_tree() {
  local source_root="${STAGE_DIR}/airootfs/usr/local/share/keskos/source"
  rm -rf "$source_root"
  mkdir -p "$source_root"

  cp -a "${REPO_ROOT}/assets" "$source_root/"
  cp -a "${REPO_ROOT}/calamares" "$source_root/"
  cp -a "${REPO_ROOT}/configs" "$source_root/"
  cp -a "${REPO_ROOT}/desktop" "$source_root/"
  cp -a "${REPO_ROOT}/browser-home" "$source_root/"
  cp -a "${REPO_ROOT}/docs" "$source_root/"
  install -m 644 "${REPO_ROOT}/assets/spinner.png" "$source_root/spinner.png"
  install -m 644 "${REPO_ROOT}/assets/kesk_os_logo_text.png" "$source_root/kesk_os_logo_text.png"
  install -m 644 "${REPO_ROOT}/assets/kesk_os_logo-removebg.png" "$source_root/kesk_os_logo-removebg.png"
}

stage_live_system_assets() {
  local root="${STAGE_DIR}/airootfs"

  rm -rf \
    "${root}/usr/share/keskos/browser-home" \
    "${root}/usr/share/keskos/startpage" \
    "${root}/usr/share/calamares/branding/keskos" \
    "${root}/etc/calamares/modules"

  mkdir -p \
    "${root}/usr/bin" \
    "${root}/usr/share/konsole" \
    "${root}/usr/share/color-schemes" \
    "${root}/usr/share/icons/hicolor/48x48/apps" \
    "${root}/usr/share/icons/hicolor/64x64/apps" \
    "${root}/usr/share/icons/hicolor/128x128/apps" \
    "${root}/usr/share/plasma/desktoptheme" \
    "${root}/usr/share/aurorae/themes" \
    "${root}/usr/share/kwin/decorations" \
    "${root}/usr/share/backgrounds/keskos" \
    "${root}/usr/share/plasma/plasmoids" \
    "${root}/usr/share/plasma/layout-templates" \
    "${root}/usr/share/plasma/look-and-feel/com.keskos.desktop" \
    "${root}/usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen/assets" \
    "${root}/usr/share/sddm/themes/keskos/assets" \
    "${root}/usr/share/keskos/browser-home" \
    "${root}/usr/share/keskos/panel-icons" \
    "${root}/usr/share/keskos/startpage" \
    "${root}/usr/share/calamares/branding/keskos" \
    "${root}/etc/calamares/modules"

  install -m 644 "${REPO_ROOT}/configs/konsole/KeskOS.colorscheme" "${root}/usr/share/konsole/KeskOS.colorscheme"
  install -m 644 "${REPO_ROOT}/configs/konsole/KeskOS.profile" "${root}/usr/share/konsole/KeskOS.profile"
  install -m 644 "${REPO_ROOT}/configs/kde/keskos.colors" "${root}/usr/share/color-schemes/KESKOS.colors"
  cp -a "${REPO_ROOT}/configs/plasma/desktoptheme/keskos-shell" "${root}/usr/share/plasma/desktoptheme/"
  cp -a "${REPO_ROOT}/configs/aurorae/themes/KeskOS-SPLIT" "${root}/usr/share/aurorae/themes/"
  cp -a "${REPO_ROOT}/configs/kwin/decorations/kwin4_decoration_qml_keskos_split" "${root}/usr/share/kwin/decorations/"

  install -m 644 "${REPO_ROOT}/assets/wallpaper.jpg" "${root}/usr/share/backgrounds/keskos/wallpaper.jpg"
  install -m 644 "${REPO_ROOT}/assets/wallpaper.svg" "${root}/usr/share/backgrounds/keskos/wallpaper.svg"
  install -m 644 "${REPO_ROOT}/assets/wallpaper-1920x1080.png" "${root}/usr/share/backgrounds/keskos/wallpaper-1920x1080.png"
  install -m 644 "${REPO_ROOT}/assets/wallpaper-2560x1440.png" "${root}/usr/share/backgrounds/keskos/wallpaper-2560x1440.png"
  install -m 644 "${REPO_ROOT}/assets/wallpaper-4096x2160.png" "${root}/usr/share/backgrounds/keskos/wallpaper-4096x2160.png"
  install -m 644 "${REPO_ROOT}/assets/kesk_os_logo_text.png" "${root}/usr/share/backgrounds/keskos/kesk_os_logo_text.png"

  install -m 644 "${REPO_ROOT}/assets/icons/hicolor/48x48/apps/keskos-launcher.png" "${root}/usr/share/icons/hicolor/48x48/apps/keskos-launcher.png"
  install -m 644 "${REPO_ROOT}/assets/icons/hicolor/64x64/apps/keskos-launcher.png" "${root}/usr/share/icons/hicolor/64x64/apps/keskos-launcher.png"
  install -m 644 "${REPO_ROOT}/assets/icons/hicolor/128x128/apps/keskos-launcher.png" "${root}/usr/share/icons/hicolor/128x128/apps/keskos-launcher.png"
  install -m 644 "${REPO_ROOT}/assets/panel-icons/browser.svg" "${root}/usr/share/keskos/panel-icons/browser.svg"
  install -m 644 "${REPO_ROOT}/assets/panel-icons/folder.svg" "${root}/usr/share/keskos/panel-icons/folder.svg"
  install -m 644 "${REPO_ROOT}/assets/panel-icons/settings.svg" "${root}/usr/share/keskos/panel-icons/settings.svg"
  install -m 644 "${REPO_ROOT}/assets/panel-icons/terminal.svg" "${root}/usr/share/keskos/panel-icons/terminal.svg"
  cp -a "${REPO_ROOT}/configs/plasmoids/org.kde.plasma.simplekickoff" "${root}/usr/share/plasma/plasmoids/"
  cp -a "${REPO_ROOT}/configs/plasmoids/com.keskos.workspaceswitcher" "${root}/usr/share/plasma/plasmoids/"
  cp -a "${REPO_ROOT}/configs/plasma/layout-templates/org.keskos.plasma.defaultPanel" "${root}/usr/share/plasma/layout-templates/"
  cp -a "${REPO_ROOT}/configs/look-and-feel/com.keskos.desktop/." "${root}/usr/share/plasma/look-and-feel/com.keskos.desktop/"
  install -m 644 "${REPO_ROOT}/configs/look-and-feel/com.keskos.desktop/contents/lockscreen/assets/background.png" "${root}/usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen/assets/background.png"
  install -m 644 "${REPO_ROOT}/configs/look-and-feel/com.keskos.desktop/contents/lockscreen/assets/logo.png" "${root}/usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen/assets/logo.png"

  install -m 644 "${REPO_ROOT}/configs/sddm/keskos/Main.qml" "${root}/usr/share/sddm/themes/keskos/Main.qml"
  install -m 644 "${REPO_ROOT}/configs/sddm/keskos/metadata.desktop" "${root}/usr/share/sddm/themes/keskos/metadata.desktop"
  install -m 644 "${REPO_ROOT}/configs/sddm/keskos/theme.conf" "${root}/usr/share/sddm/themes/keskos/theme.conf"
  install -m 644 "${REPO_ROOT}/assets/wallpaper-2560x1440.png" "${root}/usr/share/sddm/themes/keskos/assets/background.png"
  install -m 644 "${REPO_ROOT}/assets/kesk_os_logo_text.png" "${root}/usr/share/sddm/themes/keskos/assets/logo.png"

  cp -a "${REPO_ROOT}/browser-home/." "${root}/usr/share/keskos/browser-home/"
  cp -a "${REPO_ROOT}/browser-home/." "${root}/usr/share/keskos/startpage/"

  install -m 644 "${REPO_ROOT}/calamares/settings.conf" "${root}/etc/calamares/settings.conf"
  cp -a "${REPO_ROOT}/calamares/modules/." "${root}/etc/calamares/modules/"
  cp -a "${REPO_ROOT}/calamares/branding/keskos/." "${root}/usr/share/calamares/branding/keskos/"
}

stage_application_entries() {
  local root="${STAGE_DIR}/airootfs"
  mkdir -p "${root}/usr/share/applications" "${root}/etc/skel/Desktop"

  cp -a "${REPO_ROOT}/desktop/." "${root}/usr/share/applications/"
  install -m 644 "${REPO_ROOT}/airootfs/usr/share/applications/install-keskos.desktop" "${root}/usr/share/applications/install-keskos.desktop"
  install -m 755 "${REPO_ROOT}/airootfs/etc/skel/Desktop/Install KeskOS.desktop" "${root}/etc/skel/Desktop/Install KeskOS.desktop"
}

stage_boot_branding() {
  log "Adjusting the profile version metadata..."
  sed -i "s/__KESKOS_ISO_VERSION__/${ISO_VERSION}/g" "${STAGE_DIR}/profiledef.sh"
}

run_mkarchiso() {
  log "Building the KeskOS ISO with mkarchiso..."
  sudo mkarchiso \
    -v \
    -C "${GENERATED_PACMAN_CONF}" \
    -w "${ARCHISO_WORK_DIR}" \
    -o "${OUT_DIR}" \
    "${STAGE_DIR}"
  restore_build_root_ownership
}

main() {
  check_arch_host
  check_dependencies
  if (( EUID == 0 )); then
    fail "Run build.sh as a regular user. The script will call sudo only for mkarchiso."
  fi

  prepare_workdirs

  for package_name in "${AUR_PACKAGES[@]}"; do
    build_aur_package "$package_name"
  done

  refresh_local_repo
  generate_pacman_conf
  stage_profile_basics
  stage_source_tree
  stage_live_system_assets
  stage_application_entries
  stage_boot_branding
  run_mkarchiso

  log "KeskOS ISO build complete."
  log "Output directory: ${OUT_DIR}"
}

main "$@"
