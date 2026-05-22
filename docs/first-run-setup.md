# KeskOS Setup Console

This setup console is now a fallback/debug tool only.

The current supported first-boot app is `Kesk Welcome`.

See:

- `docs/kesk-welcome.md`

The default KeskOS install path has moved into Calamares:

- browser choice
- browser startpage/theme toggle
- package bundles
- custom extra packages
- feature flags

See:

- `docs/calamares-keskos-installer.md`

`KeskOS Setup Console` is no longer the primary first-login app shipped for KeskOS. `Kesk Welcome` now owns the normal first-boot flow.

It launches after the first real user login, walks through browser selection and optional package installs, then writes the completion marker at:

```text
~/.config/keskos/first-run-complete
```

If that file exists, the app exits immediately and the desktop loads normally.

## What It Does

The setup flow is organized as:

1. Welcome / first boot detection
2. Browser selection
3. Browser install + startpage/theme apply
4. Optional package installer
5. Completion summary

The app uses a terminal-styled black/orange Qt interface and deliberately avoids Breeze-style white installer UI.

## CachyOS Reference Notes

The package installer step was built with the CachyOS Package Installer workflow in mind, but no CachyOS code was copied into this repository for the current implementation.

What was reused conceptually:

- repository-backed package search
- queued package install flow
- pkexec / pacman separation from the GUI
- install log visibility

What was not reused:

- CachyOS UI code
- CachyOS branding
- CachyOS layouts
- CachyOS assets or logos

Because the current implementation is reference-only, there are no vendored third-party source files for this feature.

## Installed Files

Main entrypoints:

- `/usr/bin/keskos-first-run`
- `/usr/lib/keskos-first-run/main.py`

Backend modules:

- `/usr/lib/keskos-first-run/backend/state.py`
- `/usr/lib/keskos-first-run/backend/pacman_backend.py`
- `/usr/lib/keskos-first-run/backend/browser_setup.py`
- `/usr/lib/keskos-first-run/backend/theme_apply.py`
- `/usr/lib/keskos-first-run/package_presets.py`

Desktop/autostart:

- `/usr/share/applications/keskos-first-run.desktop`
- `/etc/xdg/autostart/keskos-first-run.desktop`

Browser theme assets:

- `/usr/share/keskos/first-run/browser-theme/firefox-userChrome.css`
- `/usr/share/keskos/first-run/browser-theme/firefox-userContent.css`

Local startpage:

- `/usr/share/keskos/startpage/index.html`

## First-Run State

Completion state:

```bash
rm ~/.config/keskos/first-run-complete
```

Deleting that file causes the setup console to open again on the next login.

## Manual Commands

Run manually:

```bash
keskos-first-run
```

Force-open even when the live-session autorun guard would normally skip it:

```bash
keskos-first-run --force
```

Reset first-run:

```bash
rm ~/.config/keskos/first-run-complete
```

View logs:

```bash
cat ~/.local/state/keskos/first-run.log
```

Search packages manually:

```bash
pacman -Ss <query>
```

Install manually:

```bash
sudo pacman -S --needed <packages>
```

## Browser Behavior

The browser step offers:

- LibreWolf
- Zen Browser
- Brave

Behavior:

- tries to resolve a pacman package from the configured repos
- installs the selected browser with `pkexec pacman -S --needed --noconfirm ...`
- tries to set the selected browser as default via `xdg-settings`, `xdg-mime`, and `mimeapps.list`
- applies the local KeskOS startpage at `file:///usr/share/keskos/startpage/index.html`

Firefox-family browsers:

- apply homepage prefs with `user.js`
- copy `userChrome.css` and `userContent.css` when a profile exists

Chromium-family browsers:

- update the Brave `Preferences` file when a profile exists

If a profile does not exist yet, the setup console reports `THEME PARTIALLY APPLIED` and continues.

## Package Installer Behavior

The package step uses:

- `pacman -Ss` for search
- preset package categories from `package_presets.py`
- `pkexec pacman -S --needed --noconfirm ...` for installs

The GUI itself does not run as root.

Only the package install action is elevated.

Failed package installs do not abort the whole wizard; they are reported in the final summary and the log.

## Emergency / Recovery Behavior

The setup console blocks normal close actions until completion.

Debug/recovery path:

- press `Ctrl+Shift+D`
- open a terminal
- view logs
- use `Emergency Skip` with confirmation

Emergency skip writes the completion state file with a `skipped` reason so the user is not permanently trapped.

## Network Handling

If networking appears unavailable, the wizard:

- shows a warning banner
- offers `Open Network Settings`
- allows retry
- still leaves the hidden emergency skip path available

It does not hard-lock the user in an unrecoverable state.

## How To Add Browser Options

Edit:

- `airootfs/usr/lib/keskos-first-run/backend/browser_setup.py`

Update:

- browser label / description
- package candidate list
- desktop file candidates
- browser family type

If the browser needs custom theming, extend:

- `airootfs/usr/lib/keskos-first-run/backend/theme_apply.py`

## How To Add Package Presets

Edit:

- `airootfs/usr/lib/keskos-first-run/package_presets.py`

Each key is a displayed category name and each value is a list of package names to probe in pacman.

## Disable Mandatory First-Run Mode

Supported options:

1. Remove the autostart file:

```bash
sudo rm /etc/xdg/autostart/keskos-first-run.desktop
```

2. Export this environment variable before launching the app:

```bash
KESKOS_DISABLE_FIRST_RUN=1
```

3. Create the completion state file manually:

```bash
mkdir -p ~/.config/keskos
printf '{\"reason\":\"manual\"}\n' > ~/.config/keskos/first-run-complete
```

## Known Limitations

- Brave package naming varies between repository sets; if none of the configured candidates exists, Brave is marked unavailable.
- Firefox-family profile theming is best-effort and depends on a browser profile existing.
- Chromium theming is intentionally limited to homepage/startup behavior instead of full browser chrome reskinning.
- The current implementation does not automatically repin the KDE taskbar to the selected browser.
- AUR-only browser packages are not required and are not used automatically unless the package already exists in the configured pacman repositories.
