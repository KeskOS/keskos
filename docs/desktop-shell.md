# Desktop Shell

KeskOS now uses a split shell layout:

- Quickshell renders the top HUD bar.
- KDE Plasma renders the real bottom taskbar.
- KWin and Plasma still provide the desktop session, window management, and virtual desktops.

This keeps the custom top-bar identity while restoring full KDE taskbar behavior for running apps, pinning, and launcher persistence.

## Why Eww Was Removed

Eww is no longer part of the active KeskOS desktop path.

- Login startup launches Quickshell, not Eww.
- `keskos-shell` kills stray `eww` processes before starting Quickshell.
- `keskos-configure-user` disables common user Eww services and removes old Eww autostarts.
- Legacy user config is moved to `~/.config/eww.deprecated-keskos`.

## Shell Layout

Quickshell is responsible for:

- the top bar
- the top-bar power button
- the top-bar CPU, MEM, NET, and POWER dropdown popups
- shell logging and startup supervision

KDE Plasma is responsible for:

- the bottom panel
- the real Icons-Only Task Manager
- pinned and running application handling
- the right-side numbered workspace switcher
- the desktop containment state that Quickshell is layered on top of

## Config Locations

Repo source:

- `configs/quickshell/keskos/`
- `configs/plasma/keskos-bottom-panel.js`
- `configs/plasma/layout-templates/org.keskos.plasma.defaultPanel/`
- `configs/plasmoids/org.kde.plasma.simplekickoff/`
- `docs/launcher-switching.md`
- `docs/plasma-panel-layout.md`

Installed source tree:

- `/usr/local/share/keskos/source/configs/quickshell/keskos/`
- `/usr/local/share/keskos/source/configs/plasma/keskos-bottom-panel.js`

Installed Plasma launcher widget:

- `/usr/share/plasma/plasmoids/org.kde.plasma.simplekickoff/`

Launcher switch helper:

- `/usr/bin/keskos-launcher-switch`
- `/usr/bin/keskos-reset-panel`

Per-user live config:

- `~/.config/quickshell/keskos/`
- `~/.config/plasma-org.kde.plasma.desktop-appletsrc`
- `~/.config/plasmashellrc`

Autostart entry:

- `~/.config/autostart/keskos-quickshell.desktop`
- `~/.config/autostart/keskos-display-watch.desktop`

Shell wrapper:

- `/usr/local/bin/keskos-shell`

Logs:

- `~/.local/state/keskos/quickshell.log`
- `~/.local/state/keskos/display-watch.log`
- `~/.cache/keskos/session-start.log`

## How Startup Works

KDE autostarts:

- `/usr/local/bin/keskos-session-start`
- `/usr/local/bin/keskos-display-watch`

That script runs:

1. `keskos-configure-user`
2. `keskos-wallpaper-apply`
3. `keskos-shell`

The display watcher then:

- watches for monitor hotplug and layout changes
- reapplies the wallpaper across all detected Plasma desktops
- refreshes the managed Plasma panel state if Plasma spawns a default panel on the new screen
- restarts the Quickshell top bar so every detected monitor gets the HUD again

`keskos-configure-user` now:

- keeps Quickshell configured for the top bar only
- creates or refreshes the managed Plasma bottom panel
- pins the default taskbar launchers
- configures four virtual desktops
- defaults the panel launcher to the patched `Kesk Kickoff` widget

`keskos-shell` then:

- stops `eww` if it is still running
- skips startup if a KeskOS Quickshell instance is already active
- launches `quickshell --config keskos`
- writes logs to `~/.local/state/keskos/quickshell.log`

## Bottom Panel

The bottom bar is now a real Plasma panel with:

- `org.kde.plasma.simplekickoff` on the far left by default
- `org.kde.plasma.taskmanager` as the real pinned/running app taskbar
- `com.keskos.workspaceswitcher` on the right side

The panel setup script lives at:

- `configs/plasma/keskos-bottom-panel.js`

It is applied through Plasma's scripting API, so the managed bottom taskbar is recreated only when it does not already match the KeskOS layout.

If the patched Kesk launcher is unavailable for any reason, the panel falls back to:

- `org.kde.plasma.kicker`
- `org.kde.plasma.kickoff`

There is also a reusable Plasma layout template installed as:

- `/usr/share/plasma/layout-templates/org.keskos.plasma.defaultPanel/`

See:

- `docs/plasma-panel-layout.md`

## Launcher Wiring

The patched SimpleKickoff launcher is now the default launcher path.

- Meta opens the Kesk launcher by default
- Alt+F1 still triggers Plasma's standard launcher action

To switch defaults:

- `keskos-launcher-switch keskos`
- `keskos-launcher-switch kde`
- `keskos-launcher-switch status`

See:

- `docs/launcher-switching.md`

## Default Pinned Apps

The real task manager is pinned by default to:

- Konsole
- Dolphin
- LibreWolf if present, otherwise Firefox
- System Settings

The KDE launcher favorites are also seeded with:

- Konsole
- Dolphin
- the preferred browser
- System Settings

To change the default pinned apps, edit:

- `configs/plasma/keskos-bottom-panel.js`

Look for the `defaultLaunchers()` function.

## Workspace Switcher

The right side of the bottom panel uses:

- `configs/plasmoids/com.keskos.workspaceswitcher/`

This avoids the stock pager rendering issue where the workspace labels could disappear into the panel theme. The widget always shows numbered desktop blocks:

- `1`
- `2`
- `3`
- `4`

Clicking a number uses `/usr/local/bin/keskos-workspace set <n>` to switch desktops.

## Restarting The Shell

Top bar only:

```bash
pkill quickshell
keskos-shell
cat ~/.local/state/keskos/quickshell.log
```

Plasma taskbar only:

```bash
kquitapp6 plasmashell
plasmashell --replace >/tmp/keskos-plasmashell.log 2>&1 &
```

Alternative Plasma restart:

```bash
kquitapp6 plasmashell && kstart plasmashell
```

## Resetting The Plasma Panel

To rebuild the managed bottom panel for the current user:

```bash
keskos-reset-panel
```

If you only want to refresh the panel logic without using the reset helper:

```bash
kquitapp6 plasmashell
plasmashell --replace >/tmp/keskos-plasmashell.log 2>&1 &
keskos-configure-user
```

## Disable Quickshell For Debugging

Temporary for the current shell:

```bash
export KESKOS_DISABLE_SHELL=1
pkill quickshell
```

To stop it on login for the current user:

```bash
mv ~/.config/autostart/keskos-quickshell.desktop ~/.config/autostart/keskos-quickshell.desktop.disabled
pkill quickshell
```

## Restore Stock Plasma Temporarily

If you want to debug with a stock Plasma layout instead of the managed KeskOS panel:

```bash
mv ~/.config/plasma-org.kde.plasma.desktop-appletsrc ~/.config/plasma-org.kde.plasma.desktop-appletsrc.kesk-backup
mv ~/.config/plasmashellrc ~/.config/plasmashellrc.kesk-backup
kquitapp6 plasmashell
plasmashell --replace >/tmp/keskos-plasmashell.log 2>&1 &
```

Then run `keskos-configure-user --force` later to restore the KeskOS panel.

## Troubleshooting

Check the shell and panel processes:

```bash
pgrep -a quickshell
pgrep -a plasmashell
pgrep -a eww
```

Inspect logs:

```bash
cat ~/.local/state/keskos/quickshell.log
cat ~/.cache/keskos/session-start.log
journalctl --user -xe
```

Check shell processes:

```bash
pgrep -a quickshell
pgrep -a eww
```

Check launcher mode and switch defaults:

```bash
keskos-launcher-switch status
keskos-launcher-switch kde
```

List and refresh Plasma applets:

```bash
kpackagetool6 --type Plasma/Applet --list
kbuildsycoca6
```

If the top bar does not appear:

1. Verify `quickshell` is installed.
2. Check that `~/.config/quickshell/keskos/shell.qml` exists.
3. Run `keskos-shell` manually from Konsole.

If the bottom taskbar does not appear:

1. Restart `plasmashell`.
2. Run `keskos-configure-user --force`.
3. Check that `/usr/share/plasma/plasmoids/com.keskos.workspaceswitcher/` exists.
4. Confirm `~/.config/plasma-org.kde.plasma.desktop-appletsrc` contains both `keskosPanel=keskos-bottom-panel-v1` and `keskosPanel=keskos-top-reserve-v1`.

If desktop icons still appear behind the top bar:

1. Restart `plasmashell`.
2. Run `keskos-configure-user --force`.
3. Confirm the managed top reserve panel marker exists in `~/.config/plasma-org.kde.plasma.desktop-appletsrc`.
