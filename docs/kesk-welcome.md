# Kesk Welcome

`Kesk Welcome` is the current KeskOS first-boot setup app.

It is a Rust/GTK adaptation of the CachyOS Welcome codebase, reworked for the current KeskOS toolchain and visual style.

## What It Does

The app opens as a guided first-boot flow with these pages:

1. Welcome
2. Network / Uplink
3. Browser
4. Top Bar Widgets
5. Optional Apps
6. Theme Check
7. System Links
8. Finish

The UI keeps the current KeskOS direction:

- black / near-black background
- orange accent `#ce6a35`
- square controls
- terminal / console presentation
- numbered setup steps
- a left-side deployment rail
- an installer-style hero/status shell that matches the current KeskOS Calamares flow more closely

## First Boot Behavior

Autostart uses:

```text
/etc/xdg/autostart/kesk-welcome.desktop
```

It runs:

```bash
kesk welcome --first-run
```

First-run mode is safe:

- if `~/.config/kesk/welcome-complete` exists, the app exits immediately
- if the legacy marker `~/.config/keskos/first-run-complete` exists, the app also exits immediately
- if the system is still in a live ISO session, first-run autostart exits immediately
- the marker is only created when the user presses `Finish`

There is no always-show-on-startup checkbox.

## Manual Rerun

Open the app manually:

```bash
kesk welcome
```

Force a manual rerun path:

```bash
kesk welcome-rerun
```

Direct binary:

```bash
kesk-welcome
```

`kesk welcome-rerun` does not delete the marker automatically. It simply opens the app again even when first-boot completion already exists.

## Browser Page

Browser follows the Network / Uplink step.

Supported browsers:

- LibreWolf
- Brave
- Zen Browser
- Firefox fallback

Behavior:

- fresh installs no longer assume any browser is preinstalled
- detects installed browsers
- uses `xdg-settings` / `xdg-mime` through the existing browser helper when setting defaults
- applies the KeskOS homepage/theme through the existing browser helper when assets exist
- uses `pacman` first for installs
- falls back to `yay` for AUR packages when needed
- offers `yay` installation only when a selected package actually needs it
- never installs packages without confirmation

If there is no internet uplink, the app still opens, but package installation stays unavailable.

If the user skips the Browser page:

- the Welcome flow still completes normally
- the desktop remains usable
- no browser may be installed yet until the user installs one later

## Network / Uplink

The Network / Uplink page checks whether package-install actions can be used later in the flow.

Backend order:

- `nmcli` for device, connection, and Wi-Fi management
- `ping -c 1 -W 2 8.8.8.8` for actual uplink verification

The page reports:

- uplink status
- active connection
- backend status
- wired status
- Wi-Fi adapter status
- detected SSIDs when NetworkManager is available

Actions:

- scan Wi-Fi networks
- connect to a selected SSID
- recheck uplink

Rules:

- the app still opens when offline
- Browser install actions stay disabled until uplink is reachable
- Optional Apps install actions stay disabled until uplink is reachable
- Wi-Fi passwords are never written to `welcome.log`

Support badges:

- `Native`: `nmcli` and `ping` available
- `Limited`: only part of the backend is available
- `Unsupported`: neither `nmcli` nor `ping` is available

## Top Bar Widgets

Current visible widget set:

- Media
- CPU
- Memory
- Network

The current backend is still limited.

The page can:

- report backend status
- reapply the default top bar setup
- restart the top bar backend

Per-widget toggles stay disabled until that backend is fully connected.

## Optional Apps

The Optional Apps page uses a curated list only.

Current groups:

- Gaming
- Creator
- Dev
- Utilities

Package rules:

- `pacman` first
- `yay` fallback for AUR-only items
- no silent installs
- confirmation before every install action
- no Docker page or Docker bundle in this flow

If there is no internet uplink, the app still opens, but package installation stays unavailable.

## Theme Check

Theme Check is a repair/reset page, not a theme picker.

It reports:

- KeskOS Orange theme state
- KDE defaults state
- launcher layout status
- panel layout status
- Konsole profile status
- Dunst status

Actions reuse existing KeskOS tools where available:

- `kesk-apply-theme`
- `kesk-apply-kde-defaults`
- launcher repair helpers
- panel reset helpers
- `kesk repair --konsole --yes`

Boot Splash stays explicitly under development. Plymouth is not treated as fully supported here yet.

## System Links

External links open with `xdg-open`:

- `https://keskos.org`
- `https://docs.keskos.org`
- `https://github.com/memegeko/keskos`
- `https://downloads.keskos.org`

If `xdg-open` fails, the app tells the user to visit the URL manually.

The page also provides quick buttons for:

- `kesk settings`
- `kesk doctor`
- `kesk upgrade`
- `kesk repair`

## Finish / Install Report

The `Finish` page now includes an explicit `INSTALL REPORT` section.

Controls:

- `Send basic install report`
- `Include extra diagnostic details`

Behavior:

- the installer already sends the basic install report during Calamares
- the basic follow-up option will not re-send the same basic payload if the installer report was already marked as sent
- extra diagnostics stay off by default
- the client posts only to `https://api.keskos.org/install-report`
- the client does not send Discord webhooks directly
- reporting failures never block the completion marker or the end of the flow

Local install-report log:

```text
~/.local/state/kesk/logs/install-report.log
```

Full reporting documentation:

- `docs/install-reporting.md`

## Logs

Logs are written to:

```text
~/.local/state/kesk/logs/welcome.log
```

The log records:

- app start
- first-run vs rerun mode
- network page open / uplink recheck / scan / connect attempts
- internet state
- browser actions
- package install attempts
- theme actions
- marker creation
- errors

The log never records Wi-Fi passwords.

## Disable Autostart

Per-user override example:

```bash
mkdir -p ~/.config/autostart
cp /etc/xdg/autostart/kesk-welcome.desktop ~/.config/autostart/
printf 'Hidden=true\n' >> ~/.config/autostart/kesk-welcome.desktop
```

## Integration

Kesk Welcome reuses existing KeskOS tools where possible:

- browser helper from `keskos-settings`
- `kesk settings`
- `kesk doctor`
- `kesk upgrade`
- `kesk repair`

## License / Attribution

This app is a fork/adaptation of CachyOS Welcome.

- upstream project: `CachyOS Welcome`
- upstream repository: `https://github.com/CachyOS/CachyOS-Welcome`

The original GPL license remains with the standalone `KeskOS/keskos-welcome` source repository, which is now the maintained package/app source of truth.
