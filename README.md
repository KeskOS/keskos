# KeskOS

`keskos` is the main ISO and Archiso build repository for the KeskOS distribution. It assembles the live image, Calamares installer, package seed lists, and staged filesystem overlay that turn the published pacman packages into a bootable installer.

## What this is

This repository contains the ISO build script, Archiso profile pieces, live-root overlay files, installer branding/configuration, and the package seed list used to compose a release image.

## Role in KeskOS

ISO and build repository.

## Package name

```txt
Primary output: KeskOS installable ISO image
Local package sources: packages/* within this repository
Target architecture: x86_64
```

## What it installs or provides

- `build.sh` stages the Archiso profile and runs `mkarchiso`.
- `packages.x86_64` defines the explicit package seed for the live ISO.
- `airootfs/`, `configs/`, `desktop/`, `calamares/`, and `assets/` provide the live-session and installer payload.
- `docs/` and `CHANGELOG.md` track build strategy and release notes.

## Commands and launchers

- `./build.sh` builds the ISO as a regular user and escalates only for `mkarchiso`.
- `./scripts/apply-kesk-simplekickoff.sh` installs the local launcher override into the current Plasma profile for desktop testing.
- This repo does not install an end-user GUI launcher by itself; it produces the ISO image.

## Config, logs, and state

- Main build inputs live in `packages.x86_64`, `pacman.conf`, `profiledef.sh`, `calamares/`, and `docs/`.
- Build output lands in `out/`.
- Build logs are emitted by `build.sh` and `mkarchiso` in the terminal session that ran the build.

## Dependencies

- Core build tooling: `archiso` / `mkarchiso`, `git`, `rsync`, `sudo`, and `repo-add`.
- Package resolution depends on the configured `[keskos]`, `[core]`, and `[extra]` repositories in `pacman.conf`.
- Some local-development paths also rely on `makepkg` and AUR build dependencies when package overrides are enabled.

## Build

```bash
./build.sh
KESKOS_ISO_VERSION=2026.05.27 ./build.sh
./build.sh --use-local-packages
KESKOS_LOCAL_PACKAGE_DIRS=/path/to/keskos-desktop/dist:/path/to/keskos-settings ./build.sh --use-local-packages
```

## Packaging notes

- This repo is not a single pacman package; its primary output is the installable ISO image.
- Desktop shell and branding sources now live in `KeskOS/keskos-desktop`; this repo should consume their published packages rather than re-own their long-term development.
- App, helper, and meta-package sources remain in their own repos and are consumed here through pacman package names.
- `./build.sh --use-local-packages` is an opt-in development path that stages prebuilt local package archives into `keskos-local` and appends a local test package set to the live package seed without changing the default build flow.

## Troubleshooting

- Run `build.sh` as a regular user. It will fail early if started as root.
- If a package cannot be resolved during staging, check `packages.x86_64`, repo availability, and the relevant package repo publish status.
- If pacman reports checksum or size mismatches, refresh the package repo contents before retrying the ISO build.

## Docs website export notes

- Good website split: overview, build process, installer payload, package strategy, and troubleshooting.
- Keep the command blocks stable so they can be copied directly into the docs site build guide.
