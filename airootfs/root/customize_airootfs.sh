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

cp -a /etc/skel/. /home/liveuser/
chown -R liveuser:liveuser /home/liveuser

install -d -m 0755 /usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen
install -m 0644 \
  /usr/local/share/keskos/source/configs/look-and-feel/com.keskos.desktop/contents/lockscreen/LockScreen.qml \
  /usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen/LockScreen.qml

if [[ -f /usr/bin/kesk ]]; then
  chmod 0755 /usr/bin/kesk
fi

if [[ -f /usr/bin/kesk-settings ]]; then
  chmod 0755 /usr/bin/kesk-settings
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

if [[ -f /home/liveuser/Desktop/Install\ KeskOS.desktop ]]; then
  chmod +x /home/liveuser/Desktop/Install\ KeskOS.desktop
fi

systemctl enable NetworkManager.service
systemctl enable sddm.service
systemctl enable systemd-resolved.service
systemctl enable qemu-guest-agent.service || true
systemctl set-default graphical.target

TARGET_USER=liveuser /usr/local/bin/keskos-configure-user --offline --force || true

echo "[keskos-live] live image customization complete."
