from __future__ import annotations

PRESET_CATEGORIES: dict[str, list[str]] = {
    "Gaming": [
        "steam",
        "lutris",
        "heroic-games-launcher",
        "mangohud",
        "gamemode",
        "goverlay",
    ],
    "Chat": [
        "discord",
        "vesktop",
        "telegram-desktop",
        "signal-desktop",
    ],
    "Development": [
        "git",
        "base-devel",
        "code",
        "vscodium",
        "kate",
        "docker",
        "docker-compose",
        "github-cli",
        "nodejs",
        "npm",
        "python",
        "python-pip",
    ],
    "Media": [
        "vlc",
        "obs-studio",
        "gimp",
        "krita",
        "audacity",
        "kdenlive",
    ],
    "Office": [
        "libreoffice-fresh",
        "okular",
        "thunderbird",
    ],
    "System Tools": [
        "fastfetch",
        "btop",
        "htop",
        "gparted",
        "partitionmanager",
        "ark",
        "spectacle",
        "timeshift",
        "kdeconnect",
    ],
    "Customization": [
        "kvantum",
        "papirus-icon-theme",
        "qt6ct",
        "nwg-look",
    ],
    "Drivers / Gaming Support": [
        "vulkan-tools",
        "vulkan-icd-loader",
        "lib32-vulkan-icd-loader",
        "mesa-utils",
    ],
}

CATEGORY_ORDER = list(PRESET_CATEGORIES.keys())
