# Kesk Doctor

This doctor tool currently ships as part of the `beta-development` branch.

`kesk doctor` is the read-only KeskOS system health checker.

It opens a terminal-based health scan with the same black/orange machine-console style as `kesk upgrade` and inspects the current system without changing it.

## Running It

From a terminal:

```bash
kesk doctor
```

Router commands that are also available:

```bash
kesk help
kesk --help
kesk version
```

## Start Menu Launcher

KeskOS ships a KDE launcher entry at:

- `/usr/share/applications/kesk-doctor.desktop`

It opens the doctor in Konsole with:

```bash
konsole --hold --workdir ~ -e /usr/bin/kesk doctor
```

That keeps the terminal visible after exit instead of closing immediately.

## What `kesk doctor` Does

When opened, the doctor:

1. Runs a read-only system scan.
2. Checks core package-manager and update-channel state.
3. Inspects desktop/theme assets used by KeskOS.
4. Counts failed services and checks disk usage.
5. Shows reboot guidance when it can detect it safely.
6. Can export a debug report for troubleshooting.

It does not repair anything yet. Repair actions will live in a future `kesk repair` tool.

## Implemented Checks

### System Integrity

- internet reachability
- `pacman` presence
- pacman database path presence
- pacman lock presence at `/var/lib/pacman/db.lck`
- pacman repository configuration
- reboot recommendation status

### Update Channels

- official repository update counts with `checkupdates`
- fallback to `pacman -Qu` when `checkupdates` is missing
- AUR update counts with `yay -Qua` when `yay` exists
- Flatpak update counts with `flatpak remote-ls --updates` when `flatpak` exists
- firmware update counts with `fwupdmgr get-updates` when `fwupdmgr` exists

These checks never perform upgrades.

### Desktop Stack

- SDDM theme presence and active theme detection
- Plymouth theme presence and active theme detection when available
- KDE/Plasma session detection
- Plasma user config file presence
- Kesk launcher/plasmoid file presence
- Quickshell command and Kesk HUD config presence
- browser detection and Kesk homepage/startpage asset presence

### Services And Storage

- failed `systemd` services
- `/`, `/home`, and `/boot` disk usage when available
- pacman cache size at `/var/cache/pacman/pkg`

### Build Info

- `/etc/os-release`
- `/etc/kesk-release` when present
- `/usr/share/kesk/version` when present
- running kernel
- Plasma version
- KDE Frameworks version
- Qt version when available

## Missing Optional Tools

Optional tools do not fail the doctor scan.

- No `yay`: AUR checks are skipped.
- No `flatpak`: Flatpak checks are skipped.
- No `fwupdmgr`: firmware checks are skipped.
- No `quickshell`: HUD checks are informational only.
- No `plymouth-set-default-theme`: Plymouth active-theme detection falls back to config inspection when possible.

## Logs

Every run writes a timestamped log to:

```text
~/.local/state/kesk/logs/
```

Log file format:

```text
doctor-YYYYMMDD-HHMMSS.log
```

Each log includes:

- scan start time
- checks performed
- status results
- warnings
- errors
- environment and command output needed for the health scan

Passwords and secrets are not logged.

## Debug Report Export

Menu option:

```text
[3] Export debug report
```

writes:

```text
~/kesk-debug-report.txt
```

The report includes:

- date and time
- KeskOS version and build info
- kernel and session information
- Plasma, Frameworks, and Qt version data when available
- package update counts
- failed services
- disk usage
- pacman lock state
- SDDM and Plymouth status
- Quickshell and launcher status
- browser/startpage asset status
- latest `kesk upgrade` and `kesk doctor` log paths

The report does not include:

- passwords
- SSH keys
- browser cookies
- tokens
- full home directory listings

## What The Status Markers Mean

- `[ OK ]` check passed
- `[ !! ]` warning or problem detected
- `[ .. ]` active work or refresh in progress
- `[ -- ]` skipped, unavailable, or not installed

## Relation To Future `kesk repair`

`kesk doctor` is only the inspection layer.

It tells you what looks wrong, missing, or unavailable. A later `kesk repair` tool can use that information to offer guided repair actions without mixing diagnostics and system changes into the same command.
