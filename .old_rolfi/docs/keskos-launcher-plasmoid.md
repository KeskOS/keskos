# KeskOS Launcher Plasmoid

`org.keskos.launcher` is the older custom Plasma 6 launcher plasmoid kept in the repo as an experimental/legacy path.

It is no longer the default launcher. Current KeskOS builds prefer the patched `org.kde.plasma.simplekickoff` package described in `docs/launcher-switching.md`.

It is a real Plasma widget, not an external floating app. It is designed to:

- appear in Plasma's launcher `Alternative Widgets` list
- replace the stock KDE launcher on the panel when selected
- keep Wolfi available as a fallback
- stay closer to the KeskOS black/orange terminal identity than Kickoff

## Install Paths

Repo source:

- `configs/plasmoids/org.keskos.launcher/`

Installed paths:

- `/usr/share/plasma/plasmoids/org.keskos.launcher/`
- `/usr/share/icons/hicolor/48x48/apps/keskos-launcher.png`
- `/usr/share/icons/hicolor/64x64/apps/keskos-launcher.png`
- `/usr/share/icons/hicolor/128x128/apps/keskos-launcher.png`

The widget now uses Plasma's native Kicker models for:

- favorites
- application categories
- search results
- real `.desktop` launch behavior

That makes it much closer to the working `Windows7StartMenu4KDE` model flow while keeping the KeskOS layout and styling.

## What It Provides

Metadata:

- `Id`: `org.keskos.launcher`
- `Name`: `KeskOS Launcher`
- `Description`: `KeskOS terminal-style application launcher`
- `X-Plasma-Provides`: `org.kde.plasma.launchermenu`

That `X-Plasma-Provides` value is what makes Plasma treat it as a launcher alternative next to the built-in launchers.

## Manual Testing

Install or upgrade the plasmoid package manually:

```bash
kpackagetool6 --type Plasma/Applet --install configs/plasmoids/org.keskos.launcher
kpackagetool6 --type Plasma/Applet --upgrade configs/plasmoids/org.keskos.launcher
```

Restart Plasma:

```bash
systemctl --user restart plasma-plasmashell.service
```

Watch logs:

```bash
journalctl --user -f | grep -i plasma
```

## Selecting It From Alternative Widgets

1. Right-click the current launcher on the Plasma panel.
2. Choose `Show Alternatives...`
3. Select `KeskOS Launcher`

If the widget metadata is installed correctly, it should appear next to:

- `Application Menu`
- `Application Launcher`
- other launcher alternatives that provide `org.kde.plasma.launchermenu`

## Switching Launcher Defaults

Use:

```bash
keskos-launcher-switch status
keskos-launcher-switch keskos
keskos-launcher-switch kde
keskos-launcher-switch wolfi
```

Meaning:

- `keskos` sets `org.keskos.launcher` as the default panel launcher
- `kde` restores the KDE launcher path
- `wolfi` restores Wolfi as the default launcher path

To repair an existing user config and reapply the custom launcher:

```bash
keskos-fix-launcher
```

## Wolfi Fallback

Wolfi stays installed and available.

Fallback entry points:

- `Meta+W`
- `keskos-toggle-wolfi`
- `keskos-launcher --mode main`
- `keskos-launcher.desktop`

## Debugging

Useful commands:

```bash
kpackagetool6 --type Plasma/Applet --list
systemctl --user restart plasma-plasmashell.service
journalctl --user -f | grep -i plasma
cat ~/.config/plasma-org.kde.plasma.desktop-appletsrc
```

If the wrong launcher opens:

1. Check `keskos-launcher-switch status`
2. Run `keskos-launcher-switch keskos`
3. Run `keskos-fix-launcher`
4. Restart `plasmashell`

If Plasma does not show the widget in `Alternative Widgets`, verify:

- `/usr/share/plasma/plasmoids/org.keskos.launcher/metadata.json` exists
- the metadata contains `org.kde.plasma.launchermenu`
- the plasmoid is listed by `kpackagetool6 --type Plasma/Applet --list`

If the menu opens but shows no applications, check QML/runtime errors with:

```bash
journalctl --user -f | grep -i -E 'plasma|kicker|keskos'
```
