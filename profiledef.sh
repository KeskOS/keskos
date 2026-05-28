#!/usr/bin/env bash
# shellcheck disable=SC2034

iso_name="keskos"
iso_label="KESKOS_$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y%m)"
iso_publisher="memegeko <https://github.com/memegeko/keskos>"
iso_application="KeskOS live and installer environment"
iso_version="__KESKOS_ISO_VERSION__"
install_dir="keskos"
buildmodes=('iso')
bootmodes=('bios.syslinux' 'uefi.grub')
pacman_conf="pacman.conf"
airootfs_image_type="erofs"
airootfs_image_tool_options=('-zlzma,109' -E 'ztailpacking')
bootstrap_tarball_compression=(zstd -c -T0 -19)
file_permissions=(
  ["/etc/shadow"]="0:0:400"
  ["/root/customize_airootfs.sh"]="0:0:755"
  ["/usr/local/bin/"]="0:0:755"
  ["/etc/skel/Desktop/"]="0:0:755"
)
