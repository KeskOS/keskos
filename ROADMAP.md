# KeskOS Roadmap

This document tracks what KeskOS already has, what is being actively polished, and what is planned next.

It is intentionally practical:

- what is already in the ISO project
- what is partially implemented and still needs cleanup
- what we want to add later

## Vision

KeskOS should feel like its own operating system, not just Arch Linux with a theme.

Core direction:

- Arch-based live ISO
- KDE Plasma base desktop
- Quickshell top HUD
- KDE native bottom taskbar
- black / orange industrial terminal look
- branded installer, login stack, terminal, browser, and desktop flow

## Current State

### Done

- Archiso-based build pipeline
- live ISO boot flow with KDE Plasma desktop
- Calamares installer integration
- custom Calamares branding and black/orange installer styling
- custom KWin / Aurorae style window decoration work
- custom wallpaper and system branding assets
- custom Konsole profile and color scheme
- custom browser start page under `browser-home/`
- `KESK` launcher integration
- Quickshell top bar
- KDE native bottom taskbar direction
- custom Plasma launcher button plasmoid
- custom workspace switcher plasmoid
- live/session helper scripts for setup and defaults
- SDDM / lock screen / splash branding pipeline
- local ISO package repo flow for AUR-built packages
- installer-time browser choice flow in Calamares
- installer-time package bundle / feature selection groundwork

### In Progress

- Welcome first-boot browser/install reliability
- installer layout polish and spacing cleanup
- Quickshell / Plasma integration stability
- installed-system defaults matching the live session exactly

### Recently Added

- browser selection moved out of Calamares and into Kesk Welcome
- Calamares deploy review page
- custom installer progress / slideshow styling
- first-boot browser theme / startpage logic in Welcome
- optional package bundle selection moved to first boot
- browser fallback away from Firefox

## Active Priorities

These are the main things KeskOS is focusing on right now.

### 1. Installer Stability

Make the custom Calamares flow feel production-ready:

- no blank pages
- no missing modules
- no broken multi-select pages
- clean package install behavior
- reliable browser selection
- clean summary and deploy review output

### 2. Installer Polish

Make Calamares feel like a real KeskOS deployment console:

- tighter spacing
- better typography
- smaller, cleaner branding
- less border clutter
- consistent sidebar steps
- no overlapping labels
- fully dark install/progress pages

### 3. Desktop Consistency

Make installed KeskOS match the intended screenshot direction:

- Quickshell top HUD
- KDE taskbar at the bottom
- consistent black/orange theme
- proper launcher behavior
- polished lock/login/terminal/browser visuals

### 4. Browser Experience

Make browser choice feel intentional:

- only install the selected browser
- set the selected browser as default
- apply the KeskOS start page automatically
- apply Firefox-family theme defaults where possible
- improve Chromium/Brave theming where possible

## Planned Next

### Installer

- searchable extra package selection in Calamares
- cleaner checkbox UI for bundles and add-ons
- package availability warnings before install
- better offline / online network handling in software pages
- richer deploy summary with selected packages and feature flags
- clearer install logging inside the live session and target system

### Desktop

- finish Quickshell popup interactions
- improve top bar dropdown polish
- tighter KDE panel theming
- stronger installed-user default layout
- better multi-monitor handling for HUD and wallpaper
- more consistent desktop icons and first-session layout

### Apps and Theming

- stronger browser theming for LibreWolf / Zen
- better Brave / Chromium policy defaults
- improved Dolphin visual theming
- improved About / system identity surfaces
- more monochrome/orange icon coverage

### Installer Options

- better feature-flag handling for:
  - HUD top bar
  - KDE taskbar
  - Plasma theme
  - SDDM
  - Plymouth
  - Docker
  - Bluetooth
  - Printing
  - NVIDIA
- optional gaming profile presets
- optional developer profile presets

### Release Engineering

- stronger automated validation before ISO release
- clearer failure messages in `build.sh`
- sanity checks for required Calamares modules after package build
- cleaner release checklist and VM test checklist

## Longer-Term Ideas

- fully unified software loadout page instead of several installer substeps
- richer package search UI in Calamares
- more custom KeskOS apps and utilities
- stronger post-install desktop provisioning
- optional demo layout script for screenshots and release media
- more custom artwork and installer media

## Known Rough Edges

These areas are not fully finished yet:

- Calamares custom software pages still need interaction polish
- packagechooser behavior depends on build-time Calamares patching
- browser package handling is still being hardened
- some browser theming is best-effort rather than perfect
- desktop shell behavior can still drift between live ISO and installed system

## Not Planned

These are intentionally out of scope right now:

- replacing KDE Plasma with Hyprland
- replacing Calamares with a custom installer from scratch
- bringing back Eww as the main shell layer
- turning KeskOS into a generic theme pack
- shipping all browsers by default just to avoid selection issues

## Milestone Direction

### Milestone A: Stable Installer

Goal:

- install succeeds cleanly
- browser choice works
- package bundles work
- no broken software pages

### Milestone B: Pixel-Correct Desktop

Goal:

- top bar, taskbar, launcher, and windows match the target visual style more closely
- installed session looks like the live session

### Milestone C: Release-Ready KeskOS

Goal:

- stable ISO build
- reliable installer flow
- consistent desktop identity
- clean release notes and screenshots

## Notes

- KeskOS is now centered around the ISO + Calamares workflow.
- The old script-installer era is preserved separately and is not the main path anymore.
- Post-install personalization should happen during install when possible, not through a forced first-run blocker app.
