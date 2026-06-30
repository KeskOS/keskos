#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[check-keskos-repo-packages] %s\n' "$1"
}

fail() {
  printf '[check-keskos-repo-packages] error: %s\n' "$1" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: ./scripts/check-keskos-repo-packages.sh [--ignore-package <pkgname> ...]

Checks that the required KeskOS ISO packages are available from the public
KeskOS pacman repository without installing anything on the host system.

Options:
  --ignore-package <pkgname>
      Skip a required package during the public repo preflight. This is useful
      when the ISO build will satisfy that package from [keskos-local] instead
      of downloads.keskos.org.
EOF
}

build_sudo_env() {
  local -n env_ref="$1"
  local variable_name=""
  local value=""

  for variable_name in \
    TMPDIR TMP TEMP \
    http_proxy https_proxy ftp_proxy rsync_proxy no_proxy all_proxy \
    HTTP_PROXY HTTPS_PROXY FTP_PROXY RSYNC_PROXY NO_PROXY ALL_PROXY \
    RES_OPTIONS LOCALDOMAIN \
    SSL_CERT_FILE SSL_CERT_DIR CURL_CA_BUNDLE
  do
    value="${!variable_name-}"
    if [[ -n "$value" ]]; then
      env_ref+=("${variable_name}=${value}")
    fi
  done
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

array_contains() {
  local needle="$1"
  shift || true
  local item=""

  for item in "$@"; do
    if [[ "$item" == "$needle" ]]; then
      return 0
    fi
  done

  return 1
}

main() {
  local repo_root required_list repo_url
  local temp_root temp_conf db_path cache_dir
  local -a packages=()
  local -a ignored_packages=()
  local -a missing=()
  local -a sudo_env=()
  local package_name=""

  while (($#)); do
    case "$1" in
      -h|--help)
        usage
        exit 0
        ;;
      --ignore-package)
        shift
        [[ -n "${1-}" ]] || fail "Missing value for --ignore-package"
        ignored_packages+=("$1")
        ;;
      *)
        usage
        exit 1
        ;;
    esac
    shift
  done

  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  required_list="${repo_root}/config/keskos-required-packages.txt"
  repo_url="${KESKOS_REPO_URL:-https://downloads.keskos.org/repo/\$repo/os/\$arch}"

  [[ -f "${required_list}" ]] || fail "Required package list not found: ${required_list}"

  require_command pacman
  require_command sudo
  require_command mktemp

  mapfile -t packages < <(awk '
    /^[[:space:]]*#/ { next }
    /^[[:space:]]*$/ { next }
    { print $1 }
  ' "${required_list}")

  (( ${#packages[@]} > 0 )) || fail "No required packages were found in ${required_list}"

  temp_root="$(mktemp -d "${TMPDIR:-/tmp}/keskos-repo-check.XXXXXX")"
  temp_conf="${temp_root}/pacman.conf"
  db_path="${temp_root}/db"
  cache_dir="${temp_root}/cache"
  trap 'sudo rm -rf "'"${temp_root}"'" >/dev/null 2>&1 || rm -rf "'"${temp_root}"'"' EXIT

  cat >"${temp_conf}" <<EOF
[options]
Architecture = auto
SigLevel = Required DatabaseOptional
LocalFileSigLevel = Optional

[keskos]
SigLevel = Optional TrustAll
Server = ${repo_url}
EOF

  mkdir -p "${db_path}" "${cache_dir}"
  build_sudo_env sudo_env

  log "Refreshing the temporary pacman sync database for the KeskOS repo..."
  sudo env "${sudo_env[@]}" pacman \
    --config "${temp_conf}" \
    --dbpath "${db_path}" \
    --cachedir "${cache_dir}" \
    -Sy --noconfirm >/dev/null

  for package_name in "${packages[@]}"; do
    if array_contains "${package_name}" "${ignored_packages[@]}"; then
      log "skipping ${package_name} because it will be provided by a local override"
      continue
    fi

    if sudo env "${sudo_env[@]}" pacman \
      --config "${temp_conf}" \
      --dbpath "${db_path}" \
      -Si "${package_name}" >/dev/null 2>&1; then
      log "found ${package_name}"
    else
      missing+=("${package_name}")
    fi
  done

  if (( ${#missing[@]} > 0 )); then
    printf '[check-keskos-repo-packages] missing package: %s\n' "${missing[@]}" >&2
    fail "Required KeskOS packages are missing from ${repo_url}"
  fi

  log "All required KeskOS packages are available from ${repo_url}"
}

main "$@"
