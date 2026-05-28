#!/usr/bin/env bash
set -euo pipefail

echo "[keskos-live] configuring the live image..."

ln -sf /usr/share/zoneinfo/UTC /etc/localtime

if ! id -u liveuser >/dev/null 2>&1; then
  useradd -m -G wheel,audio,video,storage,network -s /bin/bash liveuser
fi

passwd -d liveuser >/dev/null 2>&1 || true

install -d -m 0750 /etc/sudoers.d
cat >/etc/sudoers.d/10-liveuser <<'EOF'
liveuser ALL=(ALL) NOPASSWD: ALL
EOF
chmod 0440 /etc/sudoers.d/10-liveuser

ensure_keskos_repo_config() {
  mkdir -p /etc/pacman.d

  if [[ ! -s /etc/pacman.d/mirrorlist ]] || ! grep -Eq '^[[:space:]]*Server[[:space:]]*=' /etc/pacman.d/mirrorlist; then
    cat >/etc/pacman.d/mirrorlist <<'EOF'
## KeskOS fallback Arch Linux mirrorlist
Server = https://geo.mirror.pkgbuild.com/$repo/os/$arch
EOF
  fi

  if [[ ! -f /etc/pacman.d/keskos.conf ]]; then
    cat >/etc/pacman.d/keskos.conf <<'EOF'
[keskos]
# TODO: switch this to `SigLevel = Required DatabaseOptional` once
# `keskos-keyring` is published and the repo server signs packages + metadata.
SigLevel = Optional TrustAll
Include = /etc/pacman.d/keskos-mirrorlist
EOF
  fi

  cat >/etc/pacman.conf <<'EOF'
[options]
HoldPkg = pacman glibc
Architecture = auto
CheckSpace
ParallelDownloads = 5
SigLevel = Required DatabaseOptional
LocalFileSigLevel = Optional

Include = /etc/pacman.d/keskos.conf

[core]
Include = /etc/pacman.d/mirrorlist

[extra]
Include = /etc/pacman.d/mirrorlist

[multilib]
Include = /etc/pacman.d/mirrorlist
EOF
}

find_lockscreen_qml() {
  local candidate=""

  for candidate in \
    /usr/share/plasma/look-and-feel/com.keskos.desktop/contents/lockscreen/LockScreen.qml \
    /usr/share/keskos/source/configs/look-and-feel/com.keskos.desktop/contents/lockscreen/LockScreen.qml \
    /usr/local/share/keskos/source/configs/look-and-feel/com.keskos.desktop/contents/lockscreen/LockScreen.qml
  do
    [[ -f "$candidate" ]] || continue
    printf '%s\n' "$candidate"
    return 0
  done

  return 1
}

cp -a /etc/skel/. /home/liveuser/
chown -R liveuser:liveuser /home/liveuser

ensure_keskos_repo_config

install -d -m 0755 /usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen
if lockscreen_qml="$(find_lockscreen_qml)"; then
  install -m 0644 \
    "$lockscreen_qml" \
    /usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen/LockScreen.qml
fi

if [[ -f /usr/bin/kesk ]]; then
  chmod 0755 /usr/bin/kesk
fi

if [[ -f /usr/bin/kesk-apply-theme ]]; then
  chmod 0755 /usr/bin/kesk-apply-theme
fi

if [[ -f /usr/bin/kesk-theme-status ]]; then
  chmod 0755 /usr/bin/kesk-theme-status
fi

if [[ -f /usr/bin/kesk-hide-kcms ]]; then
  chmod 0755 /usr/bin/kesk-hide-kcms
fi

if [[ -f /usr/bin/kesk-restore-kcms ]]; then
  chmod 0755 /usr/bin/kesk-restore-kcms
fi

if [[ -f /usr/bin/kesk-list-kcms ]]; then
  chmod 0755 /usr/bin/kesk-list-kcms
fi

if [[ -f /usr/lib/kesk/kesk-settings-helper ]]; then
  chmod 0755 /usr/lib/kesk/kesk-settings-helper
fi

if [[ -f /usr/lib/kesk/commands/upgrade ]]; then
  chmod 0755 /usr/lib/kesk/commands/upgrade
fi

if [[ -f /usr/lib/kesk/commands/doctor ]]; then
  chmod 0755 /usr/lib/kesk/commands/doctor
fi

if [[ -f /usr/lib/kesk/commands/repair ]]; then
  chmod 0755 /usr/lib/kesk/commands/repair
fi

if [[ -f /usr/lib/kesk/commands/settings ]]; then
  chmod 0755 /usr/lib/kesk/commands/settings
fi

if [[ -f /usr/lib/kesk/commands/welcome ]]; then
  chmod 0755 /usr/lib/kesk/commands/welcome
fi

if [[ -f /home/liveuser/Desktop/Install\ KeskOS.desktop ]]; then
  chmod +x /home/liveuser/Desktop/Install\ KeskOS.desktop
fi

systemctl enable NetworkManager.service
systemctl enable sddm.service
systemctl enable systemd-resolved.service
systemctl enable qemu-guest-agent.service || true
systemctl set-default graphical.target

if [[ -x /usr/bin/kesk-hide-kcms ]]; then
  /usr/bin/kesk-hide-kcms --system --quiet || true
fi

if command -v kcmshell6 >/dev/null 2>&1; then
  install -d -m 0755 /usr/share/kesk/settings
  kcmshell6 --list >/usr/share/kesk/settings/kcm-default-list.txt 2>/dev/null || true
elif command -v kcmshell5 >/dev/null 2>&1; then
  install -d -m 0755 /usr/share/kesk/settings
  kcmshell5 --list >/usr/share/kesk/settings/kcm-default-list.txt 2>/dev/null || true
fi

TARGET_USER=liveuser /usr/local/bin/keskos-configure-user --offline --force || true

echo "[keskos-live] live image customization complete."
