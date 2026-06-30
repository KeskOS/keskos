#!/usr/bin/env bash
set -euo pipefail

CHOICES_FILE="${1:-/var/lib/keskos/install-choices.json}"
TARGET_USER="${TARGET_USER:-}"
LOG_FILE="/var/log/keskos-install.log"
STARTPAGE_URL="file:///usr/share/keskos/startpage/index.html"

log() {
  mkdir -p "$(dirname "$LOG_FILE")"
  printf '[keskos-install] %s\n' "$1" | tee -a "$LOG_FILE" >/dev/null
}

require_jq() {
  if ! command -v jq >/dev/null 2>&1; then
    log "jq is unavailable in target system; skipping install choice application."
    exit 0
  fi
}

read_json() {
  local query="$1"
  jq -r "$query // empty" "$CHOICES_FILE"
}

feature_enabled() {
  local feature="$1"
  local value
  value="$(jq -r --arg key "$feature" '.features[$key] // false' "$CHOICES_FILE")"
  [[ "$value" == "true" ]]
}

desktop_entry_exists() {
  local desktop_id="$1"
  local desktop_root=""

  [[ -n "$desktop_id" ]] || return 1

  for desktop_root in \
    /usr/local/share/applications \
    /usr/share/applications
  do
    [[ -f "${desktop_root}/${desktop_id}" ]] && return 0
  done

  return 1
}

set_browser_mime_default_if_available() {
  local desktop_id="$1"

  if desktop_entry_exists "$desktop_id"; then
    write_mimeapps /etc/xdg/mimeapps.list "$desktop_id"
    log "Set system mime defaults to ${desktop_id}."
  else
    log "Selected browser desktop entry ${desktop_id} is not installed; leaving browser MIME defaults for Kesk Welcome."
  fi
}

write_mimeapps() {
  local target_path="$1"
  local desktop_id="$2"
  mkdir -p "$(dirname "$target_path")"
  cat >"$target_path" <<EOF
[Default Applications]
x-scheme-handler/http=${desktop_id}
x-scheme-handler/https=${desktop_id}
text/html=${desktop_id}
application/xhtml+xml=${desktop_id}
inode/directory=dolphin.desktop
EOF
}

write_firefox_policies() {
  local dir="$1"
  mkdir -p "$dir"
  cat >"$dir/policies.json" <<EOF
{
  "policies": {
    "Homepage": {
      "URL": "${STARTPAGE_URL}",
      "StartPage": "homepage"
    },
    "OverrideFirstRunPage": "",
    "OverridePostUpdatePage": "",
    "DisableDefaultBrowserAgent": true
  }
}
EOF
}

write_brave_policies() {
  local dir="$1"
  mkdir -p "$dir"
  cp -f /usr/share/keskos/browser-themes/brave/policies.json "$dir/keskos-startpage.json"
}

seed_firefox_profile() {
  local config_root="$1"
  local profile_dir="${config_root}/keskos.default-release"

  mkdir -p "${config_root}"
  mkdir -p "${profile_dir}/chrome"

  cat >"${config_root}/profiles.ini" <<EOF
[General]
StartWithLastProfile=1
Version=2

[Profile0]
Name=default-release
IsRelative=1
Path=keskos.default-release
Default=1
EOF

  cat >"${profile_dir}/user.js" <<EOF
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);
user_pref("browser.startup.homepage", "${STARTPAGE_URL}");
user_pref("browser.startup.page", 1);
user_pref("browser.newtabpage.enabled", false);
user_pref("browser.aboutConfig.showWarning", false);
user_pref("browser.shell.checkDefaultBrowser", false);
EOF

  cp -f /usr/share/keskos/browser-themes/firefox/userChrome.css "${profile_dir}/chrome/userChrome.css"
  cp -f /usr/share/keskos/browser-themes/firefox/userContent.css "${profile_dir}/chrome/userContent.css"
}

apply_browser_theme() {
  local resolved_key="$1"
  local target_home="$2"

  if ! feature_enabled "browser_startpage"; then
    log "Browser startpage flag disabled; skipping browser theming."
    return 0
  fi

  if [[ "$resolved_key" == "librewolf" || "$resolved_key" == "firefox" || "$resolved_key" == "zen" ]]; then
    local dir=""
    for dir in \
      /usr/lib/librewolf/distribution \
      /usr/lib/firefox/distribution \
      /usr/lib/zen-browser/distribution \
      /opt/zen-browser/distribution
    do
      [[ -d "$(dirname "$dir")" || -d "$dir" ]] || continue
      write_firefox_policies "$dir"
    done
    if [[ -n "$target_home" ]]; then
      if [[ "$resolved_key" == "librewolf" ]]; then
        seed_firefox_profile "${target_home}/.librewolf"
      elif [[ "$resolved_key" == "zen" ]]; then
        seed_firefox_profile "${target_home}/.zen"
      else
        seed_firefox_profile "${target_home}/.mozilla/firefox"
      fi
    fi
    log "Applied Firefox-family homepage policies."
    return 0
  fi

  if [[ "$resolved_key" == "brave" ]]; then
    local dir=""
    for dir in \
      /etc/brave/policies/managed \
      /etc/brave-browser/policies/managed
    do
      write_brave_policies "$dir"
    done
    log "Applied Brave managed homepage policies."
    return 0
  fi
}

enable_optional_services() {
  feature_enabled "bluetooth" && systemctl enable bluetooth.service >/dev/null 2>&1 && log "Enabled bluetooth.service"
  feature_enabled "printing" && systemctl enable cups.service >/dev/null 2>&1 && log "Enabled cups.service"

  if feature_enabled "docker"; then
    systemctl enable docker.service >/dev/null 2>&1 && log "Enabled docker.service"
    if [[ -n "$TARGET_USER" ]] && id -u "$TARGET_USER" >/dev/null 2>&1; then
      usermod -aG docker "$TARGET_USER" >/dev/null 2>&1 || true
      log "Added ${TARGET_USER} to docker group."
    fi
  fi
}

configure_plymouth_theme() {
  local theme_name="keskos"

  if [[ ! -d "/usr/share/plymouth/themes/${theme_name}" ]]; then
    log "Plymouth theme ${theme_name} is not installed; leaving boot splash unchanged."
    return 0
  fi

  if ! command -v plymouth-set-default-theme >/dev/null 2>&1; then
    log "plymouth-set-default-theme is unavailable; leaving boot splash unchanged."
    return 0
  fi

  if plymouth-set-default-theme "${theme_name}" >/dev/null 2>&1; then
    log "Selected KeskOS Plymouth theme."
  else
    log "Could not select KeskOS Plymouth theme; continuing installation."
    return 0
  fi

  if plymouth-set-default-theme -R "${theme_name}" >/dev/null 2>&1; then
    log "Refreshed initramfs with the KeskOS Plymouth theme."
  else
    log "Initramfs refresh for Plymouth did not complete; mkinitcpio may refresh later."
  fi
}

apply_login_and_boot_themes() {
  if feature_enabled "sddm_theme"; then
    mkdir -p /etc/sddm.conf.d
    cat >/etc/sddm.conf.d/keskos-theme.conf <<'EOF'
[Theme]
Current=keskos
EOF
    log "Applied KeskOS SDDM theme selection."
  else
    rm -f /etc/sddm.conf.d/keskos-theme.conf
    log "Skipped KeskOS SDDM theme selection."
  fi

  if feature_enabled "plymouth"; then
    configure_plymouth_theme
  else
    log "Plymouth feature disabled."
  fi
}

remove_unselected_browsers() {
  local resolved_key="$1"
  local resolved_package="$2"
  local remove_other_browsers="$3"
  local installed_package=""
  local candidates=(
    firefox
    librewolf
    librewolf-bin
    zen-browser
    zen-browser-bin
    brave-browser
    brave-browser-bin
    brave-bin
  )

  [[ "$remove_other_browsers" == "true" ]] || return 0
  [[ -n "$resolved_key" ]] || return 0

  for installed_package in "${candidates[@]}"; do
    [[ "$installed_package" == "$resolved_package" ]] && continue
    if pacman -Q "$installed_package" >/dev/null 2>&1; then
      pacman -Rns --noconfirm "$installed_package" >/dev/null 2>&1 || true
      log "Removed non-selected browser package ${installed_package}."
    fi
  done
}

main() {
  require_jq

  if [[ ! -f "$CHOICES_FILE" ]]; then
    log "No install choices file found at ${CHOICES_FILE}; skipping optional customization."
    exit 0
  fi

  local browser_desktop=""
  local browser_key=""
  local browser_package=""
  local remove_other_browsers=""
  local target_home=""

  browser_desktop="$(read_json '.browser.desktop')"
  browser_key="$(read_json '.browser.resolved_key')"
  browser_package="$(read_json '.browser.package')"
  remove_other_browsers="$(read_json '.browser.remove_other_browsers_after_install')"

  [[ -n "$browser_desktop" ]] || browser_desktop="librewolf.desktop"
  [[ -n "$browser_key" ]] || browser_key="librewolf"
  [[ -n "$browser_package" ]] || browser_package="librewolf-bin"
  [[ -n "$remove_other_browsers" ]] || remove_other_browsers="false"

  if [[ -n "$TARGET_USER" ]] && id -u "$TARGET_USER" >/dev/null 2>&1; then
    target_home="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
  fi

  mkdir -p /etc/xdg /etc/keskos
  cp -f "$CHOICES_FILE" /etc/keskos/install-choices.json
  log "Browser setup is deferred to Kesk Welcome; Calamares will not set browser defaults or theme profiles."

  enable_optional_services
  apply_login_and_boot_themes
}

main "$@"
