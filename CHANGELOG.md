# Changelog

## 2026-05-15

### Launcher cleanup, branded panel defaults, and Plasma polish

KeskOS moved fully onto the branded Plasma launcher and panel path, cleaned out the dead Wolfi/Rofi-era install flow, and tightened the desktop defaults around a reusable KDE panel layout.

### Added

- `org.kde.plasma.simplekickoff` patch set for the branded `Kesk Kickoff` launcher
- `docs/keybinds.md` for the current enforced shortcut map
- `docs/launcher-switching.md` for launcher mode behavior and recovery
- `docs/plasma-panel-layout.md` for the branded panel structure and reset flow
- `docs/repository-structure.md` for the current repo layout
- `keskos-reset-panel` for safe, repeatable panel resets with backup
- system-wide `org.keskos.plasma.defaultPanel` layout template
- branded panel wrapper desktop entries and fixed panel icon assets

### Changed

- switched the active launcher path from old Wolfi/Rofi-era code to the branded patched Plasma launcher
- made the branded bottom panel the intended default layout for fresh users and resets
- simplified the bottom panel by removing the stock right-side tray and clock cluster
- updated launcher branding to use the real KeskOS logo in the panel button and metadata paths
- refreshed README/docs to describe the current Plasma launcher and panel workflow instead of the old custom runner stack

### Removed

- removed the old live install path for Wolfi/Rofi launcher scripts from the active build
- removed dead launcher desktop entries, dead Rofi configs, and the old `launcher/kesk_runner` runtime from the active tree
- removed the abandoned Calamares `keskosloadout` experiment from the active install flow

### Archived

- moved the old Wolfi/Rofi launcher stack into `.old_rolfi/`
- moved dead Calamares loadout and placeholder launcher icon experiments into `.old_experiments/`

### Fixed

- fixed taskbar launcher pins so they use explicit branded desktop wrappers and panel icon assets
- fixed the launcher logo path so the branded panel button no longer falls back to the broken placeholder state
- fixed panel layout drift by making the compact launcher button truly icon-first and centered
- fixed duplicate/extra panel state in the branded panel script and reset path
- fixed build staging after the old launcher tree was removed from the active source layout

## 2026-05-08

### Installer console, browser loadout, and release routing

KeskOS continued the shift from a themed live ISO into a more complete product flow, with install-time browser and software selection, better release-facing docs, and a clearer website/download split.

### Added

- `ROADMAP.md` for tracked project direction, active work, and future milestones
- Calamares software loadout steps for browser, bundles, feature flags, and add-ons
- Calamares deploy review step
- installer-side browser theme and startpage application path
- build-time Calamares UI patching for KeskOS installer polish

### Changed

- moved post-install personalization away from a forced first-login setup app and into Calamares
- updated the README to point users to:
  - `https://keskos.org` as the main website
  - `https://download.keskos.org` as the primary download location
- refreshed the README installer section and screenshot references for the current ISO flow
- changed browser handling so the selected browser is staged through the ISO workflow instead of falling back to Firefox by default
- updated release-facing docs to better reflect the current installer and desktop direction

### Fixed

- fixed multiple Calamares module load and branding failures during the custom installer work
- fixed the dark installer progress page so it no longer drifts onto an off-center white canvas
- fixed package manager preparation failures caused by the optional package step forcing `pacman -Sy`
- fixed browser packaging flow so selected browsers no longer silently collapse back to Firefox
- fixed the multi-select package/add-on checkbox interaction path in the patched Calamares chooser flow

### Notes

- GitHub remains the source and release mirror
- the public download path should now be treated as `download.keskos.org`
- the public project site should now be treated as `keskos.org`

## 2026-05-01

### Release focus and ISO polish

KeskOS now reads and behaves much more like a real operating system release rather than a repo for an old rice script workflow.

### Added

- official release-targeted ISO artifact:
  - `keskos-2026.05.01-x86_64.iso`
- seam-free custom QML KWin decoration theme
- improved live Calamares debug stream and installer logging
- more complete release screenshot set for desktop and installer flow

### Changed

- rewrote the README around the released ISO instead of the developer build tree
- expanded the README to present KeskOS as a real OS with desktop, installer, branding, and workflow features
- added a proper screenshot gallery for launcher, browser, terminal, lock screen, and installer steps
- adjusted the README release section to reflect the shipped GitHub release asset format
- tuned the custom titlebar branding and window decoration polish
- improved the Calamares install screen layout so it stays dark and readable during live install progress

### Fixed

- removed the visible seams/gaps from the custom window border by moving to a QML-based decoration path
- fixed titlebar icon placement and sizing
- fixed the Calamares install view white background problem
- fixed overlapping live debug text in the installer slideshow
- fixed live-session launcher subpage failures so blank pages fall back more safely
- fixed multiple ISO/live-install issues in the Calamares and mkinitcpio pipeline

### Notes

- the README is now intended to support the GitHub Releases page first
- the release asset is published as a compressed `.iso.zst` because the raw ISO is slightly above GitHub's `2 GiB` asset limit
- the old script installer remains preserved on `legacy-script-installer`

## 2026-04-27

### Remove broken release automation

The GitHub Actions ISO release pipeline was removed from `main`. KeskOS releases are now published manually after a local `./build.sh` and test pass.

### Changed

- removed the broken GitHub Actions ISO release workflow
- removed the CI/container-only build path from `build.sh`
- rewrote the README to describe manual release publishing instead of tag-triggered automation

## 2026-04-26

### Convert KeskOS to an ISO project

`main` is no longer the old script-based desktop installer. It is now an Archiso project that boots to KDE Plasma and installs through Calamares.

### Added

- `build.sh`
- `profiledef.sh`
- `packages.x86_64`
- `pacman.conf`
- `airootfs/`
- `calamares/`
- `browser-home/`
- live-session helper scripts under `airootfs/usr/local/bin/`
- Calamares branding under `calamares/branding/keskos/`

### Changed

- switched the project layout to an Archiso-style tree
- added a local AUR-backed package repo flow for `calamares` and `kdotool-bin`
- made the live ISO boot into an autologin KDE Plasma desktop
- added a proper `Install KeskOS` desktop shortcut and launcher entry
- moved launcher, HUD, wallpaper, Konsole, SDDM, lock screen, and splash assets into a system-wide live/install flow
- changed launcher/browser/Quickshell paths away from the old `~/.local` installer layout and into `/usr/local/bin` and `/usr/local/share/keskos`
- added a Calamares post-install hook that removes live-only pieces and applies installed-user defaults
- rewrote the README for the ISO workflow
- aligned the ISO profile to the supported `bios.syslinux` + `uefi.grub` boot path and added the missing host/package requirements for release builds
- removed the invalid `ttf-vt323` package reference so the ISO package set resolves cleanly on Arch

### Preserved

- the old script-based installer was moved safely to the `legacy-script-installer` branch
- that branch was committed with:
  - `Preserve legacy script-based installer`

### Notes

- `build.sh` now handles repo paths with spaces by generating a URI-safe local pacman repo URL
- `main` intentionally no longer ships the old `install.sh` workflow
- use `git checkout legacy-script-installer` if you want the original script installer back
