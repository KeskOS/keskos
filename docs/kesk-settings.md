# Kesk Settings

`kesk settings` is the dedicated KeskOS settings application.

It is a KDE/Qt settings app, not a dashboard and not a command launcher. Its job is to manage user-visible system settings from one place:

- KDE Plasma user settings where a safe user-level apply path exists
- KeskOS-specific settings and preferences

It does not try to replace every KDE module, and it does not embed unrelated operational tools.

## What It Configures

Kesk Settings currently provides these categories:

- `Appearance`
- `Desktop`
- `Panel & Launcher`
- `Window Behavior`
- `Input`
- `Display`
- `Sound`
- `Network`
- `Power`
- `Users`
- `Default Apps`
- `Updates`
- `Boot & Login`
- `KeskOS`
- `About`

Implemented settings include:

- Plasma look and feel, Plasma theme, color scheme, icon theme, cursor theme, font, wallpaper, and window decoration
- virtual desktop count and names
- launcher mode and launcher keybind
- KWin focus policy, border size, compositor flags, snap behavior, and titlebar layout
- keyboard layout and repeat settings
- Night Color toggle
- default audio volume and mute
- Wi-Fi radio toggle and hostname apply when `pkexec` and `hostnamectl` are available
- power profile when `powerprofilesctl` is available
- avatar copy to `~/.face.icon`
- default browser, terminal, file manager, editor, and image viewer
- update policy preferences
- KeskOS accent, CRT/scanline preferences, prompt style, homepage preference, first-run state, and experimental toggles

Some pages also include a small handoff to the matching KDE settings module when the full feature set is better handled by KDE itself.

## What It Does Not Include

Kesk Settings intentionally does not include:

- repair tools
- the package updater UI
- Docker or developer shortcuts
- server/admin tools
- logs/debug dashboards
- package-manager launchers
- terminal launch shortcuts

Those remain separate commands and launchers:

- `kesk upgrade`
- `kesk repair`
- `kesk doctor`

The `Updates` page may offer a small `Open Kesk Upgrade` button, but it does not embed the updater dashboard.

## Running It

From a terminal:

```bash
kesk settings
```

Dry-run backend inspection:

```bash
kesk settings --dry-run
```

Direct GUI launcher:

```bash
kesk-settings
```

If no graphical session is available, `kesk settings` prints:

```text
Kesk Settings requires a graphical session.
```

## Start Menu Launcher

KDE launcher entry:

- `/usr/share/applications/kesk-settings.desktop`

It launches:

```bash
kesk settings
```

The hidden branded compatibility entry `keskos-settings.desktop` points to the same command for panel/menu integrations that still reference it.

## Config Storage

KeskOS-specific settings are stored in:

```text
~/.config/kesk/settings.json
```

This file stores settings such as:

- accent color
- CRT effects
- scanlines
- panel mode
- launcher keybind
- update preferences
- boot/login preferences that are not yet root-applied directly
- default browser preference
- prompt style
- experimental toggles

GUI window state is stored separately in:

```text
~/.config/kesk/settings-gui.ini
```

KDE-native settings continue to live in their normal KDE config files such as:

- `~/.config/kdeglobals`
- `~/.config/kwinrc`
- `~/.config/plasmarc`
- `~/.config/kcminputrc`
- `~/.config/kxkbrc`
- `~/.config/mimeapps.list`

## Backups

Before important settings changes, Kesk Settings creates backups in:

```text
~/.local/state/kesk/settings-backups/
```

Backups are timestamped and grouped by settings area, for example:

- `*-appearance`
- `*-desktop`
- `*-panels`
- `*-windows`
- `*-defaults`
- `*-keskos`

## Difference From Other Kesk Commands

- `kesk settings` changes settings
- `kesk upgrade` handles package, Flatpak, AUR, and firmware updates
- `kesk repair` repairs the KeskOS desktop/theme stack
- `kesk doctor` inspects system health

Kesk Settings is meant to feel like the OS settings app. The operational and maintenance tools stay separate.

## Dry-Run And Debugging

Use:

```bash
kesk settings --dry-run
```

This prints:

- session type
- Plasma version
- Qt version
- detected backend tools
- config paths
- writable config paths

If a setting does not apply as expected:

1. Run `kesk settings --dry-run`
2. Confirm required tools such as `kwriteconfig6`, `lookandfeeltool`, `qdbus6`, `nmcli`, `wpctl`, or `powerprofilesctl`
3. Check the latest GUI/session logs in `~/.local/state/kesk/logs/`
4. Check the newest backup in `~/.local/state/kesk/settings-backups/`

## Known Limitations

- Not every KDE setting is implemented directly yet.
- Display arrangement, scaling, and refresh-rate changes still lean on KDE’s advanced display module.
- System-level boot/login changes are intentionally conservative and currently stored as preferences unless a safe user-level apply path exists.
- Network hostname changes require `pkexec` and `hostnamectl`.
- Audio routing is intentionally minimal; the page focuses on safe default volume and mute.
- The app does not run as root.
