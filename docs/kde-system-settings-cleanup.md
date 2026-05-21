# KDE System Settings Cleanup

KeskOS uses the real KDE Plasma System Settings application as its official settings app:

- `systemsettings`
- launcher branding: `Kesk Settings`

KeskOS does not replace System Settings with a custom control center.

## Goal

KDE ships many KCM modules that are useful for debugging, mobile devices, inspection, or niche workflows.
KeskOS keeps those modules installed, but hides a curated subset from the normal System Settings UI so the default desktop feels cleaner and more focused.

This cleanup does **not**:

- uninstall KDE packages
- delete KCM binaries
- patch KDE System Settings source code
- break direct access through `kcmshell6`

## How It Works

KeskOS uses KDE's own Kiosk control-module restrictions in `kdeglobals`:

- system scope: `/etc/xdg/kdeglobals`
- user fallback scope: `~/.config/kdeglobals`

The managed block looks like:

```ini
[KDE Control Module Restrictions][$i]
kcm_kaccounts=false
kcm_wayland=false
```

That keeps the real KDE stack intact while hiding selected modules from the normal System Settings shell where KDE honors the restriction.

No upstream module metadata, plugin binaries, or package files are deleted or modified.

## Hidden Lists

Default hidden modules:

- `/usr/share/kesk/settings/hidden-kcms.conf`

Optional extra hidden modules:

- `/usr/share/kesk/settings/hidden-kcms-extra.conf`

System reference list captured from the shipped image:

- `/usr/share/kesk/settings/kcm-default-list.txt`

## Commands

List modules and the configured hide lists:

```bash
kesk-list-kcms
```

Apply the default hide list:

```bash
sudo kesk-hide-kcms
```

Apply the default hide list plus the optional extra list:

```bash
sudo kesk-hide-kcms --include-extra
```

Restore the normal module visibility:

```bash
sudo kesk-restore-kcms
```

List all currently available KCMs directly:

```bash
kcmshell6 --list
```

## Backups And Logs

System-level backups:

- `/var/lib/kesk/kcm-metadata-backups/`

System log:

- `/var/log/kesk/kcm-hide.log`

User fallback backups:

- `~/.local/state/kesk/kcm-metadata-backups/`

User fallback log:

- `~/.local/state/kesk/logs/kcm-hide.log`

Because KeskOS uses KDE's official restriction mechanism, the backup is of the managed `kdeglobals` state rather than per-module plugin metadata.

## Notes

- `kcmshell6 --list` may still list modules that are hidden from the normal System Settings UI.
- Direct module launching with `kcmshell6 <module-id>` is intentionally preserved.
- Core desktop settings such as Display, Sound, Firewall, Accessibility, Login Screen, Users, Power, and About This System remain visible by default.
- `User Feedback` is hidden by default.
- The stock KDE `About This System` KCM is hidden by default and replaced in the visible UI by the KeskOS-owned `About This System` page.
- Mobile-only, debug/info, server/niche, and duplicate-feeling modules are the main targets for hiding.

## Restore Example

If you want the stock KDE visibility back:

```bash
sudo kesk-restore-kcms
systemsettings
```

If you only want to inspect a hidden page temporarily, you can still open it directly:

```bash
kcmshell6 kcm_wayland
kcmshell6 kcm_kaccounts
```
