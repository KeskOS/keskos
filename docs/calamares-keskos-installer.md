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
- `build.sh` also stages `librewolf-bin`, `zen-browser-bin`, and `brave-bin` into the ISO-local repository so browser selection does not depend on the installed system fetching them later.
- browser AUR builds use a temporary build-only GPG home under the safe build root; if a browser binary package still cannot verify its upstream key, the build retries that browser package with `--skippgpcheck` and prints a warning.

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

## Software Loadout

The installer now uses native Calamares `packagechooser` steps for the interactive software flow. These write standard global-storage keys:

- `packagechooser_keskos_browser`
- `packagechooser_keskos_browser_theme`
- `packagechooser_keskos_bundles`
- `packagechooser_keskos_desktop_profile`
- `packagechooser_keskos_addons`

The review page reads those keys and renders the terminal-style deploy summary before install begins.

## Browser Selection

Browser choices:

- `librewolf`
- `zen`
- `brave`

Resolution rules:

- package candidates are defined in `package-manifest.json`
- the supported browsers are staged into the ISO from the KeskOS local AUR-built repository
- the resolver maps the selected browser to the packaged desktop and package identifiers used by the install scripts
- post-install cleanup removes the non-selected browsers so the installed system keeps only the chosen one

Post-install behavior:

- the selected browser is written into mime defaults
- the browser launcher path uses `xdg-open` first, so it follows the chosen default browser
- the Plasma taskbar browser launcher prefers the system default browser before falling back to hardcoded candidates

## Browser Theme / Startpage

The local startpage is installed at:

- `/usr/share/keskos/startpage/index.html`

Browser theme assets:

- `/usr/share/keskos/browser-themes/firefox/`
- `/usr/share/keskos/browser-themes/brave/`

Best-effort behavior:

- Firefox-family browsers get homepage policy files
- Brave gets managed startup / homepage policies
- if a browser-specific path is unavailable, the install keeps going and logs the partial apply

## Package Bundles And Extra Packages

Bundles are defined in:

- `airootfs/usr/share/keskos/installer/package-manifest.json`

The current installer supports:

- curated bundle selection
- browser selection
- browser theme toggle
- desktop profile selection
- system add-on selection

The current pass does **not** include a fully searchable pacman UI inside Calamares, and it no longer uses the abandoned custom `notesqml` loadout experiment.

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
