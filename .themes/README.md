# KeskOS Themes

These themes are based on the palette currently shipped with the latest local ISO build:

- `out/keskos-2026.05.07-x86_64.iso`
- `configs/kde/keskos.colors`
- `browser-home/style.css`
- `assets/wallpaper.svg`

Core palette:

- `#050505` main background
- `#080706` elevated background
- `#11100e` panel edge
- `#ce6a35` accent
- `#df9a69` accent glow
- `#e7c9b3` primary text
- `#8b7363` muted text

Included files:

- `keskos-vscode-theme/` local VS Code theme extension
- `install-vscode-theme.sh` helper installer for the local VS Code theme
- `keskos-vencord.theme.css` Vencord CSS theme

Usage:

- VS Code:
  Select the extension root folder:
  `.themes/keskos-vscode-theme`
  Do not select:
  `.themes/keskos-vscode-theme/themes`
- VS Code:
  Or run `./.themes/install-vscode-theme.sh`, reload VS Code, then select `KeskOS CRT`.
- Vencord: import `keskos-vencord.theme.css` as a local theme, or place it in `~/.config/Vencord/themes/`.
