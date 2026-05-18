# Kesk Repair

This repair console currently ships as part of the `beta-development` branch.

`kesk repair` is the branded KeskOS recovery console for desktop layout, launcher recovery, and full visual-identity repair.

It uses the same black/orange terminal style as `kesk upgrade`, `kesk doctor`, and `kesk settings`, but unlike those tools it can change files after confirmation.

There is intentionally no separate `kesk theme` command. Theme repair lives inside `kesk repair` so the KeskOS toolset stays clean.

## Running It

From a terminal:

```bash
kesk repair
```

Router commands that are also available:

```bash
kesk help
kesk --help
kesk version
kesk doctor
kesk upgrade
kesk settings
```

## Start Menu Launcher

KeskOS ships a KDE launcher entry at:

- `/usr/share/applications/kesk-repair.desktop`

It opens the repair console in Konsole with:

```bash
konsole --hold --workdir ~ -e /usr/bin/kesk repair
```

## What `kesk repair` Does

The repair console is the “fix my KeskOS install” tool.

It can restore or reapply:

- the managed Plasma panel layout
- the Kesk launcher wiring
- the full KeskOS Plasma theme and color chain
- icon and cursor theme defaults
- the KeskOS Konsole profile
- Dolphin defaults when an official template exists
- GTK styling when a matching theme asset exists
- Kvantum styling when a matching theme asset exists
- the SDDM login theme
- the Plymouth boot splash when an official theme exists
- the Quickshell HUD config
- icon, font, and KDE service caches

It does not:

- create a separate theme tool
- remove packages
- run full system upgrades
- delete user data
- remove pacman lock files
- blindly overwrite unrelated configs

## Menu Actions

The repair menu now includes:

1. `Run safe repair`
2. `Reset KDE Plasma panels`
3. `Reset Kesk launcher`
4. `Reapply full KeskOS visual identity`
5. `Reapply Plasma theme/colors`
6. `Reapply icon theme`
7. `Reapply cursor theme`
8. `Reapply Konsole profile`
9. `Reapply Dolphin config`
10. `Reapply GTK/Kvantum styling`
11. `Reapply SDDM login theme`
12. `Reapply Plymouth boot theme`
13. `Repair Quickshell HUD`
14. `Rebuild icon/font cache`
15. `Show current theme status`
16. `Export repair report`
17. `Exit`

## Safe Repair

`Run safe repair` only does low-risk repairs:

- creates missing Kesk state, log, backup, and config directories
- reapplies user-level Plasma theme and color settings when assets exist
- reapplies icon and cursor defaults
- reapplies the Konsole profile
- reapplies Dolphin defaults when a template exists
- reapplies GTK and Kvantum styling when assets exist
- rebuilds icon, font, and KDE caches

Safe repair does not:

- reset panels
- touch SDDM
- touch Plymouth
- touch browser profiles
- change Quickshell autostart

## Full Visual Identity Repair

`Reapply full KeskOS visual identity` runs:

- Plasma theme and color repair
- icon theme repair
- cursor theme repair
- Konsole profile restore
- Dolphin config restore when available
- GTK/Kvantum styling restore
- cache rebuilds

After that it separately asks whether to apply:

- the SDDM login theme
- the Plymouth boot theme

Missing assets are skipped cleanly instead of forcing a separate tool.

## Theme Discovery

The repair console detects themed KeskOS assets from likely install and user paths such as:

- `/usr/share/plasma/desktoptheme/`
- `/usr/share/plasma/look-and-feel/`
- `/usr/share/color-schemes/`
- `/usr/share/icons/`
- `/usr/share/konsole/`
- `/usr/share/sddm/themes/`
- `/usr/share/plymouth/themes/`
- `/usr/share/Kvantum/`
- `/usr/share/themes/`
- `~/.local/share/plasma/desktoptheme/`
- `~/.local/share/plasma/look-and-feel/`
- `~/.local/share/color-schemes/`
- `~/.local/share/icons/`
- `~/.local/share/konsole/`
- `~/.config/Kvantum/`
- `~/.themes/`

It prefers KeskOS-specific names when present, but it can also detect compatible assets whose names contain terms like `kesk`, `keskos`, `amber`, `terminal`, or `split`.

## Show Current Theme Status

`Show current theme status` is a read-only screen inside `kesk repair`.

It shows:

- active look-and-feel package
- active Plasma theme
- active color scheme
- active icon theme
- active cursor theme
- active Konsole profile
- active GTK theme/icon/cursor settings
- active Kvantum theme
- active SDDM theme
- active Plymouth theme
- detected asset paths
- missing theme asset groups

## Config Files That May Be Changed

User-level repair may update files such as:

- `~/.config/kdeglobals`
- `~/.config/kwinrc`
- `~/.config/plasmarc`
- `~/.config/kcminputrc`
- `~/.config/konsolerc`
- `~/.local/share/konsole/KeskOS.profile`
- `~/.local/share/konsole/KeskOS.colorscheme`
- `~/.config/dolphinrc`
- `~/.config/gtk-3.0/settings.ini`
- `~/.config/gtk-4.0/settings.ini`
- `~/.config/Kvantum/kvantum.kvconfig`
- `~/.config/plasma-org.kde.plasma.desktop-appletsrc` when panel reset is used
- `~/.config/quickshell/` when HUD repair is used

System-level repair may update files such as:

- `/etc/sddm.conf`
- `/etc/sddm.conf.d/*.conf`
- `/etc/plymouth/plymouthd.conf`

## Backups

Before changing user config files, `kesk repair` stores targeted backups in:

```text
~/.local/state/kesk/backups/YYYYMMDD-HHMMSS/repair/
```

When a system-level repair touches root-owned files, it stores backups in:

```text
/var/lib/kesk/backups/YYYYMMDD-HHMMSS/repair/
```

Backups are targeted to the files or small directories that the repair action touches.

## Logs

Each run writes a timestamped log to:

```text
~/.local/state/kesk/logs/
```

Repair log format:

```text
repair-YYYYMMDD-HHMMSS.log
```

Logs include:

- start time
- detected theme assets
- selected repair actions
- backups created
- files changed
- commands executed
- exit codes
- warnings and errors
- final status

## Repair Report

`Export repair report` writes:

```text
~/kesk-repair-report.txt
```

The report includes:

- current theme status
- detected theme assets
- selected repair actions
- files backed up
- files changed
- commands run
- command exit codes
- warnings, skipped items, and notes
- the active repair log path

The report does not include secrets.

## Restoring From Backups Manually

Most backups mirror the original relative path under the backup directory.

To restore manually:

1. Copy the backed-up file or directory back into its original location.
2. Restart the affected desktop component if needed.
3. Log out and back in if the visual state does not refresh immediately.

## Actions That Require `sudo`

These actions may ask for system privileges:

- `Reapply SDDM login theme`
- `Reapply Plymouth boot theme`
- any repair that must restore missing system-owned branding assets

## What It Does Not Repair

`kesk repair` does not currently:

- reinstall missing packages
- fix broken pacman databases
- resolve general hardware problems
- restore a Plymouth theme that does not exist anywhere on the system or in the staged build
- create a standalone theme manager

## Relation To `kesk doctor`

Use `kesk doctor` first when you want a read-only health scan.

Use `kesk repair` after that when you want to actually restore the branded KeskOS desktop and theme stack with backups and confirmations.
