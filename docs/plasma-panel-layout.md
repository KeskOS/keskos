# Plasma Panel Layout

KeskOS ships a branded Plasma bottom panel instead of relying on the stock KDE default panel.

## What the KeskOS Default Panel Contains

The active branded panel uses:

- the patched `Kesk Kickoff` launcher
- `org.kde.plasma.icontasks` with pinned launchers
- the KeskOS workspace switcher

Pinned launchers come from the task manager defaults:

- Konsole
- Dolphin
- preferred browser
- System Settings

These pins use KeskOS desktop entry wrappers so the panel keeps the intended branded icons:

- `desktop/keskos-terminal.desktop`
- `desktop/keskos-files.desktop`
- `desktop/keskos-browser.desktop`
- `desktop/keskos-settings.desktop`

The workspace switcher shows:

- `1`
- `2`
- `3`
- `4`

## Active Launcher Note

The current working KeskOS launcher widget in this tree is:

- `org.kde.plasma.simplekickoff`

It is patched and branded as:

- `Kesk Kickoff`

KDE native launcher alternatives still remain available through:

- `Show Alternatives...`

## Layout Template Path

The reusable Plasma layout template is installed to:

- `/usr/share/plasma/layout-templates/org.keskos.plasma.defaultPanel/`

Repo source path:

- `configs/plasma/layout-templates/org.keskos.plasma.defaultPanel/`

## Runtime Panel Script

Fresh users and panel repairs still use the runtime panel script:

- `configs/plasma/keskos-bottom-panel.js`

That script is applied by:

- `airootfs/usr/local/bin/keskos-configure-user`

This is how fresh logins get the branded panel automatically.

## Reset Command

Use:

```bash
keskos-reset-panel
```

What it does:

1. Backs up current Plasma panel-related config
2. Reapplies the KeskOS managed panel
3. Reloads `plasmashell`

Backup path:

- `~/.config/keskos/backups/plasma-panel-YYYYMMDD-HHMMSS/`

## Manual Application

Depending on Plasma version, the template may appear from panel edit mode under panel/layout options as:

- `KeskOS Default Panel`

If you want the supported scripted path instead, use:

```bash
keskos-reset-panel
```

## How It Differs From KDE Default Panel

KeskOS changes the panel to:

- use the branded Kesk launcher first
- seed pinned app launchers through the task manager
- use the KeskOS workspace switcher instead of the stock pager when available
- keep the bottom panel minimal without the default right-side tray/clock cluster
- avoid the stock bright KDE launcher/panel feel

## Restore From Backup

If you want to restore a previous panel state manually:

1. copy the backed up files from:
   - `~/.config/keskos/backups/plasma-panel-YYYYMMDD-HHMMSS/`
2. restore them into:
   - `~/.config/`
3. restart Plasma:

```bash
systemctl --user restart plasma-plasmashell.service
```

## Related Files

- `configs/plasma/keskos-bottom-panel.js`
- `configs/plasma/layout-templates/org.keskos.plasma.defaultPanel/`
- `airootfs/usr/bin/keskos-reset-panel`
- `airootfs/usr/local/bin/keskos-configure-user`
- `configs/plasmoids/org.kde.plasma.simplekickoff/`
