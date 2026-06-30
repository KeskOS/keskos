# KeskOS Calamares Installer

KeskOS now handles post-install personalization inside Calamares instead of forcing a welcome app on first login.

Flow:

1. Live ISO boots into the themed Plasma session.
2. Calamares runs with the KeskOS black/orange branding.
3. The `SOFTWARE LOADOUT` step collects:
   - default browser
   - browser theme/startpage toggle
   - optional package bundles
   - additional pacman package names
   - desktop / feature flags
4. The `DEPLOY REVIEW` step shows the queued choices.
5. During install, Calamares resolves package choices, installs optional packages, writes install choice logs, and applies the target configuration.
6. The installed system reboots directly into the configured desktop.

## Files

Calamares config:

- `calamares/settings.conf`
- `calamares/modules/keskos-review.conf`
- `calamares/modules/keskoschoices.conf`
- `calamares/modules/packages.conf`
- `calamares/modules/prepare-target.conf`
- `calamares/modules/postinstall.conf`

Build note:

- `build.sh` patches the upstream AUR `calamares` PKGBUILD so `packagechooser` and `packagechooserq` are not skipped at compile time. KeskOS depends on those modules being present in `/usr/lib/calamares/modules/`.
- Browsers are no longer staged by Calamares or preinstalled by the ISO. Browser installation/default selection is deferred to Kesk Welcome after first login, using pacman first and yay fallback where needed.

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
6. `packagechooser@keskos_browser`
7. `packagechooser@keskos_browser_theme`
8. `packagechooser@keskos_bundles`
9. `packagechooser@keskos_desktop_profile`
10. `packagechooser@keskos_addons`
11. `notesqml@keskos_review`

Exec phase:

1. partition / mount / unpack
2. target prepare shell hook
3. locale / initramfs / users / displaymanager / network / clock
4. `keskoschoices`
5. `packages`
6. services / bootloader
7. postinstall shell hook
8. umount

## Deployment Defaults

Calamares now handles deployment only: locale, keyboard, storage, users, package installation, display-manager setup, and the required KeskOS desktop defaults.

The `keskoschoices` module writes a small deployment payload for post-install hooks, but browser and optional-app personalization are intentionally deferred to Kesk Welcome after first login.

## Browser Selection

Browser choices are no longer made in Calamares and browser packages are no longer staged into the ISO by default.

Kesk Welcome owns this flow after first boot:

- LibreWolf, Brave, Zen Browser, and Firefox fallback are offered in Welcome.
- Package resolution uses pacman first and yay fallback where needed.
- Browser MIME/default-browser setup happens only after the user confirms a browser choice.
- If the user skips Welcome browser setup, no browser may be installed until the user installs one manually.

The installer records browser setup as `welcome` / deferred so install reports do not claim Calamares installed or selected a browser.

## Browser Theme / Startpage

The local startpage package remains available for Welcome and browser setup helpers:

- `/usr/share/keskos/startpage/index.html`

Welcome applies homepage/theme assets only when a selected browser exists and the relevant assets are installed.

## Package Bundles And Extra Packages

Optional application bundles are no longer forced by Calamares. First-boot personalization belongs to Kesk Welcome so offline installs can complete cleanly and optional package failures do not break OS deployment.

Install behavior:

- optional packages are added as `try_install`
- failures are logged and skipped
- base install continues
- Calamares does not force `pacman -Sy` before this step anymore
- if the live installer has no internet, the optional package step is skipped instead of aborting the install

Output files:

- `/tmp/keskos-install-choices.json`
- `/tmp/keskos-final-packages.txt`
- `/var/lib/keskos/install-choices.json`
- `/var/lib/keskos/final-packages.txt`
- `/var/log/keskos-install.log`

## Feature Flags

Current flags with real effect in this pass:

- Quickshell top bar
- KDE bottom taskbar
- Plasma theme
- window borders
- browser startpage
- SDDM theme
- Docker support
- Bluetooth support
- printing support

Recorded but still partial:

- Plymouth theme
- NVIDIA support beyond package install

## First-Run App Status

`keskos-first-run` still exists as a fallback/debug tool, but it is no longer part of the mandatory install flow.

Changes:

- no session-start launch
- autostart desktop files are shipped disabled
- manual use is still available for debugging

Run manually:

```bash
keskos-first-run --force
```

## Debugging

Check install choices in the live session:

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

Validate package availability manually:

```bash
pacman -Si librewolf
pacman -Si zen-browser
pacman -Si brave-browser
```

## Extending The Installer

Add or edit bundle groups:

- `airootfs/usr/share/keskos/installer/package-manifest.json`

Change the deploy review UI:

- `calamares/branding/keskos/keskosreview.qml`

Adjust target apply logic:

- `airootfs/usr/lib/keskos-installer/apply-install-choices.sh`

Adjust package resolution logic:

- `airootfs/usr/lib/calamares/modules/keskoschoices/main.py`

Archived installer experiments:

- `.old_experiments/calamares-loadout/`
