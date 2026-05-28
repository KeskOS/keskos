# KeskOS Packages

KeskOS treats its custom code, theming, installer integration, and curated app groups as packages published through the KeskOS pacman repo.

This ISO repo is no longer the normal source tree for those packages. Instead, it consumes published package names from `[keskos]` during ISO assembly.

- standalone package repos now own most `keskos-*` source trees
- desktop visual packages are maintained in `KeskOS/keskos-desktop`
- app packages such as `keskos-settings`, `keskos-welcome`, and `keskos-tools` live in their own repos
- meta packages stay lightweight because they mostly declare dependencies

The goal is simple:

- fresh installs still come from the ISO
- ongoing updates come from packages
- custom KeskOS code updates through the KeskOS pacman repo
- upstream apps keep updating through Arch repos, AUR, or Flatpak as appropriate

## Package Index

| Package name | Type | Purpose | Contains / Installs | Notes |
| --- | --- | --- | --- | --- |
| `keskos-release` | Core | Distro metadata | `/etc/keskos-release`, `/usr/lib/keskos/{version,channel,build-id}` | Base identity package for installed systems |
| `keskos-keyring` | Core | Future signing hook | Placeholder doc + keyring placeholder path | No private keys shipped |
| `keskos-mirrorlist` | Core | KeskOS repo endpoint | `/etc/pacman.d/keskos-mirrorlist` | Safe to edit locally; packaged with `backup=()` |
| `keskos-branding` | Real KeskOS package | Shared logos, icons, wallpapers, launcher assets | `/usr/share/keskos/assets`, `/usr/share/keskos/panel-icons`, `/usr/share/icons/hicolor`, `/usr/share/backgrounds/keskos` | Source of truth lives in `KeskOS/keskos-desktop` |
| `keskos-theme` | Real KeskOS package | KDE/Plasma/Kvantum/Konsole/Look-and-feel stack | KDE color schemes, Plasma desktop theme, look-and-feel package, Kvantum theme, Aurorae theme, Konsole profile, default Dunst/Fastfetch files | Source of truth lives in `KeskOS/keskos-desktop` |
| `keskos-tools` | Real KeskOS package | Main CLI and repair/update tooling | `kesk`, `kesk upgrade`, `kesk doctor`, `kesk repair`, `kesk settings`, `kesk welcome`, theme helpers, panel helpers, session helpers | Core runtime glue for repair/update flows |
| `keskos-settings` | Real KeskOS package | Branded System Settings integration | Custom KCM modules, `Kesk Settings` launcher, `About KeskOS`, polkit helper, settings helper | Replaces legacy `kesk-settings-kcms` |
| `keskos-welcome` | Real KeskOS package | First-boot flow and fallback setup console | `kesk-welcome`, welcome desktop/autostart entries, legacy `keskos-first-run` console | Replaces legacy `kesk-welcome` |
| `keskos-kickoff` | Real KeskOS package | Customized launcher widget | Patched `org.kde.plasma.simplekickoff` plasmoid | Source of truth lives in `KeskOS/keskos-desktop` |
| `keskos-workspace-switcher` | Real KeskOS package | Custom workspace switcher widget | `com.keskos.workspaceswitcher` plasmoid | Source of truth lives in `KeskOS/keskos-desktop` |
| `keskos-quickshell-hud` | Real KeskOS package | Top bar / HUD layer | Quickshell config and KDE autostart entry | Source of truth lives in `KeskOS/keskos-desktop` |
| `keskos-plasma-layout` | Real KeskOS package | Default bottom panel / layout templates | Default panel script, Plasma layout template, branded Files/Terminal launchers | Source of truth lives in `KeskOS/keskos-desktop` |
| `keskos-browser-startpage` | Real KeskOS package | Browser homepage and theme assets | `/usr/share/keskos/startpage`, `/usr/share/keskos/browser/startpage`, Firefox/Brave theme assets, branded browser launcher | Source of truth lives in `KeskOS/keskos-desktop` |
| `keskos-sddm-theme` | Real KeskOS package | Login screen theme | `/usr/share/sddm/themes/keskos` plus packaged default config snippets | Source of truth lives in `KeskOS/keskos-desktop` |
| `keskos-plymouth` | Real KeskOS package | Placeholder boot splash staging | `/usr/share/plymouth/themes/kesk-os/` asset staging + docs | Source of truth lives in `KeskOS/keskos-desktop` |
| `keskos-calamares-branding` | Real KeskOS package | Installer branding and install hooks | Calamares branding, `/etc/calamares` config, `keskoschoices` module, installer wrappers, package manifest | Keeps the black/orange KeskOS installer path package-managed |
| `keskos-installer-debug-log` | Real KeskOS package | Installer log viewer | `keskos-open-installer-log`, `KeskOS Installer Debug Log` desktop entry | Small helper split out for cleaner ownership |
| `keskos-core-meta` | Meta | Base KeskOS userspace | Depends on `networkmanager`, `fastfetch`, `btop`, `git`, `base-devel`, hardware/service basics, and core KeskOS packages | No files; dependency bundle only |
| `keskos-desktop-meta` | Meta | Default desktop shell/platform | Depends on KDE Plasma pieces and branded KeskOS desktop packages | Source of truth lives in `KeskOS/keskos-desktop-meta` |
| `keskos-browsers-meta` | Meta | Browser helper bundle for installed systems | The current standalone package still depends on `firefox` alongside `keskos-browser-startpage` | Kept out of the default ISO seed until the package is reduced to helpers-only |
| `keskos-gaming-meta` | Meta | Curated gaming apps | Steam, Lutris, MangoHud, GameMode, Vulkan tools; Heroic/GOverlay as `optdepends` | Keeps uncertain/AUR items optional |
| `keskos-social-meta` | Meta | Curated social/chat apps | Telegram and Signal plus Discord/Vesktop as `optdepends` | Flatpak remains a valid fallback path |
| `keskos-dev-meta` | Meta | Curated developer apps | Git, `base-devel`, Docker, GitHub CLI, Node.js, npm, Python; Code/VSCodium as `optdepends` | Docker is not auto-enabled |
| `keskos-creator-meta` | Meta | Curated creator/media apps | VLC, OBS Studio, GIMP, Krita, Audacity, Kdenlive | Clean bundle for content creation setups |
| `keskos-office-meta` | Meta | Curated office apps | LibreOffice Fresh, Okular, Thunderbird | Productivity bundle |
| `keskos-system-tools-meta` | Meta | Curated utilities/customization tools | htop, GParted, Timeshift, KDE Connect, Papirus, qt6ct, Fastfetch, Btop, Kate, Partition Manager | General system utility bundle |
| `keskos-hardware-meta` | Meta | Common hardware support bundle | Bluetooth, printing, Vulkan/Mesa support | Keeps NVIDIA optional |
| `keskos-nvidia-meta` | Meta | Optional NVIDIA bundle | `nvidia`, `nvidia-utils`, `nvidia-settings` | Separate on purpose so NVIDIA is never forced |
| `keskos-all-meta` | Meta | Recommended overall install | Depends on `keskos-core-meta`, `keskos-desktop-meta`, `keskos-browsers-meta`, `keskos-system-tools-meta` | Optional groups stay in `optdepends` |
| `kesk-settings-kcms` | Compatibility | Legacy package name bridge | Empty compatibility package that depends on `keskos-settings` | Keeps the old name installable during transition |
| `kesk-welcome` | Compatibility | Legacy package name bridge | Empty compatibility package that depends on `keskos-welcome` | Keeps the old name installable during transition |

## Package Types

### Real KeskOS packages

These packages install actual KeskOS-owned code, themes, scripts, desktop files, QML, icons, or installer assets.

Each of these packages is expected to build from its dedicated package repository and then publish to `[keskos]`.

Examples:

- `keskos-tools`
- `keskos-settings`
- `keskos-welcome`
- `keskos-quickshell-hud`
- `keskos-calamares-branding`

### Meta packages

These packages mostly install nothing themselves.

Instead, they depend on a curated package set so users can install a role-based bundle with one command.

Examples:

- `keskos-desktop-meta`
- `keskos-gaming-meta`
- `keskos-all-meta`

### Optional dependencies

`optdepends` are used when a package is useful but not guaranteed to be in official Arch repos, or when KeskOS should not force it onto every system.

Examples:

- LibreWolf / Zen / Brave as optional browser choices in the Welcome flow
- Heroic / GOverlay in `keskos-gaming-meta`
- VS Code / VSCodium in `keskos-dev-meta`
- NVIDIA drivers via `keskos-nvidia-meta`

### Upstream packages

KeskOS does not repackage every upstream application.

Instead, it relies on normal Arch packages where possible:

- KDE Plasma
- Dolphin
- Konsole
- Steam
- LibreOffice
- Docker
- NVIDIA packages

### AUR / Flatpak apps

Some curated app choices are best handled as AUR or Flatpak installs depending on the machine and repo configuration.

KeskOS models those as `optdepends` and Welcome flow choices instead of bundling proprietary binaries into the repo.

Browsers now follow that same rule for the ISO path: the browser helper assets are present, but the actual browser package is installed only after explicit user choice in `Kesk Welcome`.

## Update Model

KeskOS package updates are meant to work like this:

1. install the OS once from the ISO
2. install or keep the KeskOS pacman repo configured
3. update the system normally with:

```bash
sudo pacman -Syu
```

or with the KeskOS wrapper:

```bash
kesk upgrade
```

Custom KeskOS code should update through:

- `keskos-*` real packages

Upstream apps should update through:

- Arch repos
- enabled extra repos
- AUR helpers where appropriate
- Flatpak where appropriate

The ISO is therefore only the bootstrap and fresh-install medium.

Normal day-to-day updates should come from packages, not ISO reinstalls.
