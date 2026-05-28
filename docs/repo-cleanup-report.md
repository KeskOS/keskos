# Repo Cleanup Report

This report covers the ISO/build repo cleanup after moving most KeskOS packages and apps into the published `[keskos]` pacman repo.

## Removed

| Path | Reason | Replacement package or reason obsolete |
| --- | --- | --- |
| `apps/kesk-welcome/` | Duplicate in-repo app source tree | `keskos-welcome` from `[keskos]`; maintained in standalone `KeskOS/keskos-welcome` |
| `packages/keskos-*/` local export folders | Duplicate local package exports in the working tree | Published `keskos-*` packages from `[keskos]` |
| `out/` | Generated ISO/package output | Obsolete generated build output; rebuilt as needed |
| `airootfs/usr/lib/kesk/**/__pycache__/` | Generated Python cache | Obsolete generated cache |
| `docs/examples/__pycache__/` | Generated Python cache | Obsolete generated cache |
| `scripts.md` | Empty, unreferenced file | Obsolete |
| `wp4997020.jpg` | Unreferenced stray root-level asset | Obsolete |

## Kept

| Path | Reason it is still required |
| --- | --- |
| `build.sh` | Main ISO build entry point |
| `packages.x86_64` | Canonical ISO seed package list |
| `pacman.conf` | Repo priority and pacman template for mkarchiso |
| `profiledef.sh` | Archiso profile metadata |
| `airootfs/` | Live ISO boot/runtime files and first-boot/install helpers |
| `calamares/` | ISO-owned Calamares config, branding, and patch helpers |
| `config/keskos-required-packages.txt` | Required package validation list for release builds |
| `airootfs/etc/pacman.d/keskos.conf` | Installed pacman repo config for target systems |
| `packages/kesk-settings-kcms/` | Compatibility wrapper for the legacy package name |
| `packages/kesk-welcome/` | Compatibility wrapper for the legacy package name |
| `buildwsl.sh` | WSL-specific build helper for sanitized workspace builds |
| `airootfs/etc/os-release` | Live ISO build-time branding template; still needed for the booted image before installed-system package refresh takes over |
| `scripts/check-keskos-repo-packages.sh` | Repo availability preflight used by `build.sh` |
| `scripts/check-branding.sh` | Central branding consistency check for release metadata and user-facing source trees |
| `scripts/check-repo-cleanliness.sh` | Repo hygiene validation added in this cleanup pass |

## Needs Manual Review

| Path | Why uncertain | Recommendation |
| --- | --- | --- |
| `assets/` | Looks duplicate from a package-source perspective, but runtime helpers still resolve installed source data through `/usr/share/keskos/source` | Keep for now; remove only after packaged source-data coverage is confirmed |
| `browser-home/` | Mirrors packaged browser startpage assets | Keep until packaged source-data path is verified end to end |
| `configs/` | Large source-data tree still used by installed source fallbacks and helper scripts | Keep for now; trim only after runtime helpers no longer depend on installed source snapshots |
| `desktop/` | Launcher metadata may still be expected by installed source-data consumers | Keep until launcher/runtime fallback path is fully package-owned |
| `scripts/build-all-packages.sh` | Still assumes in-repo package trees beyond the remaining compatibility wrappers | Review or retire after package publishing workflow is fully repo-first |
| `scripts/check-packages.sh` | Validates in-repo package definitions that mostly no longer live here | Review or retire after compatibility-wrapper workflow is settled |
| `scripts/export-package-sources.sh` | Legacy export helper from the old package-source model | Keep only if still needed for migration; otherwise retire later |
| `scripts/publish-package-repos.sh` | Legacy package repo staging helper from the old in-repo package model | Review against the current standalone package repo workflow |
| `scripts/test-keskos-local-repo.sh` | Local repo helper may still be useful, but it targets the older duplicate-source workflow | Review and update for the current local-dev override flow if still needed |
| `keskos-browsers-meta` standalone package | Current standalone package still depends on `firefox`, which would reintroduce a preinstalled browser | Trim the package upstream to helper assets only before adding it back to the ISO seed |

## Duplicated Packages Found

The audit found duplicate local package/app sources for these repo-provided package names:

- `keskos-release`
- `keskos-keyring`
- `keskos-mirrorlist`
- `keskos-tools`
- `keskos-branding`
- `keskos-theme`
- `keskos-settings`
- `keskos-welcome`
- `keskos-plasma-layout`
- `keskos-quickshell-hud`
- `keskos-kickoff`
- `keskos-workspace-switcher`
- `keskos-browser-startpage`
- `keskos-plymouth`
- `keskos-sddm-theme`
- `keskos-calamares-branding`
- `keskos-installer-debug-log`
- `keskos-core-meta`
- `keskos-desktop-meta`
- `keskos-browsers-meta`
- `keskos-system-tools-meta`

## Local Build Logic Removed Or Gated

- Release mode is now the default: `KESKOS_BUILD_MODE=release`
- Release mode refuses local package builds and `[keskos-local]` overrides
- Browser package builds are local-dev only: `KESKOS_BUILD_BROWSER_PKGS=1`
- Patched `systemsettings` override is local-dev only: `KESKOS_BUILD_SYSTEMSETTINGS_OVERRIDE=1`
- Patched `calamares` override is local-dev only: `KESKOS_BUILD_CALAMARES_OVERRIDE=1`
- `build.sh --check` validates the repo, package seed, pacman config generation, and package resolution before exiting

## Central Branding Model

KeskOS now treats `keskos-release` as the source of truth for user-visible release metadata:

- `/etc/keskos-release`
- `/usr/lib/keskos/branding.json`

Apps, tools, and first-boot flows should read those files instead of hardcoding `Layer 4` or old edition labels. Static installer, login, and boot-theme assets are still package-controlled, so they update when their package is rebuilt.

## Package Names Still Expected From `[keskos]`

- `keskos-release`
- `keskos-keyring`
- `keskos-mirrorlist`
- `keskos-tools`
- `keskos-branding`
- `keskos-theme`
- `keskos-settings`
- `keskos-welcome`
- `keskos-plasma-layout`
- `keskos-quickshell-hud`
- `keskos-kickoff`
- `keskos-workspace-switcher`
- `keskos-browser-startpage`
- `keskos-plymouth`
- `keskos-sddm-theme`
- `keskos-calamares-branding`
- `keskos-installer-debug-log`
- `keskos-core-meta`
- `keskos-desktop-meta`
- `keskos-system-tools-meta`

`keskos-browsers-meta` is intentionally not in the current ISO seed because its standalone package still depends on `firefox`.

## Browser Packages Removed From The ISO Path

These are not part of `packages.x86_64` and are not built by default:

- `brave-bin`
- `librewolf-bin`
- `zen-browser-bin`

Browser installation is deferred to `Kesk Welcome` after first boot.

## Tests And Build Checks Run

- `bash -n build.sh`
- `bash -n scripts/check-keskos-repo-packages.sh`
- `bash -n scripts/export-package-sources.sh`
- `bash -n scripts/build-keskos-release.sh`
- `bash -n scripts/check-repo-cleanliness.sh`
- `bash -n scripts/check-branding.sh`
- `./scripts/check-branding.sh`
- `./scripts/check-repo-cleanliness.sh`
- `grep`/`rg` validation for browser-package absence in `packages.x86_64`
- `grep`/`rg` validation for required KeskOS package names in `packages.x86_64`

## Known Remaining Cleanup Items

1. Decide whether `assets/`, `browser-home/`, `configs/`, and `desktop/` should remain as installed source-data inputs or be replaced fully by package-owned source snapshots.
2. Trim `keskos-browsers-meta` upstream so it no longer depends on `firefox`, then decide whether it belongs back in the ISO seed.
3. Review the legacy package export/publish helper scripts under `scripts/` and either modernize them for the standalone package-repo workflow or retire them.
