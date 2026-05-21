# Kesk Settings

KeskOS uses the real KDE Plasma System Settings application as the official settings app.

The branded launcher is:

- `Kesk Settings`

It launches:

- `systemsettings`

KeskOS does not replace KDE’s settings backends with a custom dashboard app.
Display, sound, networking, accessibility, users, defaults, file associations, power, notifications, and the rest of the normal KDE settings flow still come from the real Plasma KCM stack.

## Official Launcher

The user-facing launcher is:

- `desktop/kesk-settings.desktop`

Important values:

- `Name=Kesk Settings`
- `Comment=Configure KeskOS and KDE Plasma settings`
- `Exec=systemsettings`
- `Icon=preferences-system`

The upstream KDE launcher is hidden with a local override so the branded KeskOS entry is the visible one:

- `desktop/systemsettings.desktop`

The archived old PySide replacement UI is not part of the live launcher path and is not the default settings app anymore.

## Command Behavior

These commands are the intended entry points:

```bash
systemsettings
kesk settings
```

Useful KDE KCM commands:

```bash
kcmshell6 --list
kcmshell6 <module-name>
```

Examples:

```bash
kcmshell6 kcm_kscreen
kcmshell6 kcm_pulseaudio
kcmshell6 kcm_access
```

Exact KCM names depend on the installed package set.

## Visual Stack

Kesk Settings keeps the KDE System Settings structure and pages, then skins them with the KeskOS visual layer:

- KDE color scheme: `KeskOSDark`
- optional Kvantum theme: `KeskOS`
- safe fallback widget style: `Breeze`
- Plasma theme: `keskos-shell`
- dark/orange window decoration and title styling where available
- branded `Kesk Settings` launcher pointing at real `systemsettings`

The visual target is:

- near-black backgrounds
- orange accent `#ce6a35`
- muted gray text
- sharp rectangular controls
- no giant orange slabs
- no stock Breeze blue accents where safely avoidable

Theme apply/debug commands:

```bash
kesk-apply-theme
kesk-theme-status
plasma-apply-colorscheme KeskOSDark
```

Manual checks:

```bash
kreadconfig6 --file ~/.config/kdeglobals --group General --key ColorScheme
kreadconfig6 --file ~/.config/kdeglobals --group General --key AccentColor
kreadconfig6 --file ~/.config/kdeglobals --group KDE --key widgetStyle
```

## Hidden Stock Modules

KeskOS keeps the real KDE modules installed, but hides some stock KCMs from the normal System Settings UI for a cleaner default experience.

Important examples:

- `User Feedback` is hidden by default
- the stock KDE `About This System` entry is hidden by default
- the KeskOS-owned `About This System` page replaces it in the visible UI

Hidden-module tooling:

```bash
kesk-list-kcms
sudo kesk-hide-kcms
sudo kesk-restore-kcms
```

The default hidden list is:

- `airootfs/usr/share/kesk/settings/hidden-kcms.conf`

The optional extra list is:

- `airootfs/usr/share/kesk/settings/hidden-kcms-extra.conf`

## KeskOS Custom Modules

KeskOS now adds a small set of real custom KCM pages to the real KDE System Settings app.

### System

- `About This System`
  Website, Docs, and GitHub links open the official KeskOS destinations.
- `Help`
  Opens `https://docs.keskos.org`.

### KeskOS

- `KeskOS Theme`
- `Panels & Launcher`
- `Top Bar Widgets`
- `Browser Defaults`
- `Boot Splash`
- `KeskOS Version`

These pages keep the normal KDE System Settings layout and navigation model.
They are not a dashboard replacement.

## Module Details

### Help

Purpose:

- open the official KeskOS documentation from inside System Settings

Behavior:

- opens `https://docs.keskos.org`
- uses `xdg-open`
- if that fails, the UI shows:
  `Could not open browser. Visit https://docs.keskos.org manually.`

Support level:

- `Native`

### About This System

Purpose:

- show a short KeskOS-owned system summary
- provide official link buttons

Links:

- `https://keskos.org`
- `https://docs.keskos.org`
- `https://github.com/memegeko/keskos`

Support level:

- `Native`

### KeskOS Theme

Purpose:

- manage the current KeskOS visual identity
- switch between KeskOS styling and KDE defaults

Current rule:

- the KeskOS accent color is fixed to `#ce6a35`
- custom accent colors are not supported yet

Controls:

- current accent color display
- read-only color swatch
- theme mode display:
  `KeskOS Orange` or `KDE Defaults`
- `Apply KeskOS Orange`
- `Switch to KDE Defaults`
- `Reset KeskOS Theme`

Current implementation:

- `Apply KeskOS Orange` reuses `kesk-apply-theme`
- `Switch to KDE Defaults` uses `kesk-apply-kde-defaults`
- the KDE defaults path currently restores a stock Breeze Dark-style stack where safely supported

Support level:

- `Limited`

### Panels & Launcher

Purpose:

- manage the KDE launcher and the KeskOS panel layout

Current rule:

- KeskOS currently uses the KDE launcher only
- other launcher backends are not available

Controls:

- read-only launcher backend: `KDE Launcher`
- launcher shortcut:
  `Meta`
  `Meta+Q`
  `Meta+Space`
- `Reset KDE Launcher Layout`
- `Reapply KeskOS KDE Panel Layout`
- disabled placeholders for launcher enabled, panel auto-hide, and workspace switcher where the current backend is not fully wired

Current implementation:

- shortcut changes update KDE shortcut config directly
- layout reset/reapply uses the existing panel reset flow

Support level:

- `Limited`

### Top Bar Widgets

Purpose:

- manage the KeskOS top bar widget layer

Current rule:

- the visible widgets are:
  `Media`
  `CPU`
  `Memory`
  `Network`

Controls:

- top bar widgets enabled toggle
- disabled placeholders for per-widget toggles
- disabled placeholder for refresh rate
- `Reset Top Bar Widgets`
- `Restart Top Bar Widgets`

Current implementation:

- enable/disable is tied to the current Quickshell autostart layer
- restart/reset uses the existing shell launcher path
- per-widget toggles and refresh-rate tuning are not connected yet

Support level:

- `Limited`

### Browser Defaults

Purpose:

- choose the default browser
- install supported browsers
- apply the KeskOS browser homepage/theme layer

Supported browsers:

- `LibreWolf`
- `Brave`
- `Zen Browser`
- `Firefox`

Current implementation:

- default browser uses `xdg-settings`, `xdg-mime`, and `mimeapps.list`
- install launches `pkexec pacman -S --needed --noconfirm <package>`
- browser theme/homepage apply uses the current KeskOS browser assets
- homepage settings button opens the selected browser’s internal homepage settings when available

Behavior notes:

- installs require confirmation
- a missing browser does not break the page
- unavailable packages are reported clearly
- homepage apply is disabled if homepage assets are missing

Support level:

- `Limited`

### Boot Splash

Purpose:

- expose boot splash status without pretending Plymouth support is finished

Current rule:

- Plymouth is not integrated yet

Status shown:

- `Under works`
- Plymouth installed: yes/no
- KeskOS Plymouth theme installed: yes/no
- current boot splash: detected theme or unavailable

Controls:

- disabled `Preview`
- disabled `Apply Boot Splash`
- `Open Boot Splash Docs`

Support level:

- `Under Works`

### KeskOS Version

Purpose:

- show read-only KeskOS build and system information

Typical fields:

- KeskOS version
- build layer
- ISO build date when available
- Git commit/build ID when available
- update channel
- base system
- kernel
- Plasma
- KDE Frameworks
- Qt
- graphics platform
- CPU
- GPU
- RAM
- disk

Links:

- `https://keskos.org`
- `https://docs.keskos.org`
- `https://github.com/memegeko/keskos`

Support level:

- `Native`

## Search Behavior

KeskOS custom KCM metadata is set up so these queries resolve to the right pages:

- `docs` and `help` find `Help`
- `website` and `github` find `About This System` and `KeskOS Version`
- `orange` and `kde defaults` find `KeskOS Theme`
- `launcher` finds `Panels & Launcher`
- `top bar`, `media`, `cpu`, `memory`, and `network` find `Top Bar Widgets`
- `browser`, `librewolf`, `brave`, `zen`, and `firefox` find `Browser Defaults`
- `boot splash` and `plymouth` find `Boot Splash`
- `version` and `build` find `KeskOS Version`

Removed from the normal user-facing search path:

- `User Feedback`
- the old `Experimental Features` idea

## What Is Native vs Limited

Native:

- `Help`
- `About This System`
- `KeskOS Version`

Limited:

- `KeskOS Theme`
- `Panels & Launcher`
- `Top Bar Widgets`
- `Browser Defaults`

Under Works:

- `Boot Splash`

## Testing

Basic checks:

```bash
systemsettings
kesk-apply-theme
kesk-theme-status
kcmshell6 --list
```

Useful module checks:

```bash
kcmshell6 kcm_kscreen
kcmshell6 kcm_pulseaudio
kcmshell6 kcm_access
```

What to confirm:

1. `Kesk Settings` still launches the real KDE System Settings app.
2. `User Feedback` is gone from the visible sidebar/search flow.
3. The visible `About This System` page is the KeskOS-owned page with Website, Docs, and GitHub buttons.
4. `Help` opens `https://docs.keskos.org`.
5. The `KeskOS` category exists and contains:
   `KeskOS Theme`, `Panels & Launcher`, `Top Bar Widgets`, `Browser Defaults`, `Boot Splash`, `KeskOS Version`
6. The theme stays dark/orange with the sharp KeskOS styling.
7. Unsupported controls are disabled instead of silently doing nothing.

## Known Limitations

- The app layout is still KDE System Settings. KeskOS customizes appearance and adds selected custom KCMs, but it does not replace the real KDE settings structure.
- KDE defaults switching currently restores a safe Breeze Dark-style stack rather than every possible stock Plasma preference on every system.
- Top Bar Widgets does not yet expose live per-widget enable/disable or refresh-rate tuning.
- Boot Splash is status-only for now because Plymouth integration has not been added yet.
- Browser theme/reset support is implemented for the supported browsers, but exact profile state still depends on whether the user has launched that browser before.
