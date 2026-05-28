# ISO Package Strategy

KeskOS treats this repository as the ISO/profile repo, not the long-term source tree for every packaged app, theme, or desktop component.

Release ISO builds should install KeskOS packages from pacman repositories:

- `[keskos]` for published KeskOS packages
- `[core]` and `[extra]` for upstream Arch packages

`[keskos-local]` remains available only for explicit local development overrides.

Release branding follows the same repo-first rule. The visible product line, layer, channel, build ID, and support URLs come from `keskos-release` metadata:

- `/etc/keskos-release`
- `/usr/lib/keskos/branding.json`

Apps and tools should read those files instead of hardcoding layer names in their own source trees.

## Release Build Model

Default mode:

```bash
KESKOS_BUILD_MODE=release ./build.sh
```

Release mode rules:

- no local `keskos-*` package builds
- no local browser package builds
- no local app source builds
- no automatic injection into `[keskos-local]`
- fail early if required KeskOS packages are missing from the configured pacman repos

That means the normal ISO build consumes package names such as:

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

The required validation list lives in:

- `config/keskos-required-packages.txt`

## Local Development Mode

Use local-dev mode only when you intentionally want override packages in `[keskos-local]`:

```bash
KESKOS_BUILD_MODE=local-dev ./build.sh
```

Optional local-dev flags:

```bash
KESKOS_BUILD_MODE=local-dev \
KESKOS_BUILD_SYSTEMSETTINGS_OVERRIDE=1 \
KESKOS_BUILD_CALAMARES_OVERRIDE=1 \
KESKOS_LOCAL_PACKAGES="my-test-package" \
KESKOS_LOCAL_PACKAGE_ROOT=/path/to/packages \
KESKOS_LOCAL_REPO_SOURCE_DIR=/path/to/prebuilt-pkgs \
./build.sh
```

Browser package builds are also local-dev only:

```bash
KESKOS_BUILD_MODE=local-dev KESKOS_BUILD_BROWSER_PKGS=1 ./build.sh
```

If no local override packages are built or imported, `[keskos-local]` stays unused.

## Browser Rule

Browsers are no longer preinstalled in the default ISO payload.

The ISO seed must not include:

- `brave-bin`
- `librewolf-bin`
- `zen-browser-bin`

Browser choice now happens in `Kesk Welcome` after install.

The ISO still includes the helper pieces needed for that flow:

- `keskos-welcome`
- `keskos-browser-startpage`
- `xdg-utils`
- `networkmanager`
- `plasma-nm`

`keskos-browsers-meta` is currently not part of the ISO seed because the standalone package still depends on `firefox`. Until that package is slimmed down to helper assets only, the ISO relies on `keskos-welcome` plus `keskos-browser-startpage` for the browser handoff.

## Why This Repo-First Model Exists

This keeps the ISO repo focused on:

- Archiso profile files
- bootloader config
- live-session `airootfs` behavior
- Calamares config that is still ISO-owned
- build orchestration and validation
- documentation

It avoids keeping duplicate app and package source trees here when those same packages already have their own package repos and are published to `[keskos]`.

## Testing Package Resolution

Check required KeskOS package availability before a build:

```bash
./scripts/check-keskos-repo-packages.sh
```

Run the normal release build:

```bash
KESKOS_BUILD_MODE=release ./build.sh
```

Run the safe validation path without starting `mkarchiso`:

```bash
KESKOS_BUILD_MODE=release ./build.sh --check
```

Only skip the public repo preflight when debugging:

```bash
./build.sh --skip-repo-check
```

## Publish Before Building

If a required KeskOS package changed, publish that package to the KeskOS pacman repo first, then rebuild the ISO.

The ISO repo should consume published package outputs instead of carrying duplicate source trees for:

- apps
- desktop shell packages
- branding/theme packages
- browser helper packages
- meta packages

That applies to release metadata too. Updating the public brand from `KeskOS // Layer 4` to `KeskOS // Layer 5` should happen through a new `keskos-release` package build, not by editing each app independently.

## Installer Expectations

Calamares still installs the package set baked into the ISO.

Because browsers are no longer part of that default payload:

- a fresh install may boot with no browser installed yet
- `Kesk Welcome` remains responsible for browser selection and install
- skipping the browser page leaves the system usable, but without a browser until the user installs one later

## Branding Refresh

On installed systems, `keskos-release` and `keskos-tools` refresh branding through:

- `kesk refresh-branding`
- `/usr/share/libalpm/hooks/keskos-branding-refresh.hook`

That refresh path updates `/etc/os-release` and any generated startpage branding metadata after package upgrades. Static installer, login, or boot-theme text still changes when their own packages are rebuilt.
