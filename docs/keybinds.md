# KeskOS Keybinds

This file documents the keyboard shortcuts that are actively written or overridden by the KeskOS setup scripts.

## Main Shortcut Script

The main global shortcut configuration happens in:

- [airootfs/usr/local/bin/keskos-configure-user](/home/geko/Documents/scripts/keskos/airootfs/usr/local/bin/keskos-configure-user)

Inside that script, the `configure_shortcuts()` function writes to:

- `~/.config/kwinrc`
- `~/.config/kglobalshortcutsrc`

## Global Shortcuts Written By `configure_shortcuts()`

### Modifier-only launcher binding

Written to:

- `kwinrc` → `[ModifierOnlyShortcuts]`

Behavior:

- `Meta`
  - opens the Plasma application launcher

Technical target:

- `org.kde.plasmashell,/PlasmaShell,org.kde.PlasmaShell,activateLauncherMenu`

### Plasma launcher shortcut

Written to:

- `kglobalshortcutsrc` → `[plasmashell]`

Shortcut:

- `Alt+F1` → `Activate Application Launcher`

### KWin shortcuts

Written to:

- `kglobalshortcutsrc` → `[kwin]`

Shortcuts:

- `Edit Tiles` → `none`
- `Overview` → `none`
- `Walk Through Windows (Reverse)` → `Alt+Shift+Tab`

## Application Launch Shortcuts Written By `configure_shortcuts()`

These are written into `kglobalshortcutsrc` for both:

- `[services/<desktop-file>]`
- `[<desktop-file>]`

### Core app shortcuts

- `Meta+T`
- `Meta+Return`
  - both launch `KESKOS Terminal`
  - desktop file: `keskos-terminal.desktop`

- `Meta+N` → `KESKOS Files`
  - desktop file: `keskos-files.desktop`

- `Meta+B` → `KESKOS Browser`
  - desktop file: `keskos-browser.desktop`

## Matching Desktop Entry Defaults

These desktop files also declare the same defaults through `X-KDE-Shortcuts=`:

- [desktop/keskos-terminal.desktop](/home/geko/Documents/scripts/keskos/desktop/keskos-terminal.desktop)
- [desktop/keskos-files.desktop](/home/geko/Documents/scripts/keskos/desktop/keskos-files.desktop)
- [desktop/keskos-browser.desktop](/home/geko/Documents/scripts/keskos/desktop/keskos-browser.desktop)

## Other Shortcut Code In The Repo

These are not part of the global KDE shortcut setup above, but they do define local window shortcuts:

### First-run setup window

Defined in:

- [airootfs/usr/lib/keskos-first-run/main.py](/home/geko/Documents/scripts/keskos/airootfs/usr/lib/keskos-first-run/main.py)

Window-local shortcuts:

- `Esc` → show blocked-close warning
- `Ctrl+Shift+D` → toggle debug panel

These are Qt window shortcuts, not KDE global shortcuts.

## Summary

The script currently changes or enforces these keys:

- `Meta`
- `Alt+F1`
- `Alt+Shift+Tab`
- `Meta+T`
- `Meta+Return`
- `Meta+N`
- `Meta+B`

And it disables:

- `Edit Tiles`
- `Overview`
