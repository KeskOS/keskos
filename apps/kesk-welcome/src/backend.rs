use serde::{Deserialize, Serialize};
use serde_json::Value;

use std::collections::HashMap;
use std::env;
use std::fs::{self, File};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Clone, Debug)]
pub struct ActionResponse {
    pub ok: bool,
    pub message: String,
}

#[derive(Clone, Debug, Serialize)]
pub struct InstallReportRuntime {
    pub install_result: String,
    pub browser_selected: String,
    pub top_bar_widgets_selected: Vec<String>,
    pub optional_apps_selected: Vec<String>,
    pub browser_install_result: String,
    pub browser_default_result: String,
    pub browser_theme_result: String,
    pub topbar_result: String,
    pub optional_apps_result: String,
    pub theme_result: String,
    pub welcome_mode: String,
    pub network_connection_type: String,
    pub network_uplink_checked: bool,
    pub network_uplink_online: bool,
    pub nmcli_available: bool,
    pub ping_available: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum InstallSource {
    Installed,
    Pacman,
    Aur,
    AurNeedsYay,
    Unavailable,
}

#[derive(Clone, Debug)]
pub struct InstallTarget {
    pub package_name: String,
    pub source: InstallSource,
    pub source_label: String,
}

#[derive(Clone, Copy, Debug)]
pub struct BrowserOption {
    pub key: &'static str,
    pub label: &'static str,
    pub pacman_candidates: &'static [&'static str],
    pub aur_candidates: &'static [&'static str],
}

#[derive(Clone, Debug)]
pub struct BrowserSnapshot {
    pub key: String,
    pub label: String,
    pub installed: bool,
    pub current_default: bool,
    pub homepage_assets_available: bool,
    pub source_label: String,
    pub package_name: String,
}

#[derive(Clone, Copy, Debug)]
pub struct CatalogItem {
    pub id: &'static str,
    pub label: &'static str,
    pub group: &'static str,
    pub pacman_candidates: &'static [&'static str],
    pub aur_candidates: &'static [&'static str],
}

#[derive(Clone, Debug)]
pub struct CatalogStatus {
    pub id: String,
    pub label: String,
    pub target: InstallTarget,
}

#[derive(Clone, Debug)]
pub struct WiFiNetwork {
    pub ssid: String,
    pub signal: String,
    pub security: String,
}

#[derive(Clone, Debug)]
pub struct NetworkSnapshot {
    pub nmcli_available: bool,
    pub ping_available: bool,
    pub support_badge: String,
    pub uplink_online: bool,
    pub uplink_checked: bool,
    pub status_label: String,
    pub status_message: String,
    pub backend_status: String,
    pub active_connection: String,
    pub connection_type: String,
    pub wired_active: bool,
    pub wired_status: String,
    pub wifi_device_detected: bool,
    pub wifi_status: String,
    pub wifi_networks: Vec<WiFiNetwork>,
    pub last_checked_timestamp: Option<u64>,
}

#[derive(Clone, Debug)]
pub struct TopBarSnapshot {
    pub backend_connected: bool,
    pub can_reset: bool,
    pub can_restart: bool,
}

#[derive(Clone, Debug)]
pub struct ThemeSnapshot {
    pub kesk_theme_active: String,
    pub kde_defaults_active: String,
    pub launcher_layout: String,
    pub panel_layout: String,
    pub konsole_profile: String,
    pub dunst_theme: String,
    pub plymouth_installed: bool,
    pub plymouth_theme_installed: bool,
    pub can_reapply_kesk: bool,
    pub can_reset_kde: bool,
    pub can_reapply_launcher: bool,
    pub can_reapply_panels: bool,
    pub can_reapply_konsole: bool,
}

#[derive(Clone, Debug)]
pub struct CommandSpec {
    pub label: String,
    pub preview: String,
    pub argv: Vec<String>,
}

#[derive(Deserialize)]
struct BrowserHelperPayload {
    browsers: Vec<BrowserHelperBrowser>,
}

#[derive(Clone, Deserialize)]
struct BrowserHelperBrowser {
    key: String,
    label: String,
    package_name: String,
    installed: bool,
    current_default: bool,
    homepage_assets_available: bool,
}

const BROWSER_OPTIONS: &[BrowserOption] = &[
    BrowserOption {
        key: "librewolf",
        label: "LibreWolf",
        pacman_candidates: &["librewolf", "librewolf-bin"],
        aur_candidates: &["librewolf-bin", "librewolf"],
    },
    BrowserOption {
        key: "brave",
        label: "Brave",
        pacman_candidates: &["brave-browser", "brave"],
        aur_candidates: &["brave-bin", "brave-browser-bin"],
    },
    BrowserOption {
        key: "zen",
        label: "Zen Browser",
        pacman_candidates: &["zen-browser", "zen"],
        aur_candidates: &["zen-browser-bin", "zen-browser"],
    },
    BrowserOption {
        key: "firefox",
        label: "Firefox",
        pacman_candidates: &["firefox"],
        aur_candidates: &[],
    },
];

const OPTIONAL_APPS: &[CatalogItem] = &[
    CatalogItem {
        id: "steam",
        label: "Steam",
        group: "Gaming",
        pacman_candidates: &["steam"],
        aur_candidates: &[],
    },
    CatalogItem {
        id: "heroic",
        label: "Heroic Games Launcher",
        group: "Gaming",
        pacman_candidates: &["heroic-games-launcher"],
        aur_candidates: &["heroic-games-launcher-bin"],
    },
    CatalogItem {
        id: "lutris",
        label: "Lutris",
        group: "Gaming",
        pacman_candidates: &["lutris"],
        aur_candidates: &[],
    },
    CatalogItem {
        id: "protonupqt",
        label: "ProtonUp-Qt",
        group: "Gaming",
        pacman_candidates: &["protonup-qt"],
        aur_candidates: &[],
    },
    CatalogItem {
        id: "discord",
        label: "Discord",
        group: "Gaming",
        pacman_candidates: &["discord"],
        aur_candidates: &[],
    },
    CatalogItem {
        id: "obs",
        label: "OBS Studio",
        group: "Creator",
        pacman_candidates: &["obs-studio"],
        aur_candidates: &[],
    },
    CatalogItem {
        id: "gimp",
        label: "GIMP",
        group: "Creator",
        pacman_candidates: &["gimp"],
        aur_candidates: &[],
    },
    CatalogItem {
        id: "kdenlive",
        label: "Kdenlive",
        group: "Creator",
        pacman_candidates: &["kdenlive"],
        aur_candidates: &[],
    },
    CatalogItem {
        id: "blender",
        label: "Blender",
        group: "Creator",
        pacman_candidates: &["blender"],
        aur_candidates: &[],
    },
    CatalogItem {
        id: "code",
        label: "Visual Studio Code / VSCodium",
        group: "Dev",
        pacman_candidates: &["code"],
        aur_candidates: &["vscodium", "vscodium-bin"],
    },
    CatalogItem {
        id: "github-cli",
        label: "GitHub CLI",
        group: "Dev",
        pacman_candidates: &["github-cli"],
        aur_candidates: &[],
    },
    CatalogItem {
        id: "nodejs",
        label: "Node.js",
        group: "Dev",
        pacman_candidates: &["nodejs"],
        aur_candidates: &[],
    },
    CatalogItem {
        id: "python-pip",
        label: "Python Tools (pip)",
        group: "Dev",
        pacman_candidates: &["python-pip"],
        aur_candidates: &[],
    },
    CatalogItem {
        id: "vlc",
        label: "VLC",
        group: "Utilities",
        pacman_candidates: &["vlc"],
        aur_candidates: &[],
    },
    CatalogItem {
        id: "7zip",
        label: "7zip / p7zip",
        group: "Utilities",
        pacman_candidates: &["7zip", "p7zip"],
        aur_candidates: &[],
    },
    CatalogItem {
        id: "flatpak",
        label: "Flatpak",
        group: "Utilities",
        pacman_candidates: &["flatpak"],
        aur_candidates: &[],
    },
    CatalogItem {
        id: "mission-center",
        label: "Mission Center",
        group: "Utilities",
        pacman_candidates: &["mission-center"],
        aur_candidates: &["mission-center"],
    },
];

pub fn repo_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn source_root_candidates() -> Vec<PathBuf> {
    vec![
        PathBuf::from("/usr/local/share/keskos/source"),
        PathBuf::from("/usr/share/keskos/source"),
        repo_root(),
    ]
}

fn first_existing_path(candidates: &[PathBuf]) -> Option<String> {
    candidates
        .iter()
        .find(|candidate| candidate.exists())
        .map(|candidate| candidate.to_string_lossy().into_owned())
}

fn source_path(relative: &str) -> Option<String> {
    let candidates: Vec<PathBuf> = source_root_candidates()
        .into_iter()
        .map(|root| root.join(relative))
        .collect();
    first_existing_path(&candidates)
}

fn resolve_binary(command_name: &str, source_relative: Option<&str>) -> Option<String> {
    if command_exists(command_name) {
        return Some(command_name.to_string());
    }

    let runtime_candidates = [
        PathBuf::from("/usr/bin").join(command_name),
        PathBuf::from("/usr/local/bin").join(command_name),
    ];

    if let Some(path) = first_existing_path(&runtime_candidates) {
        return Some(path);
    }

    source_relative.and_then(source_path)
}

pub fn config_root() -> PathBuf {
    env::var_os("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| home_dir().join(".config"))
}

pub fn state_root() -> PathBuf {
    env::var_os("XDG_STATE_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| home_dir().join(".local").join("state"))
}

pub fn marker_path() -> PathBuf {
    config_root().join("kesk").join("welcome-complete")
}

pub fn legacy_marker_path() -> PathBuf {
    home_dir().join(".config").join("keskos").join("first-run-complete")
}

pub fn log_path() -> PathBuf {
    state_root().join("kesk").join("logs").join("welcome.log")
}

pub fn write_marker(mode: &str) -> Result<(), String> {
    let path = marker_path();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }

    let mut file = File::create(&path).map_err(|error| error.to_string())?;
    file.write_all(format!("mode={mode}\n").as_bytes()).map_err(|error| error.to_string())
}

pub fn home_dir() -> PathBuf {
    env::var_os("HOME").map(PathBuf::from).unwrap_or_else(|| PathBuf::from("/"))
}

pub fn command_exists(name: &str) -> bool {
    if name.contains('/') {
        return Path::new(name).is_file();
    }

    env::var_os("PATH")
        .map(|paths| env::split_paths(&paths).any(|dir| dir.join(name).is_file()))
        .unwrap_or(false)
}

pub fn is_live_environment() -> bool {
    Path::new("/run/archiso").exists() || Path::new("/run/calamares").exists()
}

fn unix_timestamp() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or(0)
}

fn state_is_connected(state: &str) -> bool {
    let normalized = state.trim().to_ascii_lowercase();
    normalized == "connected" || normalized.starts_with("connected ")
}

fn connection_type_from_nmcli(value: &str) -> &'static str {
    let normalized = value.trim().to_ascii_lowercase();
    if normalized.contains("wifi") || normalized.contains("wireless") {
        "wifi"
    } else if normalized.contains("ethernet") || normalized.contains("wired") {
        "wired"
    } else {
        "unknown"
    }
}

fn ping_uplink_available() -> bool {
    command_exists("ping")
        && run_capture("ping", &["-c", "1", "-W", "2", "8.8.8.8"])
            .map(|output| output.status.success())
            .unwrap_or(false)
}

pub fn network_snapshot() -> NetworkSnapshot {
    let nmcli_available = command_exists("nmcli");
    let ping_available = command_exists("ping");
    let support_badge = if nmcli_available && ping_available {
        String::from("Native")
    } else if nmcli_available || ping_available {
        String::from("Limited")
    } else {
        String::from("Unsupported")
    };

    let mut wired_device_detected = false;
    let mut wired_active = false;
    let mut wifi_device_detected = false;
    let mut wifi_active = false;
    let mut active_connection = String::from("unknown");
    let mut connection_type = String::from("unknown");
    let mut wifi_networks = Vec::new();

    if nmcli_available {
        if let Ok(output) = run_capture("nmcli", &["-t", "--escape", "no", "-f", "DEVICE,TYPE,STATE", "device"]) {
            let text = String::from_utf8_lossy(&output.stdout);
            for line in text.lines() {
                let mut parts = line.splitn(3, ':');
                let _device = parts.next().unwrap_or_default().trim();
                let device_type = parts.next().unwrap_or_default().trim();
                let state = parts.next().unwrap_or_default().trim();
                match connection_type_from_nmcli(device_type) {
                    "wired" => {
                        wired_device_detected = true;
                        if state_is_connected(state) {
                            wired_active = true;
                        }
                    },
                    "wifi" => {
                        wifi_device_detected = true;
                        if state_is_connected(state) {
                            wifi_active = true;
                        }
                    },
                    _ => {},
                }
            }
        }

        if let Ok(output) = run_capture(
            "nmcli",
            &["-t", "--escape", "no", "-f", "NAME,TYPE", "connection", "show", "--active"],
        ) {
            let text = String::from_utf8_lossy(&output.stdout);
            for line in text.lines() {
                let mut parts = line.splitn(2, ':');
                let name = parts.next().unwrap_or_default().trim();
                let active_type = parts.next().unwrap_or_default().trim();
                if name.is_empty() {
                    continue;
                }
                let normalized_type = connection_type_from_nmcli(active_type);
                if normalized_type != "unknown" {
                    active_connection = format!("{name} ({active_type})");
                    connection_type = normalized_type.to_string();
                    break;
                }
                if active_connection == "unknown" {
                    active_connection = format!("{name} ({active_type})");
                }
            }
        }

        if wifi_device_detected {
            if let Ok(output) = run_capture(
                "nmcli",
                &[
                    "-t",
                    "--escape",
                    "no",
                    "-f",
                    "SSID,SIGNAL,SECURITY",
                    "device",
                    "wifi",
                    "list",
                ],
            ) {
                let mut deduped: HashMap<String, WiFiNetwork> = HashMap::new();
                let text = String::from_utf8_lossy(&output.stdout);
                for line in text.lines() {
                    let mut parts = line.splitn(3, ':');
                    let ssid = parts.next().unwrap_or_default().trim();
                    let signal = parts.next().unwrap_or_default().trim();
                    let security = parts.next().unwrap_or_default().trim();
                    if ssid.is_empty() {
                        continue;
                    }

                    let entry = WiFiNetwork {
                        ssid: ssid.to_string(),
                        signal: if signal.is_empty() { String::from("?") } else { signal.to_string() },
                        security: if security.is_empty() || security == "--" {
                            String::from("Open")
                        } else {
                            security.to_string()
                        },
                    };

                    match deduped.get(ssid) {
                        Some(existing)
                            if existing.signal.parse::<i32>().unwrap_or(0)
                                >= entry.signal.parse::<i32>().unwrap_or(0) => {},
                        _ => {
                            deduped.insert(ssid.to_string(), entry);
                        },
                    }
                }

                wifi_networks = deduped.into_values().collect();
                wifi_networks.sort_by(|left, right| {
                    right
                        .signal
                        .parse::<i32>()
                        .unwrap_or(0)
                        .cmp(&left.signal.parse::<i32>().unwrap_or(0))
                        .then_with(|| left.ssid.cmp(&right.ssid))
                });
            }
        }
    }

    if connection_type == "unknown" {
        if wired_active {
            connection_type = String::from("wired");
            active_connection = String::from("Wired connection detected");
        } else if wifi_active {
            connection_type = String::from("wifi");
            active_connection = String::from("Wi-Fi connection detected");
        }
    }

    let uplink_online = ping_uplink_available();
    let uplink_checked = ping_available;
    let status_label;
    let status_message;
    if uplink_online {
        status_label = String::from("Uplink online");
        status_message = if connection_type == "wired" {
            String::from("Wired uplink online.")
        } else if connection_type == "wifi" {
            String::from("Wi-Fi connected and internet is reachable.")
        } else {
            String::from("Internet connection detected.")
        };
    } else if ping_available {
        status_label = String::from("No uplink");
        status_message = if connection_type == "wired" {
            String::from("Wired connection detected, but internet is unreachable.")
        } else if connection_type == "wifi" {
            String::from("Connected, but internet is not reachable.")
        } else {
            String::from("No uplink to the internet. Package installation is unavailable.")
        };
    } else {
        status_label = String::from("No uplink");
        status_message = String::from("ping is unavailable. Internet reachability cannot be verified.");
    }

    let backend_status = if nmcli_available && ping_available {
        String::from("NetworkManager backend detected. Uplink test backend detected.")
    } else if nmcli_available {
        String::from(
            "NetworkManager backend detected. ping is unavailable, so internet reachability cannot be verified.",
        )
    } else if ping_available {
        String::from("NetworkManager is unavailable. Network setup cannot be managed from Kesk Welcome.")
    } else {
        String::from(
            "NetworkManager is unavailable. Network setup cannot be managed from Kesk Welcome. ping is also unavailable.",
        )
    };

    let wired_status = if !nmcli_available {
        String::from("unknown")
    } else if wired_active {
        String::from("active")
    } else if wired_device_detected {
        String::from("detected, not connected")
    } else {
        String::from("not detected")
    };

    let wifi_status = if !nmcli_available {
        String::from("unavailable")
    } else if wifi_active {
        String::from("detected, connected")
    } else if wifi_device_detected {
        String::from("detected, not connected")
    } else {
        String::from("not detected")
    };

    NetworkSnapshot {
        nmcli_available,
        ping_available,
        support_badge,
        uplink_online,
        uplink_checked,
        status_label,
        status_message,
        backend_status,
        active_connection,
        connection_type,
        wired_active,
        wired_status,
        wifi_device_detected,
        wifi_status,
        wifi_networks,
        last_checked_timestamp: Some(unix_timestamp()),
    }
}

pub fn connect_wifi(ssid: &str, password: Option<&str>) -> ActionResponse {
    if !command_exists("nmcli") {
        return ActionResponse {
            ok: false,
            message: String::from(
                "NetworkManager is unavailable. Network setup cannot be managed from Kesk Welcome.",
            ),
        };
    }

    if ssid.trim().is_empty() {
        return ActionResponse { ok: false, message: String::from("Select a Wi-Fi network first.") };
    }

    let mut args = vec![
        String::from("device"),
        String::from("wifi"),
        String::from("connect"),
        ssid.to_string(),
    ];
    if let Some(value) = password.filter(|value| !value.trim().is_empty()) {
        args.push(String::from("password"));
        args.push(value.to_string());
    }

    match run_capture_owned("nmcli", &args) {
        Ok(output) if output.status.success() => {
            let snapshot = network_snapshot();
            ActionResponse {
                ok: true,
                message: if snapshot.uplink_online {
                    String::from("Wi-Fi connected and internet is reachable.")
                } else if snapshot.connection_type == "wifi" {
                    String::from("Connected, but internet is not reachable.")
                } else {
                    String::from("Connection completed, but uplink status is unknown.")
                },
            }
        },
        Ok(output) => {
            let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
            let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
            let message = if !stderr.is_empty() {
                stderr
            } else if !stdout.is_empty() {
                stdout
            } else {
                String::from("Connection failed.")
            };
            ActionResponse { ok: false, message }
        },
        Err(error) => ActionResponse { ok: false, message: error },
    }
}

fn run_capture(program: &str, args: &[&str]) -> Result<Output, String> {
    Command::new(program).args(args).output().map_err(|error| error.to_string())
}

fn run_capture_owned(program: &str, args: &[String]) -> Result<Output, String> {
    Command::new(program).args(args).output().map_err(|error| error.to_string())
}

fn browser_helper_path() -> String {
    resolve_binary(
        "kesk-browser-settings",
        Some("packages/kesk-settings-kcms/scripts/kesk-browser-settings"),
    )
    .unwrap_or_else(|| String::from("kesk-browser-settings"))
}

pub fn doctor_command_path() -> String {
    resolve_binary("kesk", Some("airootfs/usr/bin/kesk")).unwrap_or_else(|| String::from("kesk"))
}

pub fn repair_command_path() -> String {
    resolve_binary("kesk", Some("airootfs/usr/bin/kesk")).unwrap_or_else(|| String::from("kesk"))
}

pub fn configure_user_command_path() -> Option<String> {
    resolve_helper("keskos-configure-user", "airootfs/usr/local/bin/keskos-configure-user")
}

pub fn quickshell_wrapper_command_path() -> Option<String> {
    resolve_helper("keskos-shell", "airootfs/usr/local/bin/keskos-shell")
}

pub fn reset_panel_command_path() -> Option<String> {
    resolve_helper("keskos-reset-panel", "airootfs/usr/bin/keskos-reset-panel")
}

pub fn fix_launcher_command_path() -> Option<String> {
    resolve_helper("keskos-fix-launcher", "airootfs/usr/bin/keskos-fix-launcher")
        .or_else(|| resolve_helper("keskos-launcher-switch", "airootfs/usr/bin/keskos-launcher-switch"))
}

pub fn theme_apply_command_path() -> String {
    resolve_binary("kesk-apply-theme", Some("airootfs/usr/bin/kesk-apply-theme"))
        .unwrap_or_else(|| String::from("kesk-apply-theme"))
}

pub fn kde_defaults_command_path() -> String {
    resolve_binary(
        "kesk-apply-kde-defaults",
        Some("packages/kesk-settings-kcms/scripts/kesk-apply-kde-defaults"),
    )
    .unwrap_or_else(|| String::from("kesk-apply-kde-defaults"))
}

fn browser_helper_status() -> Option<BrowserHelperPayload> {
    let helper = browser_helper_path();
    let output = run_capture(&helper, &["status"]).ok()?;
    if !output.status.success() {
        return None;
    }
    serde_json::from_slice(&output.stdout).ok()
}

fn browser_option(key: &str) -> Option<&'static BrowserOption> {
    BROWSER_OPTIONS.iter().find(|option| option.key == key)
}

pub fn browser_snapshots() -> Vec<BrowserSnapshot> {
    let mut helper_map: HashMap<String, BrowserHelperBrowser> = HashMap::new();
    if let Some(payload) = browser_helper_status() {
        for entry in payload.browsers {
            helper_map.insert(entry.key.clone(), entry);
        }
    }

    BROWSER_OPTIONS
        .iter()
        .map(|option| {
            let install_target = resolve_install_target(option.pacman_candidates, option.aur_candidates);
            let helper_entry = helper_map.get(option.key).cloned();

            let label = helper_entry
                .as_ref()
                .map(|entry| entry.label.clone())
                .unwrap_or_else(|| option.label.to_string());
            let installed = helper_entry
                .as_ref()
                .map(|entry| entry.installed)
                .unwrap_or_else(|| install_target.source == InstallSource::Installed);
            let current_default = helper_entry.as_ref().map(|entry| entry.current_default).unwrap_or(false);
            let homepage_assets_available =
                helper_entry.as_ref().map(|entry| entry.homepage_assets_available).unwrap_or(false);
            let package_name = if !install_target.package_name.is_empty() {
                install_target.package_name.clone()
            } else {
                helper_entry.as_ref().map(|entry| entry.package_name.clone()).unwrap_or_default()
            };

            BrowserSnapshot {
                key: option.key.to_string(),
                label,
                installed,
                current_default,
                homepage_assets_available,
                source_label: install_target.source_label.clone(),
                package_name,
            }
        })
        .collect()
}

fn run_browser_helper(action: &[&str]) -> ActionResponse {
    let helper = browser_helper_path();
    match run_capture(&helper, action) {
        Ok(output) => {
            if let Ok(json) = serde_json::from_slice::<Value>(&output.stdout) {
                let ok = json.get("ok").and_then(Value::as_bool).unwrap_or(output.status.success());
                let message = json
                    .get("message")
                    .and_then(Value::as_str)
                    .unwrap_or("Browser helper finished.")
                    .to_string();
                return ActionResponse { ok, message };
            }

            ActionResponse {
                ok: output.status.success(),
                message: String::from_utf8_lossy(&output.stderr).trim().to_string(),
            }
        },
        Err(error) => ActionResponse { ok: false, message: error },
    }
}

pub fn set_default_browser(key: &str) -> ActionResponse {
    run_browser_helper(&["set-default", key])
}

pub fn apply_browser_theme(key: &str, include_homepage: bool) -> ActionResponse {
    let homepage = if include_homepage { "yes" } else { "no" };
    run_browser_helper(&["apply-theme", key, "--homepage", homepage])
}

pub fn browser_install_target(key: &str) -> InstallTarget {
    browser_option(key)
        .map(|option| resolve_install_target(option.pacman_candidates, option.aur_candidates))
        .unwrap_or_else(|| InstallTarget {
            package_name: String::new(),
            source: InstallSource::Unavailable,
            source_label: String::from("unavailable"),
        })
}

fn resolve_install_target(pacman_candidates: &[&str], aur_candidates: &[&str]) -> InstallTarget {
    for candidate in pacman_candidates.iter().chain(aur_candidates.iter()) {
        if is_installed(candidate) {
            return InstallTarget {
                package_name: (*candidate).to_string(),
                source: InstallSource::Installed,
                source_label: String::from("installed"),
            };
        }
    }

    for candidate in pacman_candidates.iter().chain(aur_candidates.iter()) {
        if pacman_available(candidate) {
            return InstallTarget {
                package_name: (*candidate).to_string(),
                source: InstallSource::Pacman,
                source_label: String::from("pacman"),
            };
        }
    }

    let mut aur_pool: Vec<&str> = aur_candidates.to_vec();
    for candidate in pacman_candidates {
        if !aur_pool.contains(candidate) {
            aur_pool.push(candidate);
        }
    }

    if command_exists("yay") {
        for candidate in aur_pool {
            if aur_available(candidate) {
                return InstallTarget {
                    package_name: candidate.to_string(),
                    source: InstallSource::Aur,
                    source_label: String::from("AUR"),
                };
            }
        }
    } else if !aur_pool.is_empty() {
        return InstallTarget {
            package_name: aur_pool[0].to_string(),
            source: InstallSource::AurNeedsYay,
            source_label: String::from("yay required"),
        };
    }

    InstallTarget {
        package_name: String::new(),
        source: InstallSource::Unavailable,
        source_label: String::from("unavailable"),
    }
}

fn is_installed(package_name: &str) -> bool {
    run_capture("pacman", &["-Q", package_name]).map(|output| output.status.success()).unwrap_or(false)
}

fn pacman_available(package_name: &str) -> bool {
    run_capture("pacman", &["-Si", package_name]).map(|output| output.status.success()).unwrap_or(false)
}

fn aur_available(package_name: &str) -> bool {
    run_capture("yay", &["-Si", package_name]).map(|output| output.status.success()).unwrap_or(false)
}

pub fn optional_app_catalog() -> &'static [CatalogItem] {
    OPTIONAL_APPS
}

pub fn optional_app_statuses() -> Vec<CatalogStatus> {
    OPTIONAL_APPS
        .iter()
        .map(|item| CatalogStatus {
            id: item.id.to_string(),
            label: item.label.to_string(),
            target: resolve_install_target(item.pacman_candidates, item.aur_candidates),
        })
        .collect()
}

pub fn topbar_snapshot() -> TopBarSnapshot {
    let backend_connected = command_exists("quickshell") && quickshell_config_exists();
    let can_restart = backend_connected && resolve_helper("keskos-shell", "airootfs/usr/local/bin/keskos-shell").is_some();
    let can_reset = resolve_helper("keskos-configure-user", "airootfs/usr/local/bin/keskos-configure-user").is_some();

    TopBarSnapshot { backend_connected, can_reset, can_restart }
}

fn quickshell_config_exists() -> bool {
    let mut candidates = vec![home_dir().join(".config/quickshell/keskos/shell.qml")];
    candidates.extend(
        source_root_candidates()
            .into_iter()
            .map(|root| root.join("configs/quickshell/keskos/shell.qml")),
    );
    candidates.iter().any(|candidate| candidate.exists())
}

pub fn theme_snapshot() -> ThemeSnapshot {
    let repair_json = run_json_command(&repair_command_path(), &[String::from("repair"), String::from("--status"), String::from("--json")]);
    let doctor_json = run_json_command(&doctor_command_path(), &[String::from("doctor"), String::from("--json")]);

    let color_scheme = json_string_at(&repair_json, &["theme_status", "active", "color_scheme"]).unwrap_or_else(|| String::from("unknown"));
    let look_and_feel =
        json_string_at(&repair_json, &["theme_status", "active", "look_and_feel"]).unwrap_or_else(|| String::from("unknown"));
    let konsole_profile =
        json_string_at(&repair_json, &["theme_status", "active", "konsole_profile"]).unwrap_or_else(|| String::from("unknown"));
    let plymouth_theme =
        json_string_at(&repair_json, &["theme_status", "active", "plymouth_theme"]).unwrap_or_else(|| String::from("unavailable"));
    let launcher_matches = json_array_len(&doctor_json, &["launcher_matches"]) > 0;
    let quickshell_matches = json_array_len(&doctor_json, &["quickshell_matches"]) > 0;

    let kesk_theme_active = if color_scheme == "KeskOSDark" || look_and_feel == "com.keskos.desktop" {
        String::from("yes")
    } else if color_scheme == "unknown" {
        String::from("unknown")
    } else {
        String::from("no")
    };
    let kde_defaults_active = if kesk_theme_active == "no" { String::from("yes") } else { String::from("no") };
    let launcher_layout = if launcher_matches { String::from("detected") } else { String::from("missing") };
    let panel_layout = if home_dir().join(".config/plasma-org.kde.plasma.desktop-appletsrc").exists() {
        String::from("detected")
    } else {
        String::from("unknown")
    };
    let konsole_status = if konsole_profile.contains("KeskOS") { String::from("detected") } else { String::from("missing") };
    let dunst_status = if dunst_config_detected() { String::from("detected") } else { String::from("unknown") };
    let plymouth_installed = command_exists("plymouth-set-default-theme") || command_exists("plymouthd");
    let plymouth_theme_installed = plymouth_theme != "unavailable";

    ThemeSnapshot {
        kesk_theme_active,
        kde_defaults_active,
        launcher_layout,
        panel_layout: if quickshell_matches { String::from("detected") } else { panel_layout },
        konsole_profile: konsole_status,
        dunst_theme: dunst_status,
        plymouth_installed,
        plymouth_theme_installed,
        can_reapply_kesk: resolve_helper("kesk-apply-theme", "airootfs/usr/bin/kesk-apply-theme").is_some(),
        can_reset_kde: resolve_helper("kesk-apply-kde-defaults", "packages/kesk-settings-kcms/scripts/kesk-apply-kde-defaults").is_some(),
        can_reapply_launcher: resolve_helper("keskos-fix-launcher", "airootfs/usr/bin/keskos-fix-launcher").is_some()
            || resolve_helper("keskos-launcher-switch", "airootfs/usr/bin/keskos-launcher-switch").is_some(),
        can_reapply_panels: resolve_helper("keskos-reset-panel", "airootfs/usr/bin/keskos-reset-panel").is_some(),
        can_reapply_konsole: resolve_helper("kesk", "airootfs/usr/bin/kesk").is_some(),
    }
}

fn dunst_config_detected() -> bool {
    let candidates = [
        home_dir().join(".config/dunst/dunstrc"),
        PathBuf::from("/etc/xdg/dunst/dunstrc"),
        PathBuf::from("/etc/dunst/dunstrc"),
    ];
    candidates.iter().any(|candidate| candidate.exists())
}

fn resolve_helper(command_name: &str, repo_relative: &str) -> Option<String> {
    resolve_binary(command_name, Some(repo_relative))
}

fn run_json_command(program: &str, args: &[String]) -> Value {
    run_capture_owned(program, args)
        .ok()
        .and_then(|output| serde_json::from_slice::<Value>(&output.stdout).ok())
        .unwrap_or(Value::Null)
}

fn json_string_at(value: &Value, path: &[&str]) -> Option<String> {
    let mut current = value;
    for key in path {
        current = current.get(*key)?;
    }
    current.as_str().map(ToString::to_string)
}

fn json_array_len(value: &Value, path: &[&str]) -> usize {
    let mut current = value;
    for key in path {
        let Some(next) = current.get(*key) else {
            return 0;
        };
        current = next;
    }
    current.as_array().map(Vec::len).unwrap_or(0)
}

pub fn open_url(url: &str) -> ActionResponse {
    if !command_exists("xdg-open") {
        return ActionResponse {
            ok: false,
            message: format!("Could not open browser. Visit {url} manually."),
        };
    }

    match run_capture("xdg-open", &[url]) {
        Ok(output) if output.status.success() => ActionResponse {
            ok: true,
            message: format!("Opened {url}"),
        },
        _ => ActionResponse {
            ok: false,
            message: format!("Could not open browser. Visit {url} manually."),
        },
    }
}

fn install_report_script_path() -> Option<String> {
    first_existing_path(&[
        PathBuf::from("/usr/lib/kesk/install_report.py"),
        PathBuf::from("/usr/local/lib/kesk/install_report.py"),
        repo_root().join("airootfs/usr/lib/kesk/install_report.py"),
    ])
}

fn python_command_path() -> Option<String> {
    resolve_binary("python3", None).or_else(|| resolve_binary("python", None))
}

pub fn send_install_report(include_extra: bool, runtime: &InstallReportRuntime) -> ActionResponse {
    let Some(script) = install_report_script_path() else {
        return ActionResponse {
            ok: false,
            message: String::from("Install report helper is unavailable on this system."),
        };
    };

    let Some(python) = python_command_path() else {
        return ActionResponse {
            ok: false,
            message: String::from("Python runtime is unavailable. Install report could not be sent."),
        };
    };

    let runtime_json = match serde_json::to_string(runtime) {
        Ok(value) => value,
        Err(error) => {
            return ActionResponse {
                ok: false,
                message: format!("Could not serialize the install report payload: {error}"),
            };
        },
    };

    let mut command = Command::new(python);
    command.arg(script).arg("send");
    if include_extra {
        command.arg("--include-extra");
    }
    command.env("KESK_INSTALL_REPORT_RUNTIME_JSON", runtime_json);

    match command.output() {
        Ok(output) => {
            if let Ok(json) = serde_json::from_slice::<Value>(&output.stdout) {
                let ok = json.get("ok").and_then(Value::as_bool).unwrap_or(output.status.success());
                let message = json
                    .get("message")
                    .and_then(Value::as_str)
                    .unwrap_or("Install report finished.")
                    .to_string();
                return ActionResponse { ok, message };
            }

            let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
            ActionResponse {
                ok: output.status.success(),
                message: if stderr.is_empty() {
                    String::from("Install report finished.")
                } else {
                    stderr
                },
            }
        },
        Err(error) => ActionResponse { ok: false, message: error.to_string() },
    }
}

pub fn yay_install_command_spec() -> CommandSpec {
    let script = concat!(
        "set -euo pipefail; ",
        "workdir=\"$(mktemp -d)\"; ",
        "trap 'rm -rf \"$workdir\"' EXIT; ",
        "sudo pacman -S --needed git base-devel; ",
        "git clone https://aur.archlinux.org/yay.git \"$workdir/yay\"; ",
        "cd \"$workdir/yay\"; ",
        "makepkg -si"
    );

    CommandSpec {
        label: String::from("Install yay"),
        preview: String::from(
            "sudo pacman -S --needed git base-devel\n\
git clone https://aur.archlinux.org/yay.git <tmp>/yay\n\
cd <tmp>/yay\n\
makepkg -si",
        ),
        argv: terminal_argv(script),
    }
}

fn terminal_argv(script: &str) -> Vec<String> {
    let wrapped = format!("{script}; code=$?; echo; read -n 1 -s -r -p 'Press any key to close'; exit $code");
    if command_exists("konsole") {
        vec![
            String::from("konsole"),
            String::from("-e"),
            String::from("bash"),
            String::from("-lc"),
            wrapped,
        ]
    } else {
        vec![String::from("bash"), String::from("-lc"), script.to_string()]
    }
}
