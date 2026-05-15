Kesk Kickoff

This folder contains the KeskOS-restyled overlay for `org.kde.plasma.simplekickoff`.

Files changed
- `metadata.json`
- `metadata.desktop`
- `contents/config/main.xml`
- `contents/ui/main.qml`
- `contents/ui/FullRepresentation.qml`
- `contents/ui/Header.qml`
- `contents/ui/BasePage.qml`
- `contents/ui/ApplicationsPage.qml`
- `contents/ui/AbstractKickoffItemDelegate.qml`
- `contents/ui/KickoffListDelegate.qml`
- `contents/ui/KickoffGridDelegate.qml`
- `contents/ui/KickoffListView.qml`
- `contents/ui/KickoffGridView.qml`
- `contents/ui/LeaveButtons.qml`
- `contents/ui/KeskStyle.qml`
- `contents/images/keskos-mark.png`
- `assets/icons/hicolor/48x48/apps/keskos-launcher.png`
- `assets/icons/hicolor/64x64/apps/keskos-launcher.png`
- `assets/icons/hicolor/128x128/apps/keskos-launcher.png`

How to restart Plasma
```bash
gtk-update-icon-cache ~/.local/share/icons/hicolor || true
kbuildsycoca6 --noincremental || true
kquitapp6 plasmashell || killall plasmashell
rm -rf ~/.cache/plasmashell/qmlcache ~/.cache/plasma*
kstart6 plasmashell
```

How to revert to the original local copy
```bash
cp -r ~/.local/share/plasma/plasmoids/org.kde.plasma.simplekickoff \
      ~/.local/share/plasma/plasmoids/org.kde.plasma.simplekickoff.backup.$(date +%Y%m%d-%H%M%S)

rm -rf ~/.local/share/plasma/plasmoids/org.kde.plasma.simplekickoff
cp -r ~/.local/share/plasma/plasmoids/org.kde.plasma.simplekickoff.backup.TIMESTAMP \
      ~/.local/share/plasma/plasmoids/org.kde.plasma.simplekickoff
```

How to tweak the accent color
- Edit `contents/ui/KeskStyle.qml`
- Change `accentColor`
- Optionally adjust `accentBrightColor`, `accentSoftColor`, `accentDimColor`, `hoverFillColor`, `selectedFillColor`, and `borderColor`

Logo notes
- The compact launcher button and footer branding now use `contents/images/keskos-mark.png`, copied directly from the real repo branding asset `assets/kesk_os_logo-removebg.png`.
- The icon theme entry `keskos-launcher` now resolves to fixed-size PNGs generated from that same real logo:
  - `assets/icons/hicolor/48x48/apps/keskos-launcher.png`
  - `assets/icons/hicolor/64x64/apps/keskos-launcher.png`
  - `assets/icons/hicolor/128x128/apps/keskos-launcher.png`
- The old simplified SVG placeholder was retired to `.old_experiments/launcher-icons/` and is no longer part of the active launcher path.

Known limitations
- The launcher still uses KDE's native Kicker/KRunner models, so some subcomponents keep KDE behavior even though the visuals are restyled.
- Symbolic system-action icons depend on the active icon theme.
- Font fallback is handled by Qt/fontconfig; if `VT323` is unavailable, headers fall back automatically.
