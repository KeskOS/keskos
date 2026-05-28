# Branding Strategy

KeskOS now treats release branding as shared system metadata instead of scattered hardcoded strings.

The current visible line is:

- `KeskOS // Layer 4`

That value should be updateable later through package upgrades. Moving to `Layer 5` should happen by rebuilding and publishing `keskos-release`, not by editing each app separately.

## Source Of Truth

The central branding files are:

- `/etc/keskos-release`
- `/usr/lib/keskos/branding.json`

Those files should expose:

- product name
- pretty name
- layer and layer name
- brand line
- channel
- build ID
- accent color
- public URLs

Technical IDs stay stable:

- `ID=keskos`

Do not replace technical IDs with pretty branding strings.

## Runtime Helpers

Shared branding helpers live in the `keskos-release` package:

- `/usr/lib/keskos/branding.sh`
- `/usr/lib/keskos/branding.py`

KeskOS apps and tools should read those helpers or the metadata files directly instead of hardcoding:

- `Layer 4`
- old `S.P.L.I.T.` edition labels
- per-app release names

## What Updates Automatically

After a `keskos-release` package upgrade:

- `kesk version`
- `kesk upgrade`
- `kesk doctor`
- `kesk repair`
- `Kesk Welcome`
- `Kesk Settings` About/Version
- browser startpage branding metadata

should all reflect the new brand line after the updated metadata is installed.

## What Still Needs A Package Rebuild

Some surfaces are still package-controlled rather than purely runtime-driven:

- Calamares installer branding
- SDDM theme text
- Plymouth splash assets
- static theme text baked into packaged visual assets

Those should stay generic where runtime branding is not practical. When they do show brand text, they update through their own package rebuilds.

## Refresh Flow

Installed systems refresh branding through:

```bash
kesk refresh-branding
```

That command is intended to be safe and idempotent. It validates current metadata, refreshes generated branding outputs, and updates `/etc/os-release`.

The normal automatic refresh path is:

- `/usr/share/libalpm/hooks/keskos-branding-refresh.hook`

That hook runs after upgrades to:

- `keskos-release`
- `keskos-branding`
- `keskos-browser-startpage`

## How Layer 4 Becomes Layer 5

1. Update `keskos-release` metadata defaults and package output.
2. Rebuild and publish the updated `keskos-release` package.
3. Rebuild any static branding packages that intentionally show the layer in visual assets.
4. Upgrade the system with pacman or `kesk upgrade`.
5. Let the branding refresh hook update runtime metadata.

The goal is that apps and tools pick up the new layer automatically without needing their own code changes.

## Testing

Check for hardcoded branding regressions:

```bash
./scripts/check-branding.sh
```

Run the repo cleanup + branding validation bundle:

```bash
./scripts/check-repo-cleanliness.sh
```

Run ISO build validation without starting `mkarchiso`:

```bash
KESKOS_BUILD_MODE=release ./build.sh --check
```

## What Not To Do

Do not:

- hardcode `Layer 4` into every app
- change `ID=keskos`
- use pretty branding in technical IDs
- reintroduce old `S.P.L.I.T.` edition labels as the main product name
- fork brand/version metadata separately across apps
