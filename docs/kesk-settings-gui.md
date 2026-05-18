# Kesk Settings GUI

This GUI control center is currently part of the `beta-development` branch.

`kesk-settings` is the main graphical control center for KeskOS.

It is designed to feel like a KeskOS secure console inside a native desktop app rather than a generic KDE settings clone.

## Launching It

From the app menu:

- `Kesk Settings`

From a terminal:

```bash
kesk-settings
```

Router behavior:

```bash
kesk settings
```

- launches the GUI when `DISPLAY` or `WAYLAND_DISPLAY` is available
- falls back to the terminal control center when no graphical session is available
- `kesk settings --tui` forces the terminal fallback

## Relationship To The CLI Tools

The GUI does not replace the terminal maintenance tools.

It uses:

- `kesk upgrade` for update checks and updater actions
- `kesk doctor` for health scans and debug report export
- `kesk repair` for repair actions, theme recovery, and repair reports

This keeps one shared backend path for both normal users and power users.

There is no separate `kesk theme` command. Theme and visual identity repair remain inside `kesk repair`.

## Pages

### Dashboard

Shows lightweight status cards for:

- system state
- update counts
- last doctor health summary
- desktop identity summary

### Updates

Shows:

- pacman, AUR, Flatpak, and firmware availability
- detected update counts
- grouped package/update lists

Buttons:

- `REFRESH`
- `UPGRADE ALL`
- `UPGRADE OFFICIAL`
- `UPGRADE AUR`
- `UPGRADE FLATPAK`
- `UPGRADE FIRMWARE`

Safety:

- the GUI asks for confirmation first
- update actions are launched through the existing CLI updater path
- privileged or interactive update flows are handed off to Konsole
- the page shows log/output information in its console panel

### System Doctor

Shows the read-only health checks from `kesk doctor`:

- package state
- update tools
- failed services
- storage pressure
- KDE/Plasma state
- launcher files
- SDDM theme
- Plymouth theme
- Quickshell/HUD
- browser homepage assets
- reboot recommendation

Buttons:

- `RUN SCAN`
- `EXPORT REPORT`
- `OPEN LAST REPORT`

### Repair

GUI front-end for `kesk repair`.

It exposes:

- safe repair
- panel reset
- launcher repair
- full visual identity repair
- Plasma/colors
- icon theme
- cursor theme
- Konsole profile
- Dolphin config
- GTK/Kvantum styling
- SDDM theme
- Plymouth theme
- Quickshell HUD
- cache rebuild
- repair report export

Safety:

- the GUI confirms before running an action
- action details explain what may change
- SDDM and Plymouth actions are clearly marked as privileged
- user/system backups still come from `kesk repair`

### Appearance

Shows user-level visual status and routes theme work through `kesk repair`.

It can:

- display the current Plasma/icon/cursor/Konsole/GTK/Kvantum status
- reapply the current KeskOS visual identity
- jump to the full repair console

### Desktop

Shows:

- current desktop session
- panel config presence
- launcher file status
- HUD status

Buttons:

- `RESET PANELS`
- `REPAIR LAUNCHER`
- `RESTART PLASMA`
- `RESTART HUD`

### Boot & Login

Shows:

- active SDDM theme
- active Plymouth theme

Buttons:

- `REAPPLY SDDM THEME`
- `REAPPLY PLYMOUTH THEME`
- `OPEN BOOT DOCS`

Safety:

- SDDM affects the login screen
- Plymouth affects the boot splash and may rebuild initramfs
- privileged actions are launched through the existing repair path

### Logs

Shows:

- Kesk logs from `~/.local/state/kesk/logs/`
- backup directories from `~/.local/state/kesk/backups/`

Features:

- filter logs by tool
- preview log contents
- copy selected paths
- open logs or backups folders
- clear logs with confirmation

### About

Shows:

- KeskOS version/build
- kernel
- user
- hostname
- desktop session
- Plasma version
- Qt version
- package count
- logs and backups paths
- project links

## Logs

GUI logs are written to:

```text
~/.local/state/kesk/logs/gui-YYYYMMDD-HHMMSS.log
```

They include:

- app start
- page opens
- commands launched
- warnings and errors

Passwords and secrets are not logged.

## Configuration

GUI preferences are stored in:

```text
~/.config/kesk/settings.conf
```

Current stored values include:

- last opened page
- window size
- whether lightweight dashboard checks should run on startup

No secrets are stored there.

## Actions That May Need Sudo

The following actions can require elevated privileges:

- official package upgrades
- firmware updates
- SDDM theme repair
- Plymouth theme repair

The GUI does not store passwords or invent a custom privilege prompt. When a real terminal or elevated path is safer, it launches the existing CLI flow in Konsole.

## Known Limitations

- the GUI is the new main control center, but the terminal tools remain the canonical maintenance tools
- update actions are still terminal-backed for the safest interactive package-manager behavior
- some visual/boot repair actions depend on whether the required KeskOS assets are actually installed on the target system
- `kesk welcome`, first-boot flows, a browser manager, and optional package installer work are intentionally not part of this app yet
