#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/keskos-wsl-build"
WORK_REPO="${CACHE_ROOT}/repo"
ORIGINAL_OUT_DIR="${REPO_ROOT}/out"
WORKSPACE_BUILD_ROOT="${CACHE_ROOT}/safe-build-${UID}"
WORKSPACE_TMPDIR="${CACHE_ROOT}/tmp-${UID}"
WORKSPACE_RESOLV_CONF="${CACHE_ROOT}/resolv.conf-${UID}"
WORKSPACE_MIRRORLIST="${CACHE_ROOT}/mirrorlist-${UID}"
PREPARE_ONLY=0
BUILD_ARGS=()
TMP_BIND_ACTIVE=0
RESOLV_BIND_ACTIVE=0
RESOLV_BIND_TARGET=""

log() {
  printf '[keskos-buildwsl] %s\n' "$1"
}

warn() {
  printf '[keskos-buildwsl] warning: %s\n' "$1" >&2
}

fail() {
  printf '[keskos-buildwsl] error: %s\n' "$1" >&2
  exit 1
}

require_command() {
  local command_name="$1"
  command -v "$command_name" >/dev/null 2>&1 || fail "Missing required command: ${command_name}"
}

show_help() {
  cat <<'EOF'
Usage: bash buildwsl.sh [--prepare-only] [build.sh args...]

WSL helper for KeskOS ISO builds.

What it does:
  - copies the repo into a Linux-local workspace
  - converts CRLF files to LF
  - recreates placeholder symlinks under airootfs/etc
  - restores execute bits on shebang scripts
  - moves the heavy mkarchiso work tree out of /tmp
  - forces compiler and linker temp files into a Linux-local TMPDIR
  - temporarily bind-mounts that temp directory over /tmp for pacstrap/mkarchiso
  - snapshots a stable resolver config for the root-run build
  - uses a WSL-friendly pacman mirrorlist with extra fallback servers
  - runs the normal build.sh from that sanitized copy
  - syncs finished artifacts back to ./out

Options:
  --prepare-only   stage and sanitize the workspace, but do not start build.sh
  --help           show this help
EOF
}

is_wsl() {
  [[ -n "${WSL_INTEROP:-}" ]] && return 0
  [[ -r /proc/sys/kernel/osrelease ]] && grep -qi 'microsoft' /proc/sys/kernel/osrelease && return 0
  [[ -r /proc/version ]] && grep -qi 'microsoft' /proc/version && return 0
  return 1
}

cleanup_workspace() {
  if [[ -e "$WORK_REPO" ]]; then
    log "Removing previous WSL workspace copy..."
    rm -rf -- "$WORK_REPO"
  fi

  if [[ -e "$WORKSPACE_BUILD_ROOT" ]]; then
    log "Removing previous WSL build root..."
    sudo rm -rf -- "$WORKSPACE_BUILD_ROOT"
  fi

  if [[ -e "$WORKSPACE_TMPDIR" ]]; then
    log "Removing previous WSL temp directory..."
    sudo rm -rf -- "$WORKSPACE_TMPDIR"
  fi

  rm -f -- "$WORKSPACE_RESOLV_CONF" "$WORKSPACE_MIRRORLIST"
}

cleanup_tmp_bind() {
  if (( TMP_BIND_ACTIVE == 1 )); then
    log "Unmounting temporary /tmp bind mount..."
    if ! sudo umount /tmp; then
      warn "Could not unmount /tmp automatically. You may need to run: sudo umount /tmp"
    fi
    TMP_BIND_ACTIVE=0
  fi
}

cleanup_resolv_bind() {
  if (( RESOLV_BIND_ACTIVE == 1 )); then
    log "Unmounting temporary resolver bind mount..."
    if ! sudo umount "$RESOLV_BIND_TARGET"; then
      warn "Could not unmount ${RESOLV_BIND_TARGET} automatically. You may need to run: sudo umount ${RESOLV_BIND_TARGET}"
    fi
    RESOLV_BIND_ACTIVE=0
  fi
}

bind_workspace_tmp() {
  log "Bind-mounting ${WORKSPACE_TMPDIR} over /tmp for the build..."
  sudo mount --bind "$WORKSPACE_TMPDIR" /tmp
  TMP_BIND_ACTIVE=1
}

bind_workspace_resolver() {
  RESOLV_BIND_TARGET="$(readlink -f /etc/resolv.conf 2>/dev/null || printf '/etc/resolv.conf')"
  log "Bind-mounting ${WORKSPACE_RESOLV_CONF} over ${RESOLV_BIND_TARGET} for the build..."
  sudo mount --bind "$WORKSPACE_RESOLV_CONF" "$RESOLV_BIND_TARGET"
  RESOLV_BIND_ACTIVE=1
}

prepare_network_files() {
  local resolv_source=""
  local mirror_source=""

  resolv_source="$(readlink -f /etc/resolv.conf 2>/dev/null || printf '/etc/resolv.conf')"
  mirror_source="/etc/pacman.d/mirrorlist"

  log "Creating stable WSL resolver snapshot at ${WORKSPACE_RESOLV_CONF}"
  python3 - "$resolv_source" "$WORKSPACE_RESOLV_CONF" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])

fallback_nameservers = ["1.1.1.1", "8.8.8.8"]
lines: list[str] = []
nameservers: list[str] = []

if source.exists():
    for raw_line in source.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("search ", "domain ", "options ")):
            lines.append(line)
            continue
        if line.startswith("nameserver "):
            value = line.split(None, 1)[1].strip()
            if value and value not in nameservers:
                nameservers.append(value)

for fallback in fallback_nameservers:
    if fallback not in nameservers:
        nameservers.append(fallback)

target.parent.mkdir(parents=True, exist_ok=True)
with target.open("w", encoding="utf-8") as handle:
    handle.write("# KeskOS WSL build resolver snapshot\n")
    saw_options = any(line.startswith("options ") for line in lines)
    for line in lines:
        handle.write(line + "\n")
    if not saw_options:
        handle.write("options timeout:2 attempts:2 rotate\n")
    for nameserver in nameservers:
        handle.write(f"nameserver {nameserver}\n")
PY

  log "Creating WSL-friendly pacman mirrorlist at ${WORKSPACE_MIRRORLIST}"
  python3 - "$mirror_source" "$WORKSPACE_MIRRORLIST" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])

fallback_servers = [
    "Server = https://mirror.rackspace.com/archlinux/$repo/os/$arch",
    "Server = https://mirrors.kernel.org/archlinux/$repo/os/$arch",
    "Server = https://arch.mirror.constant.com/$repo/os/$arch",
    "Server = https://mirror.math.princeton.edu/pub/archlinux/$repo/os/$arch",
]

servers: list[str] = []
pattern = re.compile(r"^\s*Server\s*=")

if source.exists():
    for raw_line in source.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if line and pattern.match(line) and line not in servers:
            servers.append(line)

for fallback in fallback_servers:
    if fallback not in servers:
        servers.append(fallback)

target.parent.mkdir(parents=True, exist_ok=True)
with target.open("w", encoding="utf-8") as handle:
    handle.write("## KeskOS WSL build mirrorlist\n")
    handle.write("## Existing host entries are kept first, then stable fallbacks are appended.\n")
    for line in servers:
        handle.write(line + "\n")
PY
}

prepare_workspace() {
  require_command python3
  require_command bash

  mkdir -p "$CACHE_ROOT"
  cleanup_workspace
  mkdir -p "$WORKSPACE_TMPDIR"
  chmod 1777 "$WORKSPACE_TMPDIR"

  log "Creating Linux-local workspace at ${WORK_REPO}"
  python3 - "$REPO_ROOT" "$WORK_REPO" <<'PY'
from __future__ import annotations

import os
import shutil
import stat
import sys
from pathlib import Path

repo_root = Path(sys.argv[1]).resolve()
work_repo = Path(sys.argv[2]).resolve()

ignore_names = {
    ".git",
    "out",
    "__pycache__",
    ".pytest_cache",
}

def ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in ignore_names}

shutil.copytree(repo_root, work_repo, ignore=ignore)

converted = 0
symlinks = 0
executables = 0

def should_treat_as_text(data: bytes) -> bool:
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True

def is_symlink_placeholder(path: Path, text: str) -> bool:
    if not text.startswith("/"):
        return False
    if "\n" in text:
        return False
    if len(text) > 300:
        return False
    relative = path.relative_to(work_repo).as_posix()
    parts = relative.split("/")
    if relative == "airootfs/etc/localtime":
        return True
    if relative == "airootfs/etc/systemd/system-generators/systemd-gpt-auto-generator":
        return True
    if any(part.endswith(".wants") or part.endswith(".requires") for part in parts):
        return True
    return False

for path in sorted(work_repo.rglob("*")):
    if not path.is_file():
        continue

    data = path.read_bytes()
    if should_treat_as_text(data):
        normalized = data.replace(b"\r\n", b"\n")
        if normalized != data:
            path.write_bytes(normalized)
            data = normalized
            converted += 1

        text = data.decode("utf-8").strip()
        if is_symlink_placeholder(path, text):
            path.unlink()
            path.symlink_to(text)
            symlinks += 1
            continue

    if data.startswith(b"#!"):
        current_mode = path.stat().st_mode
        new_mode = current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        if new_mode != current_mode:
            os.chmod(path, new_mode)
            executables += 1

print(f"converted={converted}")
print(f"symlinks={symlinks}")
print(f"executables={executables}")
PY

  prepare_network_files
}

run_build() {
  log "Running build.sh from the sanitized WSL workspace..."
  (
    cd "$WORK_REPO"
    export KESKOS_SAFE_BUILD_ROOT="$WORKSPACE_BUILD_ROOT"
    export TMPDIR="$WORKSPACE_TMPDIR"
    export TMP="$WORKSPACE_TMPDIR"
    export TEMP="$WORKSPACE_TMPDIR"
    export KESKOS_OVERRIDE_MIRRORLIST="$WORKSPACE_MIRRORLIST"
    export KESKOS_PACMAN_SYNC_ATTEMPTS="${KESKOS_PACMAN_SYNC_ATTEMPTS:-3}"
    bash ./build.sh "$@"
  )
}

sync_output_back() {
  local workspace_out="${WORK_REPO}/out"
  if [[ ! -d "$workspace_out" ]]; then
    warn "Workspace build completed without an out/ directory to sync back."
    return 0
  fi

  log "Syncing build artifacts back to ${ORIGINAL_OUT_DIR}"
  mkdir -p "$ORIGINAL_OUT_DIR"

  python3 - "$workspace_out" "$ORIGINAL_OUT_DIR" <<'PY'
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

source = Path(sys.argv[1]).resolve()
target = Path(sys.argv[2]).resolve()

def copy_file_contents(src: str | Path, dst: str | Path) -> None:
    src_path = Path(src)
    dst_path = Path(dst)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src_path, dst_path)
    try:
        shutil.copymode(src_path, dst_path)
    except OSError:
        pass

for item in source.iterdir():
    destination = target / item.name
    if item.is_dir():
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        elif destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(item, destination, symlinks=False, copy_function=copy_file_contents)
        continue
    if destination.is_dir():
        shutil.rmtree(destination)
    elif destination.is_symlink():
        destination.unlink()
    copy_file_contents(item, destination)
PY
}

main() {
  while (( $# > 0 )); do
    case "$1" in
      --prepare-only)
        PREPARE_ONLY=1
        shift
        ;;
      --help|-h)
        show_help
        exit 0
        ;;
      *)
        BUILD_ARGS+=("$1")
        shift
        ;;
    esac
  done

  if (( EUID == 0 && PREPARE_ONLY == 0 )); then
    fail "Run buildwsl.sh as a regular user. It will call sudo through build.sh when needed."
  fi

  if ! is_wsl; then
    warn "WSL was not detected. buildwsl.sh still works, but it is primarily meant for WSL checkouts."
  fi

  if [[ "$REPO_ROOT" == /mnt/* ]]; then
    log "Repo is on a Windows-mounted filesystem. A sanitized Linux-local copy will be used for the build."
  fi

  prepare_workspace

  if (( PREPARE_ONLY == 1 )); then
    log "Workspace prepared only. build.sh was not started."
    log "Prepared workspace: ${WORK_REPO}"
    log "Planned build root: ${WORKSPACE_BUILD_ROOT}"
    log "Planned TMPDIR: ${WORKSPACE_TMPDIR}"
    log "Prepared resolver: ${WORKSPACE_RESOLV_CONF}"
    log "Prepared mirrorlist: ${WORKSPACE_MIRRORLIST}"
    return 0
  fi

  trap 'cleanup_resolv_bind; cleanup_tmp_bind' EXIT
  bind_workspace_resolver
  bind_workspace_tmp
  run_build "${BUILD_ARGS[@]}"
  sync_output_back
  cleanup_resolv_bind
  cleanup_tmp_bind
  trap - EXIT

  log "WSL build complete."
  log "Workspace copy: ${WORK_REPO}"
  log "Build root: ${WORKSPACE_BUILD_ROOT}"
  log "TMPDIR: ${WORKSPACE_TMPDIR}"
  log "Resolver snapshot: ${WORKSPACE_RESOLV_CONF}"
  log "Mirrorlist: ${WORKSPACE_MIRRORLIST}"
  log "Mirrored output: ${ORIGINAL_OUT_DIR}"
}

main "$@"
