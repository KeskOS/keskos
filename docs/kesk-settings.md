# Kesk Settings

`kesk settings` is the main KeskOS graphical settings application.

It is designed to feel closer to KDE Plasma System Settings than to a dashboard or launcher:

- grouped category sidebar
- search field at the top-left
- black/orange KeskOS shell styling
- real settings pages on the right
- bottom `Reset` / `Apply` action bar

It intentionally does **not** turn into:

- a repair dashboard
- an updater dashboard
- a logs console
- a package manager
- a developer tools launcher

Those remain separate commands:

- `kesk upgrade`
- `kesk doctor`
- `kesk repair`

## Purpose

Kesk Settings is the user-facing place for:

- KDE Plasma user settings that have a safe apply path
- KeskOS-specific desktop preferences
- handoff to KDE modules for more complex settings that should stay in KDE’s own tools

It is the normal desktop settings app.
The operational tools stay outside it on purpose.

## Layout

The current GUI uses a Plasma-style structure:

- title area: `Kesk Settings — System Settings`
- grouped left sidebar
- search field with sidebar toggle
- right content panel
- page title and description at the top
- compact sections with rows, toggles, combos, sliders, and buttons
- bottom `Reset` and `Apply` buttons when the current page supports direct writes

The default page is `Quick Settings`.

## Categories

The sidebar is grouped into these sections:

- `Quick Settings`
- `Input & Output`
- `Connected Devices`
- `Networking`
- `Appearance & Style`
- `Apps & Windows`
- `System`
- `KeskOS`

Implemented pages include:

- `Quick Settings`
- `Mouse & Touchpad`
- `Keyboard`
- `Sound`
- `Display & Monitor`
- `Accessibility`
- `Disks & Cameras`
- `Printers`
- `Removable Storage`
- `Bluetooth`
- `Wi-Fi & Internet`
- `Online Accounts`
- `VPN`
- `Proxy`
- `Wallpaper`
- `Colors & Themes`
- `Text & Fonts`
- `Icons`
- `Cursors`
- `Window Decorations`
- `Splash Screen`
- `Login Screen`
- `Default Applications`
- `File Associations`
- `Window Behavior`
- `Task Switcher`
- `Shortcuts`
- `Notifications`
- `Search`
- `Power Management`
- `Users`
- `Region & Language`
- `Date & Time`
- `Privacy & Security`
- `Boot & Login`
- `Updates`
- `About This System`
- `KeskOS Theme`
- `Panels & Launcher`
- `HUD / Widgets`
- `Browser Defaults`
- `Boot Splash`
- `Experimental Features`

No sidebar page is intentionally blank.
Every page now includes:

- a title and scope description
- compact settings rows or status rows
- real controls where a safe backend already exists
- disabled planned controls where the backend is not connected yet
- KDE module handoff buttons where that is the safer or more complete path

Some pages already write settings directly.
Some pages currently provide focused read-only state plus a safe handoff to a KDE module.
When a page is not fully wired yet, it states:

`This setting will use KDE config backend when implemented.`

## Quick Settings

`Quick Settings` is the first page and includes:

- theme preview cards:
  - `Breeze`
  - `Breeze Dark`
  - `Automatic`
  - `KeskOS Dark`
- appearance shortcut buttons:
  - `Wallpaper`
  - `Global Theme`
  - `Colors & Themes`
- animation speed slider
- file click behavior controls
- `General Behavior` KDE module handoff

`KeskOS Dark` applies the branded KeskOS theme chain while preserving the managed panel and official wallpaper path.

## What Uses Real KDE Backends

Directly implemented settings currently include combinations of:

- global theme, Plasma theme, color scheme, icon theme, cursor theme, font, window decoration, wallpaper
- animation duration factor
- desktop count and workspace names
- launcher mode and launcher shortcut
- panel mode and branded panel preferences
- keyboard layout and repeat settings
- Night Color
- audio volume and mute
- Wi-Fi radio and hostname handoff
- power profile and timeout preferences
- user avatar and display name preferences
- default application handlers
- update-check preferences
- boot/login preference storage
- KeskOS accent, CRT, scanline, homepage, and experimental preferences

KDE module handoff is used where that is safer or more complete, such as:

- accessibility
- Bluetooth
- advanced network settings
- shortcuts
- search/KRunner
- region and language
- date and time
- privacy/lock-screen settings

## Backend Status

Each backend-facing page now reports one of these states:

- `Connected`
- `Limited`
- `KDE handoff`
- `Intentional handoff`
- `Missing tools`
- `Requires admin`

Current backend coverage:

- `Accessibility`: direct large-text, reduced-animation, and cursor-size writes; advanced KDE handoff for the rest
- `Bluetooth`: adapter/service/device listing plus connect, disconnect, pair, trust, and remove when `bluetoothctl` exists
- `Online Accounts`: lightweight account discovery plus KDE Online Accounts handoff
- `VPN`: NetworkManager-backed list, connect, disconnect, import, and auto-connect
- `Proxy`: direct KDE proxy writes through `kioslaverc`
- `File Associations`: MIME search plus safe `xdg-mime` and `mimeapps.list` updates
- `Task Switcher`: read-only current status plus KWin advanced handoff
- `Notifications`: Dunst-backed notification editing, Do Not Disturb, test notifications, reload, and branded preset apply
- `Search`: Baloo indexing on/off and hidden-file indexing, plus KDE search handoff
- `Privacy`: recent-file cleanup and stored privacy prefs, plus KDE lock-screen/privacy handoff
- `Audio`: device discovery, default-device switching, mute, and volume through `wpctl`/`pactl`
- `Display`: safe read state plus brightness where supported; monitor layout and scaling still hand off to KDE
- `Boot & Login`: privileged SDDM, Plymouth, quiet-boot, and splash-duration actions through the Kesk Settings helper

## Privileged Settings

The settings GUI itself does not run as root.

Privileged actions now go through:

```text
/usr/lib/kesk/kesk-settings-helper
```

with the policy:

```text
/usr/share/polkit-1/actions/org.keskos.settings.policy
```

This helper is intentionally limited to:

- setting the active SDDM theme
- updating the KeskOS SDDM background when the theme supports it
- setting the active Plymouth theme
- toggling quiet boot
- storing boot splash minimum duration
- rebuilding initramfs on request

These actions may require:

- administrator authentication
- initramfs rebuilds
- reboot or logout to verify results

## KeskOS Settings Storage

KeskOS-specific GUI settings are stored in:

```text
~/.config/kesk/settings.json
```

GUI window state is stored in:

```text
~/.config/kesk/settings-gui.ini
```

KDE-native settings still live in their normal KDE files, for example:

- `~/.config/kdeglobals`
- `~/.config/kwinrc`
- `~/.config/plasmarc`
- `~/.config/kcminputrc`
- `~/.config/kxkbrc`
- `~/.config/mimeapps.list`
- `~/.config/baloofilerc`
- `~/.config/kioslaverc`

## Backups

Before important KDE/user config changes, Kesk Settings writes targeted backups to:

```text
~/.local/state/kesk/settings-backups/
```

Backups are grouped by settings area, for example:

- `*-appearance`
- `*-desktop`
- `*-panels`
- `*-windows`
- `*-quick-settings`

The Dunst notifications page also writes direct file backups before rewriting user config:

- `dunstrc.YYYYMMDD-HHMMSS.bak`
- `dunst.desktop.YYYYMMDD-HHMMSS.bak`

System-level privileged helper actions also create targeted backups under:

```text
/var/lib/kesk/settings-backups/
```

## Logs

GUI runs write logs to:

```text
~/.local/state/kesk/logs/gui-YYYYMMDD-HHMMSS.log
```

These logs include:

- app start
- selected pages
- launched commands
- apply results
- warnings and errors

No passwords or secrets are stored.

## Notifications Backend

KeskOS uses `dunst` as the runtime notification daemon.

The Notifications page now targets Dunst first and keeps KDE notifications as an advanced handoff only.

Primary config path:

```text
~/.config/dunst/dunstrc
```

System fallback path:

```text
/etc/dunst/dunstrc
```

Supported direct Dunst actions include:

- enable or disable notification autostart
- live Do Not Disturb through `dunstctl`
- notification position, width, height, font, icons, transparency, border, and urgency colors
- KeskOS branded Dunst preset apply
- Dunst reload
- test notifications through `notify-send`

Useful commands:

```bash
notify-send "KESKOS" "Notification backend online."
dunstctl is-paused
dunstctl set-paused true
dunstctl set-paused false
dunstctl reload
```

If duplicate notifications appear, KeskOS is likely running Dunst alongside KDE/Plasma notification integration.
In that case, keep Dunst as the main notifier and adjust the KDE notification stack from the advanced KDE handoff button if needed.

## Known Limitations And Handoffs

| Page | Current backend | Limitation | Reason |
| --- | --- | --- | --- |
| Notifications | Dunst primary | Per-app rules use KDE handoff | Dunst handles global notification style, KDE handles app-specific notification rules |
| Notifications | Dunst primary | DND/reload need dunstctl | Live control depends on Dunst tooling |
| Notifications | Dunst primary | Test notifications need notify-send | Test button uses libnotify |
| Notifications | Dunst primary | Duplicate notifications possible | Plasma notification integration may still be active |
| Accessibility | KDE handoff | Advanced toggles not directly written | Safer to use KDE module |
| Online Accounts | KDE handoff | Not directly edited | KDE account system is complex |
| Task Switcher | KDE handoff | Not directly edited | KWin settings are safer through KDE module |
| Display | KDE handoff only | No direct layout/scaling apply | Avoid black-screen risk |
| Boot & Login | Privileged helper | Needs pkexec/assets/recognized bootloader | System-level changes are risky |

Test commands:

```bash
notify-send "KESKOS" "Notification backend online."
dunstctl is-paused
dunstctl set-paused true
dunstctl set-paused false
dunstctl reload

kcmshell6 kcm_notifications
kcmshell6 kcm_access
kcmshell6 kcm_kscreen
kcmshell6 kwintabbox
```

## Tools Used

The graphical settings app now relies on combinations of:

- `kwriteconfig6`
- `kreadconfig6`
- `kcmshell6`
- `qdbus6`
- `kscreen-doctor`
- `wpctl`
- `pactl`
- `dunst`
- `dunstctl`
- `notify-send`
- `nmcli`
- `xdg-mime`
- `xdg-settings`
- `balooctl6`
- `bluetoothctl`
- `pkexec`

Missing optional tools do not crash the app.
Instead the page reports `Limited` or `Missing tools`.

## Running It

From a KDE/Wayland or X11 session:

```bash
kesk settings
```

Direct GUI entry:

```bash
kesk-settings
```

Dry-run backend check:

```bash
kesk settings --dry-run
```

`--dry-run` prints:

- detected session type
- whether a graphical session is present
- detected KDE helper tools
- detected Dunst helper tools
- config paths
- writable config/backups paths
- privileged helper/polkit visibility
- backend summaries and missing optional tools
- Dunst runtime status and Do Not Disturb availability
- a limitations / handoff matrix for notifications, accessibility, online accounts, task switcher, display, and boot/login

## Start Menu Launcher

Desktop launcher:

- `/usr/share/applications/kesk-settings.desktop`

It launches:

```bash
kesk settings
```

## Difference From The Command Tools

- `kesk settings` changes desktop/system preferences
- `kesk upgrade` handles updates
- `kesk doctor` checks health
- `kesk repair` restores and repairs the branded desktop stack

Kesk Settings is not supposed to replace those operational tools with a giant dashboard.

## Debugging Missing Backends

If a page shows `Missing tools` or `Limited`:

1. Run `kesk settings --dry-run`
2. Check the `TOOLS` section for the missing command
3. Check the `BACKENDS` section for the page-specific summary
4. Use the page's `Open Advanced ...` button when the direct backend is intentionally conservative

Useful examples:

- Bluetooth needs `bluetoothctl`
- Dunst notifications need `dunst`, `dunstctl`, and optionally `notify-send`
- VPN and Wi-Fi extras need `nmcli`
- direct audio control needs `wpctl` or `pactl`
- direct display brightness needs `brightnessctl`
- boot/login system changes need `pkexec` plus the Kesk Settings helper

## Testing

Useful tests:

```bash
kesk settings --dry-run
kesk settings
kesk-settings
```

In the GUI, test:

1. search in the sidebar
2. page switching
3. `Quick Settings`
4. direct apply on pages like `Colors & Themes`, `Window Behavior`, `Input`, `Power`, `Updates`, `Accessibility`, `Advanced Networking`, `Sound`, `Privacy`, and `Boot & Login`
5. `kesk settings --dry-run` for backend availability
6. KDE module handoff buttons on limited pages
7. `Notifications` for Dunst config writes, Do Not Disturb, reload, preset apply, and test notifications

## Known Limitations

- Not every sidebar page writes settings directly yet.
- Task-switcher details are still intentionally conservative because KWin tabbox keys vary across setups.
- The Notifications page assumes Dunst is the active runtime notifier. If Plasma integration also shows popups, you may need to adjust the advanced KDE notification stack separately.
- `Automatic` theme mode in `Quick Settings` is kept conservative until a real scheduled-theme backend is added.
- Boot/login changes now have a root-backed helper path, but they still require admin approval and may need a reboot or logout to verify.
- If the usual XDG state/config paths are not writable, Kesk Settings falls back to a safe writable runtime path instead of crashing.
