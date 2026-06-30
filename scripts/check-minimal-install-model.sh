#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failures=0

fail() {
  printf '[check-minimal-install-model] FAIL: %s\n' "$1" >&2
  failures=$((failures + 1))
}

pass() {
  printf '[check-minimal-install-model] PASS: %s\n' "$1"
}

assert_seed_absent() {
  local package="$1"
  if grep -qxF "$package" "${repo_root}/packages.x86_64"; then
    fail "packages.x86_64 still includes optional package ${package}"
  else
    pass "${package} is not in packages.x86_64"
  fi
}

assert_seed_present() {
  local package="$1"
  if grep -qxF "$package" "${repo_root}/packages.x86_64"; then
    pass "${package} remains in packages.x86_64"
  else
    fail "packages.x86_64 is missing required package ${package}"
  fi
}

assert_pkgbuild_dep_absent() {
  local pkgbuild="$1"
  local package="$2"
  if awk '
    /^depends=\(/ { in_deps=1; next }
    in_deps && /^\)/ { in_deps=0 }
    in_deps { print }
  ' "$pkgbuild" | tr -d "[:space:]'\"" | grep -qxF "$package"; then
    fail "$(basename "$(dirname "$pkgbuild")") hard-depends on optional package ${package}"
  else
    pass "$(basename "$(dirname "$pkgbuild")") does not hard-depend on ${package}"
  fi
}

for package in discover kate packagekit-qt6 partitionmanager brave-bin librewolf-bin zen-browser-bin; do
  assert_seed_absent "$package"
done

for package in fastfetch btop networkmanager plasma-desktop keskos-welcome keskos-settings keskos-tools; do
  assert_seed_present "$package"
done

for package in base-devel git htop gparted partitionmanager timeshift cups print-manager kdeconnect; do
  assert_pkgbuild_dep_absent "${repo_root}/../keskos-core-meta/PKGBUILD" "$package"
done

for package in bluedevil kdeconnect discover; do
  assert_pkgbuild_dep_absent "${repo_root}/../keskos-desktop-meta/PKGBUILD" "$package"
done

if (( failures > 0 )); then
  printf '[check-minimal-install-model] %d check(s) failed.\n' "$failures" >&2
  exit 1
fi

printf '[check-minimal-install-model] minimal install model checks passed.\n'
