# Building the ISO from the KeskOS Pacman Repo

The ISO repo now consumes published KeskOS packages instead of keeping duplicate in-tree package exports for normal release builds.

## Source Of Truth

The package source of truth now lives in dedicated repos under `KeskOS`, then publishes to:

- `https://downloads.keskos.org/repo/`

Examples:

- `KeskOS/keskos-desktop`
- `KeskOS/keskos-welcome`
- `KeskOS/keskos-settings`
- `KeskOS/keskos-tools`
- `KeskOS/keskos-release`
- `KeskOS/keskos-desktop-meta`

This ISO repo should consume those package outputs by package name.

## Repo Priority

Release builds resolve packages in this order:

1. `[keskos]`
2. `[core]`
3. `[extra]`

Local development builds can optionally prepend:

1. `[keskos-local]`
2. `[keskos]`
3. `[core]`
4. `[extra]`

`[keskos-local]` is empty by default and should be used only for explicit overrides.

## Release Build

```bash
KESKOS_BUILD_MODE=release ./build.sh
```

Release mode:

- does not build local `keskos-*` package trees
- does not build browser AUR packages
- does not inject local builds into `[keskos-local]`
- validates required KeskOS packages before `mkarchiso`

Validation-only mode:

```bash
KESKOS_BUILD_MODE=release ./build.sh --check
```

## Local Development Build

```bash
KESKOS_BUILD_MODE=local-dev ./build.sh
```

Optional local-dev override examples:

```bash
KESKOS_BUILD_MODE=local-dev \
KESKOS_BUILD_SYSTEMSETTINGS_OVERRIDE=1 \
KESKOS_BUILD_CALAMARES_OVERRIDE=1 \
KESKOS_LOCAL_REPO_SOURCE_DIR=/path/to/prebuilt-pkgs \
./build.sh
```

## Required KeskOS Packages

The required package list is maintained in:

- `config/keskos-required-packages.txt`

Check it directly with:

```bash
./scripts/check-keskos-repo-packages.sh
```

That required set intentionally excludes:

- `brave-bin`
- `librewolf-bin`
- `zen-browser-bin`

Those browsers are no longer ISO requirements.

## What The ISO Repo Still Owns

This repo should continue to own:

- `build.sh`
- `packages.x86_64`
- `pacman.conf`
- `profiledef.sh`
- `grub/`
- `syslinux/`
- `efiboot/`
- `airootfs/` live-image behavior
- Calamares config and installer glue that is still ISO-specific
- docs and CI/build helpers

## What Should Not Be Duplicated Here

When a package already exists in `[keskos]`, this repo should not depend on an in-tree duplicate source export for release builds.

That includes:

- app sources
- packaged desktop shell sources
- packaged branding/theme assets
- browser package source trees
- package-local PKGBUILD exports that already live in standalone package repos

## Browser Flow

The ISO still carries the browser setup path:

- `keskos-welcome`
- `keskos-browser-startpage`

But the actual browser packages are installed later through `Kesk Welcome`.

`keskos-browsers-meta` is currently kept out of the ISO seed because the standalone package still depends on `firefox`, which would reintroduce a preinstalled browser.

## Debugging Missing Packages

If package validation fails:

1. confirm the package exists in its dedicated package repo
2. confirm it was built and published to `[keskos]`
3. rerun `./scripts/check-keskos-repo-packages.sh`

The ISO build should fail early instead of silently falling back to stale in-repo copies.
