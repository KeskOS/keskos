#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
SOURCE_DIR="${REPO_ROOT}/configs/plasmoids/org.kde.plasma.simplekickoff"
TARGET_DIR="${HOME}/.local/share/plasma/plasmoids/org.kde.plasma.simplekickoff"
ICON_ROOT="${HOME}/.local/share/icons/hicolor"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${HOME}/.local/share/plasma/plasmoids/org.kde.plasma.simplekickoff.backup.${TIMESTAMP}"

if [[ ! -d "${SOURCE_DIR}" ]]; then
  printf 'Missing source plasmoid: %s\n' "${SOURCE_DIR}" >&2
  exit 1
fi

if [[ -d "${TARGET_DIR}" ]]; then
  cp -a "${TARGET_DIR}" "${BACKUP_DIR}"
  printf 'Backup created at %s\n' "${BACKUP_DIR}"
fi

rm -rf "${TARGET_DIR}"
mkdir -p "$(dirname "${TARGET_DIR}")"
cp -a "${SOURCE_DIR}" "${TARGET_DIR}"

mkdir -p \
  "${ICON_ROOT}/48x48/apps" \
  "${ICON_ROOT}/64x64/apps" \
  "${ICON_ROOT}/128x128/apps"

install -m 644 "${REPO_ROOT}/assets/icons/hicolor/48x48/apps/keskos-launcher.png" "${ICON_ROOT}/48x48/apps/keskos-launcher.png"
install -m 644 "${REPO_ROOT}/assets/icons/hicolor/64x64/apps/keskos-launcher.png" "${ICON_ROOT}/64x64/apps/keskos-launcher.png"
install -m 644 "${REPO_ROOT}/assets/icons/hicolor/128x128/apps/keskos-launcher.png" "${ICON_ROOT}/128x128/apps/keskos-launcher.png"
rm -f "${ICON_ROOT}/scalable/apps/keskos-launcher.svg"

gtk-update-icon-cache "${ICON_ROOT}" || true
kbuildsycoca6 --noincremental || true
rm -rf "${HOME}/.cache/plasmashell/qmlcache" "${HOME}"/.cache/plasma*
kquitapp6 plasmashell || killall plasmashell || true
kstart6 plasmashell

printf 'Installed patched SimpleKickoff to %s\n' "${TARGET_DIR}"
