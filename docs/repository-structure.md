# Repository Structure

This file describes the active high-level layout of the KeskOS ISO/build repository after the repo-first package cleanup.

## Active Top-Level Areas

- `airootfs/`
  - Files installed into the live ISO / target filesystem.
  - Includes runtime scripts, Calamares helpers, autostarts, and packaged browser theme assets.

- `build.sh`
  - Main ISO build entry point.
  - Defaults to `KESKOS_BUILD_MODE=release` and consumes published packages from `[keskos]`.

- `assets/`
  - Shared branding, wallpapers, splash assets, and installed launcher icon PNGs.
  - Current launcher icon theme files live under `assets/icons/hicolor/`.
  - Kept for now because runtime helpers still resolve installed source data through `/usr/share/keskos/source`.

- `browser-home/`
  - Local KeskOS browser startpage HTML/CSS/JS.
  - Kept for now because the packaged browser/startpage assets still mirror this source content.

- `calamares/`
  - KeskOS Calamares branding, module config, and build-time UI patches.

- `configs/`
  - Source configs mirrored into packaged desktop/runtime assets.
  - Notable active paths:
    - `configs/plasmoids/org.kde.plasma.simplekickoff/`
    - `configs/plasmoids/com.keskos.workspaceswitcher/`
    - `configs/plasma/keskos-bottom-panel.js`
    - `configs/plasma/layout-templates/org.keskos.plasma.defaultPanel/`
    - `configs/quickshell/keskos/`
    - `configs/sddm/keskos/`
    - `configs/look-and-feel/com.keskos.desktop/`

- `desktop/`
  - Desktop launchers for the default browser, files, terminal, and about entry.
  - Kept while the packaged source-data path still expects launcher metadata.

- `docs/`
  - Maintained project documentation for installer flow, launcher switching, desktop shell behavior, keybinds, and repo structure.

- `scripts/`
  - Build, validation, and maintenance helpers kept outside the installed ISO tree.
  - Notable active helpers:
    - `scripts/check-keskos-repo-packages.sh`
    - `scripts/check-repo-cleanliness.sh`
    - `scripts/apply-kesk-simplekickoff.sh`

## Active Launcher Path

The current working launcher path is:

- `configs/plasmoids/org.kde.plasma.simplekickoff/`

It is packaged for the ISO through the published KeskOS desktop packages rather than copied directly by `build.sh`.

It is wired into the panel by:

- `configs/plasma/keskos-bottom-panel.js`

It is configured for users by:

- `airootfs/usr/local/bin/keskos-configure-user`

Launcher switching/repair helpers:

- `airootfs/usr/bin/keskos-launcher-switch`
- `airootfs/usr/bin/keskos-fix-launcher`
- `airootfs/usr/bin/keskos-reset-panel`

## Archived / Retired Areas

- `.old_rolfi/`
  - Retired Wolfi/Rofi launcher stack and related helpers.

- `.old_experiments/`
  - Small archived development leftovers that are no longer part of the active build.
  - Current contents:
    - retired Calamares `notesqml` loadout experiment
    - retired launcher SVG placeholder icon

## Naming Conventions

Active branding now consistently prefers:

- `KeskOS` for product naming
- `Kesk Kickoff` for the patched launcher name
- `keskos-launcher` for the installed launcher icon theme name

## Safe Cleanup Rule

Before removing any file from the active tree:

1. Search for references in `build.sh`, `airootfs/`, `configs/`, `desktop/`, `docs/`, and `calamares/`.
2. Confirm it is not required for Archiso, Calamares, or the installed `/usr/share/keskos/source` runtime fallback path.
3. Prefer listing uncertain leftovers in `docs/repo-cleanup-report.md` for manual review instead of deleting immediately.
