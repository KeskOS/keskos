# Plymouth Boot Splash

KeskOS uses the `keskos-plymouth` package for the graphical boot splash on installed systems.

## What It Shows

The active theme is named `keskos` and is installed to:

```txt
/usr/share/plymouth/themes/keskos/
```

The splash is intentionally quiet and styled like a black/orange BIOS terminal. It shows static firmware/POST text, the KeskOS logo, a framed boot log panel, a blinking cursor, and footer status text.

Raw kernel and systemd logs are not shown in the splash. Curated milestones are sent with:

```bash
plymouth display-message --text="MESSAGE"
```

## Package Files

The package installs:

```txt
/usr/share/plymouth/themes/keskos/keskos.plymouth
/usr/share/plymouth/themes/keskos/keskos.script
/usr/share/plymouth/themes/keskos/kesk_os_logo_text.png
/usr/bin/keskos-plymouth-message
/usr/bin/keskos-plymouth-boot-status
/usr/bin/keskos-plymouth-wait
/usr/lib/systemd/system/keskos-plymouth-boot-status.service
/usr/lib/systemd/system/keskos-plymouth-min-duration.service
/etc/keskos/boot.conf
```


## Live ISO Wiring

The live ISO also starts Plymouth before the desktop loads. This is separate from the installed-system Calamares bootloader configuration.

Live ISO requirements:

```txt
packages.x86_64 includes plymouth and keskos-plymouth
airootfs/etc/mkinitcpio.conf.d/archiso.conf includes kms and plymouth before archiso
airootfs/etc/plymouth/plymouthd.conf selects Theme=keskos
ISO boot entries pass quiet splash loglevel=3 rd.udev.log_level=3 vt.global_cursor_default=0 systemd.show_status=false udev.log_priority=3
airootfs enables keskos-plymouth-boot-status.service and keskos-plymouth-min-duration.service for graphical.target
```

This makes the live USB show the same black/orange KeskOS Plymouth splash before SDDM starts.

## Installer Wiring

The installer config sets GRUB kernel parameters for a quiet splash:

```txt
quiet splash loglevel=3 rd.udev.log_level=3 vt.global_cursor_default=0 systemd.show_status=false udev.log_priority=3
```

The installed system mkinitcpio hooks include `kms` before `plymouth`, and `plymouth` before `block` and `filesystems`:

```txt
HOOKS=(base udev autodetect microcode modconf kms keyboard keymap consolefont plymouth block filesystems fsck)
```

During postinstall, the installer selects the theme and attempts to refresh initramfs:

```bash
plymouth-set-default-theme -R keskos
```

If that command is unavailable or fails, installation continues and the next mkinitcpio refresh can pick up the theme.

## Tuning Duration

The minimum visible splash duration is configured in:

```txt
/etc/keskos/boot.conf
```

Default:

```bash
KESKOS_PLYMOUTH_MIN_SECONDS=6
```

## Manual Test

On an installed system:

```bash
sudo plymouth-set-default-theme -R keskos
systemctl status keskos-plymouth-boot-status.service
systemctl status keskos-plymouth-min-duration.service
```

To send a test message while Plymouth is active:

```bash
sudo keskos-plymouth-message "[00:00:04.417] INIT    User session pending ..."
```

## Troubleshooting

If the splash does not appear, verify:

- `plymouth` and `keskos-plymouth` are installed.
- `plymouth-set-default-theme` reports `keskos`.
- `/etc/mkinitcpio.conf` contains the `plymouth` hook before `block`.
- GRUB has `quiet splash` in the generated entry.
- Initramfs was rebuilt after the theme was installed.

Static boot graphics are package-controlled. Updating the splash design requires publishing a new `keskos-plymouth` package and rebuilding initramfs.
