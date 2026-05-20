# Kesk Settings

KeskOS now uses the real KDE Plasma System Settings application as the official settings app.

The branded launcher name is:

- `Kesk Settings`

But it launches:

- `systemsettings`

This phase does not replace KDE settings backends, does not fork System Settings, and does not add custom KeskOS KCM modules yet.

## Phase 1 Scope

Phase 1 only changes the presentation and default wiring around the existing KDE app:

- official KDE color scheme: `KeskOSDark`
- Kvantum widget style with the sharp `KeskOS` theme when the engine is available
- Breeze widget style as the safe fallback when Kvantum is unavailable
- existing KeskOS Plasma theme and window decoration where already available
- icon and cursor defaults applied with safe Breeze fallbacks
- branded launcher entry for the real KDE app

Phase 1 does not do any of the following:

- custom KCM modules
- hidden or removed KDE settings modules
- repair dashboards
- update dashboards
- Docker tooling
- log viewers
- package-manager frontends

## Official Launcher

The user-facing launcher is:

- `desktop/kesk-settings.desktop`

It is branded as:

- `Name=Kesk Settings`
- `Comment=Configure KeskOS and KDE Plasma settings`
- `Exec=systemsettings`
- `Icon=preferences-system`

The upstream KDE menu entry is hidden by a local override so the branded KeskOS launcher is the visible one:

- `desktop/systemsettings.desktop`

During image staging that override is installed under:

- `/usr/local/share/applications/systemsettings.desktop`

The old custom settings app is kept hidden as experimental:

- `desktop/keskos-settings.desktop`
- `Exec=kesk settings --experimental`
- `NoDisplay=true`

## Command Behavior

These commands are now the intended entry points:

```bash
systemsettings
kesk settings
```

`kesk settings` now launches the real KDE System Settings app instead of the custom PySide replacement UI.

Useful KCM commands:

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

Exact module names vary by distro package set. If one of the example modules is missing, check `kcmshell6 --list` and use the matching module name available on that system.

The old custom GUI is still available only as an experimental fallback:

```bash
kesk settings --experimental
```

It is not the default launcher and it is not the official settings app anymore.

## KCM Architecture

KDE Plasma System Settings is built around KCM modules.

A KCM is a KDE Configuration Module that can be loaded:

- inside `systemsettings`
- directly with `kcmshell6`

That means KeskOS can extend the real settings app later without forking it.
Future KeskOS pages should be added as real KCM plugins with metadata, QML/Kirigami UI, and backend logic where needed.

This phase does not add those plugins yet.

## System Settings Cleanup

KeskOS also ships a focused System Settings cleanup layer that hides mobile-only, debug/info, and niche KCM modules from the normal Settings UI while keeping the real KDE modules installed.

See:

- `docs/kde-system-settings-cleanup.md`

Useful commands:

```bash
kesk-list-kcms
sudo kesk-hide-kcms
sudo kesk-restore-kcms
```

## Theme Defaults

The official phase 1 visual stack is:

- color scheme: `KeskOSDark`
- widget style: `kvantum`
- Plasma desktop theme: `keskos-shell`
- window decoration: `kwin4_decoration_qml_keskos_split`
- icon fallback: `breeze-dark`
- cursor fallback: `breeze_cursors`
- Qt widget engine: `Kvantum` with the `KeskOS` theme when the engine is installed and safe to use
- fallback Qt widget engine: `Breeze` if Kvantum is missing or unstable

Palette targets:

- main background: `#050505`
- secondary background: `#070707`
- card/control background: `#0b0a09` and `#11100e`
- accent orange: `#ce6a35`
- text: `#b8afa6`
- muted text: `#8f8a84`
- disabled text: `#4c4845`

Readable mono-friendly defaults are kept for desktop fonts, preferring:

- JetBrains Mono
- Iosevka
- Noto Sans Mono

## Real KDE System Settings Theming

`Kesk Settings` still opens the real KDE System Settings application.

The stronger KeskOS appearance is applied through:

- KDE color scheme
- KDE globals such as `AccentColor` and `widgetStyle`
- Kvantum SVG styling for sharper Qt widgets when available
- Plasma desktop theme
- icon and cursor theme defaults
- optional Kvantum widget styling when the engine is available

This means KeskOS can strongly change:

- backgrounds
- accent colors
- button and field colors
- sidebar selection colors
- titlebar/decorations
- font defaults

Important detail:

- a KDE color scheme changes colors
- the Qt application style changes widget shapes
- Kvantum is what lets KeskOS remove most of the rounded Breeze feel from buttons, line edits, combo boxes, sliders, and sidebar selections

But KeskOS still cannot fully redesign the System Settings layout without:

- patching `systemsettings`
- forking KDE code
- or adding new custom KCM modules

That deeper UI restructuring is intentionally out of scope for this phase.

The old custom settings app remains hidden and experimental.

## Theme Apply Path

The active theme application path is now centralized in:

- `airootfs/usr/bin/kesk-apply-theme`

This script safely and idempotently applies:

- `KeskOSDark`
- `AccentColor=#ce6a35`
- `Kvantum` with the `KeskOS` theme when available
- `Breeze` as the safe fallback if Kvantum is missing
- `keskos-shell` Plasma theme when available
- icon and cursor theme defaults when available
- readable mono-ish font defaults
- the `KeskOS` Kvantum theme if the engine is installed

The desktop setup flow reuses that same script through:

- `airootfs/usr/local/bin/keskos-configure-user`

Theme apply logs are written to:

- `~/.local/state/kesk/logs/theme-apply.log`

The theme status/debug command is:

- `airootfs/usr/bin/kesk-theme-status`

It reports:

- current KDE color scheme
- current accent color
- current widget style
- current Plasma theme
- current icon theme
- current cursor theme
- current font
- whether Kvantum is installed
- current Kvantum theme if present
- whether the `KeskOS` Kvantum theme assets exist
- whether the branded launcher still points to `systemsettings`

Relevant files:

- `configs/kde/KeskOSDark.colors`
- `configs/kde/keskos.colors`
- `configs/Kvantum/KeskOS/`
- `configs/look-and-feel/com.keskos.desktop/contents/defaults`
- `airootfs/usr/bin/kesk-apply-theme`
- `airootfs/usr/bin/kesk-theme-status`
- `airootfs/usr/local/bin/keskos-configure-user`

## Testing

Use this checklist after building or booting the image:

1. Launch the real app directly:

```bash
systemsettings
```

2. Reapply the theme stack:

```bash
kesk-apply-theme
```

3. Inspect the current theme state:

```bash
kesk-theme-status
```

4. Launch the branded menu entry:

- open `Kesk Settings` from the KDE launcher

5. Confirm the launched window is the real KDE System Settings app, not the old custom PySide settings shell.

6. Confirm common KDE modules still load:

- display
- sound
- networking
- accessibility
- default applications
- file associations

7. Inspect available KCMs:

```bash
kcmshell6 --list
```

8. Reapply the KDE color scheme directly if you need to debug overrides:

```bash
plasma-apply-colorscheme KeskOSDark
```

9. Test representative modules:

```bash
kcmshell6 kcm_kscreen
kcmshell6 kcm_pulseaudio
kcmshell6 kcm_access
```

10. Confirm the visual result:

- near-black background
- dark sidebar
- orange selected sidebar item
- orange hover/selection accents
- darker, sharper buttons, combo boxes, and text fields
- readable text and controls
- no major Breeze blue accent remains
- no custom dashboard opens
- no light theme pages appear by default
- real KCM pages still open normally

If it still looks too default, check:

- `kesk-theme-status`
- `kreadconfig6 --file ~/.config/kdeglobals --group General --key ColorScheme`
- `kreadconfig6 --file ~/.config/kdeglobals --group General --key AccentColor`
- `kreadconfig6 --file ~/.config/kdeglobals --group KDE --key widgetStyle`
- whether `Kvantum installed` is `yes`
- whether `current Kvantum theme` resolves to `KeskOS`
- whether the app was already running and needs a full restart
- whether the user already has older KDE config overriding the new defaults

Existing users coming from older KeskOS or Plasma theme setups should rerun `kesk-apply-theme`.
The script now strips stale inline KDE color overrides from `~/.config/kdeglobals` before reapplying `KeskOSDark`, which helps the inner System Settings UI stop falling back toward a half-Breeze look.

## Known Limitations

- Modern System Settings pages use KDE Kirigami/QML, so layout and component structure are still fundamentally KDE even after strong recoloring and widget styling.
- Kvantum improves Qt Widgets and many embedded controls, but it does not fully restyle every Kirigami/QML component inside System Settings.
- Some upstream KDE pages may still show isolated upstream iconography or minor accent remnants until deeper Plasma theming work is done.
- Because stability matters more than extreme styling, Breeze remains the safe fallback whenever Kvantum is absent or not intended.
- Exact KCM names depend on the installed distro package set.
- This phase does not add native KeskOS pages inside System Settings yet.

## Future Custom KCM Modules

These are future ideas only and are not implemented in this task:

- KeskOS Theme
- Panels & Launcher
- HUD / Widgets
- Browser Defaults
- Dunst Notifications
- Boot Splash

When those arrive, they should be real KCM plugins loaded by KDE System Settings rather than a separate replacement control-center app.
