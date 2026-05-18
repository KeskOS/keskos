# Kesk Settings

This control center work currently ships as part of the `beta-development` branch.

`kesk settings` is now the main entrypoint for KeskOS settings and maintenance.

Behavior:

- in a graphical session, `kesk settings` launches the `kesk-settings` Qt GUI
- without `DISPLAY` or `WAYLAND_DISPLAY`, it falls back to the terminal control center
- `kesk settings --tui` forces the terminal fallback

The GUI and TUI both route maintenance work through the existing KeskOS tools:

- `kesk upgrade`
- `kesk doctor`
- `kesk repair`

There is still no separate `kesk theme` command. Theme and visual identity recovery stay inside `kesk repair`.

## Running It

From a terminal:

```bash
kesk settings
```

Force the terminal fallback:

```bash
kesk settings --tui
```

Launch the GUI directly:

```bash
kesk-settings
```

## Start Menu Launcher

KeskOS ships a KDE launcher entry at:

- `/usr/share/applications/kesk-settings.desktop`

It launches:

```bash
kesk-settings
```

The branded pinned desktop entry `keskos-settings.desktop` is still kept for panel compatibility, but it is hidden from the normal app menu and points to the same GUI control center.

## What It Does

Kesk Settings is the KeskOS control hub.

The GUI provides these pages:

- `Dashboard`
- `Updates`
- `System Doctor`
- `Repair`
- `Appearance`
- `Desktop`
- `Boot & Login`
- `Logs`
- `About`

The terminal fallback provides the simpler menu-driven launcher:

1. `System Upgrade`
2. `System Doctor`
3. `Repair Console`
4. `About KeskOS`
5. `Open Logs Directory`
6. `Open Backups Directory`
7. `Open Documentation`
8. `Exit`

## Relationship Between GUI And CLI

The GUI does not replace the existing CLI tools.

- `kesk upgrade` remains the updater backend
- `kesk doctor` remains the doctor backend
- `kesk repair` remains the repair and theme backend

The GUI uses JSON and direct-action modes where possible, and launches the existing terminal tooling in Konsole when a privileged or interactive action is safer there.

That keeps one shared maintenance flow for both desktop users and terminal users.

## About KeskOS

The `About` page and terminal about view show:

- KeskOS version/build when available
- kernel version
- desktop session
- current desktop identifier
- Plasma version when available
- Qt version when available
- active user
- hostname
- uptime
- package count when `pacman` is available
- current shell
- logs directory path
- backups directory path

## Logs

Kesk Settings writes logs to:

```text
~/.local/state/kesk/logs/
```

Typical files:

- `settings-YYYYMMDD-HHMMSS.log` for the TUI fallback
- `gui-YYYYMMDD-HHMMSS.log` for the Qt GUI

Logs include:

- app/tool start time
- selected pages and menu options
- commands launched
- exit codes
- warnings and errors

Passwords and secrets are not logged.

## Backups

Kesk Settings uses the standard KeskOS backup location:

```text
~/.local/state/kesk/backups/
```

The GUI can open that folder and list backup directories, but it does not auto-restore them yet.

## What It Does Not Do Yet

For this stage, Kesk Settings still does not:

- add `kesk welcome`
- enable first-boot or autostart personalization flows
- create a separate theme console
- replace all KDE settings modules
- edit browser profiles directly from a dedicated browser manager
- install optional packages

Theme, panel, SDDM, Plymouth, and other branded desktop recovery work should still be run through `Repair -> kesk repair`.
