const KESKOS_LAUNCHER_WIDGET = "org.kde.plasma.simplekickoff";
const KICKER_WIDGET = "org.kde.plasma.kicker";
const KICKOFF_WIDGET = "org.kde.plasma.kickoff";
const TASKS_WIDGET = "org.kde.plasma.icontasks";
const WORKSPACE_WIDGET = "com.keskos.workspaceswitcher";
const PANEL_MARKER = "keskos-bottom-panel-v1";
const PANEL_HEIGHT = 48;

function hasWidget(widgetType) {
    return knownWidgetTypes.indexOf(widgetType) !== -1;
}

function firstExistingDesktopId(candidates) {
    for (let i = 0; i < candidates.length; ++i) {
        if (applicationPath(candidates[i])) {
            return candidates[i];
        }
    }

    return "";
}

function asLauncher(desktopId) {
    return desktopId ? "applications:" + desktopId : "";
}

function resolveBrowserDesktopId() {
    return defaultApplication("browser", true)
        || firstExistingDesktopId(["librewolf.desktop", "zen-browser.desktop", "zen.desktop", "brave-browser.desktop", "brave.desktop"])
        || "keskos-browser.desktop";
}

function resolveTerminalDesktopId() {
    return firstExistingDesktopId(["org.kde.konsole.desktop", "konsole.desktop"])
        || defaultApplication("terminal", true)
        || "keskos-terminal.desktop";
}

function resolveFilesDesktopId() {
    return firstExistingDesktopId(["org.kde.dolphin.desktop", "dolphin.desktop"])
        || defaultApplication("filemanager", true)
        || "keskos-files.desktop";
}

function resolveSettingsDesktopId() {
    return firstExistingDesktopId(["systemsettings.desktop", "org.kde.systemsettings.desktop", "kdesystemsettings.desktop"])
        || "systemsettings.desktop";
}

function resolvePanelTerminalDesktopId() {
    return firstExistingDesktopId(["keskos-terminal.desktop"]) || resolveTerminalDesktopId();
}

function resolvePanelFilesDesktopId() {
    return firstExistingDesktopId(["keskos-files.desktop"]) || resolveFilesDesktopId();
}

function resolvePanelBrowserDesktopId() {
    return firstExistingDesktopId(["keskos-browser.desktop"]) || resolveBrowserDesktopId();
}

function resolvePanelSettingsDesktopId() {
    return firstExistingDesktopId(["keskos-settings.desktop"]) || resolveSettingsDesktopId();
}

function resolveLauncherWidgetType() {
    if (hasWidget(KESKOS_LAUNCHER_WIDGET)) {
        return KESKOS_LAUNCHER_WIDGET;
    }

    if (hasWidget(KICKER_WIDGET)) {
        return KICKER_WIDGET;
    }

    if (hasWidget(KICKOFF_WIDGET)) {
        return KICKOFF_WIDGET;
    }

    return "";
}

function unique(items) {
    const seen = {};
    const result = [];

    for (let i = 0; i < items.length; ++i) {
        const item = items[i];
        if (!item || seen[item]) {
            continue;
        }

        seen[item] = true;
        result.push(item);
    }

    return result;
}

function configureLauncher(widget) {
    if (!widget) {
        return;
    }

    const favorites = unique([
        resolveTerminalDesktopId(),
        resolveFilesDesktopId(),
        resolvePanelBrowserDesktopId(),
        resolveSettingsDesktopId()
    ]).filter(function(entry) {
        return entry && entry.length > 0;
    });

    widget.currentConfigGroup = new Array("General");
    widget.writeConfig("icon", "keskos-launcher");
    widget.writeConfig("useCustomButtonImage", false);
    widget.writeConfig("customButtonImage", "");
    widget.writeConfig("menuLabel", "");

    if (widget.type === KESKOS_LAUNCHER_WIDGET) {
        widget.writeConfig("favorites", favorites);
        widget.writeConfig("systemFavorites", ["suspend", "reboot", "shutdown", "logout"]);
        widget.writeConfig("primaryActions", 3);
        widget.writeConfig("paneSwap", false);
        widget.writeConfig("favoritesDisplay", 0);
        widget.writeConfig("applicationsDisplay", 0);
        widget.writeConfig("alphaSort", false);
        widget.writeConfig("showActionButtonCaptions", false);
        widget.writeConfig("compactMode", true);
        widget.writeConfig("pin", false);
    } else {
        widget.writeConfig("favoriteApps", favorites.join(","));
        widget.writeConfig("favoriteSystemActions", "logout,reboot,shutdown");
        widget.writeConfig("showRecentApps", false);
        widget.writeConfig("showRecentDocs", false);
        widget.writeConfig("showRecentContacts", false);
        widget.writeConfig("showPowerSession", true);
        widget.writeConfig("useExtraRunners", false);
        widget.writeConfig("switchTabsOnHover", false);
    }
}

function configureTasks(widget) {
    if (!widget) {
        return;
    }

    widget.currentConfigGroup = new Array("General");
    widget.writeConfig("launchers", unique([
        asLauncher(resolvePanelTerminalDesktopId()),
        asLauncher(resolvePanelFilesDesktopId()),
        asLauncher(resolvePanelBrowserDesktopId()),
        asLauncher(resolvePanelSettingsDesktopId())
    ]).join(","));
    widget.writeConfig("fill", true);
    widget.writeConfig("iconSpacing", 0);
    widget.writeConfig("indicateAudioStreams", false);
    widget.writeConfig("separateLaunchers", true);
}

var panel = new Panel
panel.location = "bottom"
panel.height = PANEL_HEIGHT
panel.lengthMode = "fill"
panel.hiding = "none"
panel.currentConfigGroup = new Array("General")
panel.writeConfig("keskosPanel", PANEL_MARKER)

var launcherType = resolveLauncherWidgetType()
var launcher = launcherType ? panel.addWidget(launcherType) : null
var tasks = panel.addWidget(TASKS_WIDGET)
var workspace = hasWidget(WORKSPACE_WIDGET) ? panel.addWidget(WORKSPACE_WIDGET) : null

if (launcher) {
    launcher.index = 0
    configureLauncher(launcher)
}

tasks.index = launcher ? 1 : 0
configureTasks(tasks)

if (workspace) {
    workspace.index = launcher ? 2 : 1
}

var order = []
if (launcher) {
    order.push(String(launcher.id))
}
order.push(String(tasks.id))
if (workspace) {
    order.push(String(workspace.id))
}

panel.currentConfigGroup = new Array("General")
panel.writeConfig("AppletOrder", order.join(";"))
