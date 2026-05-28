# KeskOS Calamares Installer

KeskOS now keeps Calamares focused on core OS deployment, then hands first-boot personalization to `Kesk Welcome` after login.

Flow:

1. Live ISO boots into the themed Plasma session.
2. Calamares runs with the KeskOS black/orange branding.
3. Calamares walks the streamlined deployment flow:
   - `01 PRE-FLIGHT`
   - `02 LOCATION`
   - `03 KEYBOARD`
   - `04 DISK TARGET`
   - `05 USER PROFILE`
   - `06 DEPLOY REVIEW`
   - `07 INSTALL`
   - `08 COMPLETE`
4. During install, Calamares applies the required KeskOS desktop defaults non-interactively.
5. The installed system reboots into the configured desktop, where `Kesk Welcome` continues personalization after login.

## Files

Calamares config:

- `calamares/settings.conf`
- `calamares/modules/keskos-review.conf`
- `calamares/modules/keskoschoices.conf`
- `calamares/modules/packages.conf`
- `calamares/modules/prepare-target.conf`
- `calamares/modules/postinstall.conf`

Build note:

- release `build.sh` runs now consume the published package set from the configured pacman repos instead of building duplicate local `keskos-*` package trees.
- local override builds such as patched `calamares`, patched `systemsettings`, or browser AUR packages are available only in `KESKOS_BUILD_MODE=local-dev` with explicit opt-in flags.

Calamares branding:

- `calamares/branding/keskos/branding.desc`
- `calamares/branding/keskos/stylesheet.qss`
- `calamares/branding/keskos/show.qml`
- `calamares/branding/keskos/keskosreview.qml`

Custom install helpers:

- `airootfs/usr/lib/calamares/modules/keskoschoices/main.py`
- `airootfs/usr/share/keskos/installer/package-manifest.json`
- `airootfs/usr/lib/keskos-installer/apply-install-choices.sh`
- `airootfs/usr/local/bin/keskos-postinstall-root`
- `airootfs/usr/local/bin/keskos-configure-user`

## Module Order

Show phase:

1. `welcome`
2. `locale`
3. `keyboard`
4. `partition`
5. `users`
6. `notesqml@keskos_review`

Exec phase:

1. partition / mount / unpack
2. target prepare shell hook
3. locale / initramfs / users / displaymanager / network / clock
4. `keskoschoices`
5. `packages`
6. services / bootloader
7. postinstall shell hook, including install-report source generation and success send
8. umount

## Deployment Defaults

The interactive loadout pages are gone from Calamares. Instead, the hidden `keskoschoices` module resolves a fixed deployment profile and writes the normal install-choice artifacts used by the post-install scripts.

Default behavior in the current flow:

- does not install browser packages during Calamares
- defers browser selection and browser package installation to `Kesk Welcome`
- skips browser theme / startpage apply during Calamares when no browser package is present
- leaves HTTP/HTML browser defaults unset when the target system has no installed browser yet
- applies required desktop defaults such as theme, layout, and SDDM branding automatically
- preserves the normal install-choice JSON and package list outputs used by post-install hooks

The review page shows a terminal-style deployment summary and explicitly tells the user that personalization continues in `Kesk Welcome` after login.

## What Calamares Still Owns

- pre-flight checks
- locale / location
- keyboard
- disk target / partitioning
- user profile
- deploy review
- package install
- post-install defaults
- reboot / completion

## What Kesk Welcome Owns

- network / uplink
- browser selection
- top bar widgets
- optional apps
- theme check
- system links
- finish / install report

## Browser Packages

Supported browser packages remain defined in:

- `airootfs/usr/share/keskos/installer/package-manifest.json`

That manifest is now used only as browser metadata for the installer handoff. Calamares no longer preinstalls those browser packages into the default ISO payload.

## Automatic Branding / Defaults

Required defaults that still apply automatically during install:

- KeskOS base theme
- default KDE layout
- default SDDM theme when present
- required desktop packages
- Kesk Welcome handoff after login

`apply-install-choices.sh` still reads:

- `/var/lib/keskos/install-choices.json`

That keeps the post-install pipeline stable even though the visible choice pages are gone.

## Output Files

The streamlined flow still writes:

- `/tmp/keskos-install-choices.json`
- `/tmp/keskos-final-packages.txt`
- `/tmp/keskos-install-session.json`
- `/var/lib/keskos/install-session.json`
- `/var/lib/keskos/install-choices.json`
- `/var/lib/keskos/install-report-source.json`
- `/var/lib/keskos/final-packages.txt`
- `/var/log/keskos-install.log`

## Install Reporting

- successful installs send a sanitized JSON report to `https://api.keskos.org/install-report`
- failed installs send a sanitized failure report from the installer wrapper
- the installer never sends directly to Discord

## Debugging

Check resolved install defaults in the live session:

```bash
cat /tmp/keskos-install-choices.json
cat /tmp/keskos-final-packages.txt
```

Check target install log:

```bash
cat /var/log/keskos-install.log
```

Run Calamares with debug logging:

```bash
calamares -d
```

Validate the first-boot browser flow manually:

```bash
kesk welcome-rerun
```

## Extending The Installer

Adjust the manifest and silent defaults:

- `airootfs/usr/share/keskos/installer/package-manifest.json`
- `calamares/modules/keskoschoices.conf`

Change the deploy review UI:

- `calamares/branding/keskos/keskosreview.qml`

Adjust target apply logic:

- `airootfs/usr/lib/keskos-installer/apply-install-choices.sh`

Adjust package resolution logic:

- `airootfs/usr/lib/calamares/modules/keskoschoices/main.py`

Archived installer experiments:

- `.old_experiments/calamares-loadout/`
