# Launcher Switching

KeskOS now ships one primary launcher path:

- `org.kde.plasma.simplekickoff` patched as `Kesk Kickoff`

KDE's native launchers remain available as safe alternatives through Plasma's normal
`Show Alternatives...` flow, but the old Wolfi/Rofi launcher stack is no longer part
of the active ISO install.

The retired launcher stack is archived in:

- `.old_rolfi/`

## Default Behavior

- `Meta` opens the current Plasma launcher
- `Alt+F1` triggers Plasma's standard launcher action
- the bottom panel uses `Kesk Kickoff` by default

Launcher preference order:

1. `org.kde.plasma.simplekickoff`
2. `org.kde.plasma.kicker`
3. `org.kde.plasma.kickoff`

## Switch Command

Use:

```bash
keskos-launcher-switch status
keskos-launcher-switch keskos
keskos-launcher-switch kde
keskos-fix-launcher
```

Behavior:

- `status` prints the current default launcher mode
- `keskos` makes the patched `org.kde.plasma.simplekickoff` the default panel/meta path
- `kde` makes KDE Application Menu / Kicker the default panel/meta path
- `keskos-fix-launcher` repairs existing installs, removes stale launcher state, reapplies the Kesk launcher, and reloads Plasma

## Backups

Before switching, KeskOS writes timestamped backups to:

- `~/.config/keskos/backups/plasma-launcher-before-kde-switch/`

The repair helper writes a direct backup to:

- `~/.config/keskos/backups/plasma-launcher-YYYYMMDD-HHMMSS/`

Typical backed up files:

- `~/.config/kglobalshortcutsrc`
- `~/.config/kwinrc`
- `~/.config/plasma-org.kde.plasma.desktop-appletsrc`
- `~/.config/plasmashellrc`
- `~/.config/keskos/launcher-mode`

## Files And Config Paths

Repo files involved:

- `configs/plasmoids/org.kde.plasma.simplekickoff/`
- `configs/plasma/keskos-bottom-panel.js`
- `scripts/apply-kesk-simplekickoff.sh`
- `desktop/keskos-browser.desktop`
- `desktop/keskos-files.desktop`
- `desktop/keskos-terminal.desktop`
- `airootfs/usr/bin/keskos-launcher-switch`
- `airootfs/usr/bin/keskos-fix-launcher`
- `airootfs/usr/local/bin/keskos-configure-user`

Installed paths involved:

- `/usr/bin/keskos-launcher-switch`
- `/usr/bin/keskos-fix-launcher`
- `/usr/share/plasma/plasmoids/org.kde.plasma.simplekickoff/`
- `~/.config/kglobalshortcutsrc`
- `~/.config/kwinrc`
- `~/.config/plasma-org.kde.plasma.desktop-appletsrc`
- `~/.config/keskos/launcher-mode`

## Favorites

The KDE launcher favorites are preloaded with:

- Konsole
- Dolphin
- the preferred browser
- System Settings

The preferred browser resolves from the current desktop defaults first, then falls
back through KeskOS browser candidates.

## Troubleshooting

If Meta opens the wrong thing:

1. Run `keskos-launcher-switch status`
2. Run `keskos-launcher-switch keskos` or `keskos-launcher-switch kde`
3. Run `keskos-fix-launcher`
4. Restart `plasmashell` if the panel did not refresh cleanly

If the panel shows duplicate launchers:

1. Run `keskos-launcher-switch status`
2. Run `keskos-fix-launcher`
3. Confirm `~/.config/plasma-org.kde.plasma.desktop-appletsrc` only has one managed `keskos-bottom-panel-v1` panel

If the whole panel layout needs to be rebuilt:

```bash
keskos-reset-panel
```

See:

- `docs/plasma-panel-layout.md`

If Plasma needs a manual shell restart:

```bash
systemctl --user restart plasma-plasmashell.service
```

## Switching Back

To restore KDE launcher default:

```bash
keskos-launcher-switch kde
```

To restore the Kesk launcher default:

```bash
keskos-launcher-switch keskos
```
