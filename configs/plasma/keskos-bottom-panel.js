const MARKER = "keskos-bottom-panel-v1";
const TOP_RESERVE_MARKER = "keskos-top-reserve-v1";
const KESKOS_LAUNCHER_WIDGET = "org.kde.plasma.simplekickoff";
const KICKOFF_WIDGET = "org.kde.plasma.kickoff";
const KICKER_WIDGET = "org.kde.plasma.kicker";
const TASKS_WIDGET = "org.kde.plasma.icontasks";
const LEGACY_TASK_WIDGETS = ["org.kde.plasma.taskmanager"];
const WORKSPACE_WIDGET = "com.keskos.workspaceswitcher";
const LEGACY_PAGER_WIDGETS = ["org.kde.plasma.pager", "org.kde.plasma.activitypager"];
const WORKSPACE_WIDGET_CANDIDATES = [WORKSPACE_WIDGET].concat(LEGACY_PAGER_WIDGETS);
const BOTTOM_PANEL_HEIGHT = 48;
const DEFAULT_LAUNCHER_MODE = "keskos";
const CUSTOM_LAUNCHER_ICON = "keskos-launcher";

function arrayHas(items, value) {
    return items && items.indexOf(value) !== -1;
}

function widgetAvailable(widgetType) {
    return arrayHas(knownWidgetTypes, widgetType);
}

function firstExistingDesktopId(candidates) {
    for (let i = 0; i < candidates.length; ++i) {
        if (applicationPath(candidates[i])) {
            return candidates[i];
        }
    }

    return "";
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
    return firstExistingDesktopId(["org.kde.systemsettings.desktop", "systemsettings.desktop", "kdesystemsettings.desktop"])
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

function resolveWorkspaceWidgetType() {
    for (let i = 0; i < WORKSPACE_WIDGET_CANDIDATES.length; ++i) {
        if (widgetAvailable(WORKSPACE_WIDGET_CANDIDATES[i])) {
            return WORKSPACE_WIDGET_CANDIDATES[i];
        }
    }

    return WORKSPACE_WIDGET;
}

function resolveLauncherMode() {
    if (DEFAULT_LAUNCHER_MODE === "keskos" && widgetAvailable(KESKOS_LAUNCHER_WIDGET)) {
        return "keskos";
    }

    return "kde";
}

function resolveNativeLauncherWidgetType() {
    if (widgetAvailable(KICKER_WIDGET)) {
        return KICKER_WIDGET;
    }

    if (widgetAvailable(KICKOFF_WIDGET)) {
        return KICKOFF_WIDGET;
    }

    return "";
}

function resolveLauncherWidgetType() {
    const launcherMode = resolveLauncherMode();

    if (launcherMode === "keskos" && widgetAvailable(KESKOS_LAUNCHER_WIDGET)) {
        return KESKOS_LAUNCHER_WIDGET;
    }

    return resolveNativeLauncherWidgetType();
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

function asLauncher(desktopId) {
    return desktopId ? "applications:" + desktopId : "";
}

function defaultLaunchers() {
    const launchers = [];

    launchers.push(asLauncher(resolvePanelTerminalDesktopId()));
    launchers.push(asLauncher(resolvePanelFilesDesktopId()));
    launchers.push(asLauncher(resolvePanelBrowserDesktopId()));
    launchers.push(asLauncher(resolvePanelSettingsDesktopId()));

    return unique(launchers);
}

function findManagedPanel(marker) {
    const panelList = panels();

    for (let i = 0; i < panelList.length; ++i) {
        const panel = panelList[i];
        panel.currentConfigGroup = new Array("General");

        if (panel.readConfig("keskosPanel", "") === marker) {
            return panel;
        }
    }

    return null;
}

function removeDuplicateManagedPanels(marker, keepPanel) {
    const panelList = panels();

    for (let i = 0; i < panelList.length; ++i) {
        const panel = panelList[i];
        panel.currentConfigGroup = new Array("General");

        if (panel.readConfig("keskosPanel", "") !== marker) {
            continue;
        }

        if (keepPanel && panel.id === keepPanel.id) {
            continue;
        }

        try {
            panel.remove();
        } catch (error) {
        }
    }
}

function panelMarker(panel) {
    panel.currentConfigGroup = new Array("General");
    return panel.readConfig("keskosPanel", "");
}

function isBottomPanel(panel) {
    try {
        if (panel.location === "bottom") {
            return true;
        }
    } catch (error) {
    }

    return false;
}

function removeConflictingBottomPanels(keepPanel) {
    const panelList = panels();

    for (let i = 0; i < panelList.length; ++i) {
        const panel = panelList[i];

        if (keepPanel && panel.id === keepPanel.id) {
            continue;
        }

        if (panelMarker(panel) === MARKER || panelMarker(panel) === TOP_RESERVE_MARKER) {
            continue;
        }

        if (panel.screen !== 0) {
            continue;
        }

        if (!isBottomPanel(panel)) {
            continue;
        }

        try {
            panel.remove();
        } catch (error) {
        }
    }
}

function panelNeedsReset(panel) {
    if (!panel) {
        return true;
    }

    if (screenCount <= 1 && panel.screen !== 0) {
        return true;
    }

    return false;
}

function findWidget(panel, widgetTypes) {
    for (let i = 0; i < panel.widgetIds.length; ++i) {
        const widget = panel.widgetById(panel.widgetIds[i]);

        if (widget && arrayHas(widgetTypes, widget.type)) {
            return widget;
        }
    }

    return null;
}

function removeWidgets(panel, widgetTypes) {
    for (let i = panel.widgetIds.length - 1; i >= 0; --i) {
        const widget = panel.widgetById(panel.widgetIds[i]);
        if (widget && arrayHas(widgetTypes, widget.type)) {
            widget.remove();
        }
    }
}

function clearPanelWidgets(panel) {
    for (let i = panel.widgetIds.length - 1; i >= 0; --i) {
        const widget = panel.widgetById(panel.widgetIds[i]);
        if (widget) {
            widget.remove();
        }
    }
}

function removeManagedPanel(marker) {
    const panel = findManagedPanel(marker);

    if (!panel) {
        return;
    }

    try {
        panel.remove();
    } catch (error) {
    }
}

function configureKdeLauncher(widget) {
    if (!widget) {
        return;
    }

    const favorites = unique([
        resolveTerminalDesktopId(),
        resolveFilesDesktopId(),
        resolveBrowserDesktopId(),
        resolveSettingsDesktopId()
    ]);

    widget.currentConfigGroup = new Array("General");
    widget.writeConfig("icon", CUSTOM_LAUNCHER_ICON);
    widget.writeConfig("useCustomButtonImage", false);
    widget.writeConfig("customButtonImage", "");
    widget.writeConfig("menuLabel", "");
    widget.writeConfig("favoriteApps", favorites.join(","));
    widget.writeConfig("favoriteSystemActions", "logout,reboot,shutdown");

    if (widget.type === KICKER_WIDGET) {
        widget.writeConfig("showRecentApps", false);
        widget.writeConfig("showRecentDocs", false);
        widget.writeConfig("showRecentContacts", false);
        widget.writeConfig("showPowerSession", true);
        widget.writeConfig("useExtraRunners", false);
        widget.writeConfig("switchTabsOnHover", false);
    } else if (widget.type === KICKOFF_WIDGET) {
        widget.writeConfig("showRecentApps", false);
        widget.writeConfig("showRecentDocs", false);
        widget.writeConfig("showRecentContacts", false);
        widget.writeConfig("useExtraRunners", false);
    }

    widget.reloadConfig();
}

function configureKeskosLauncher(widget) {
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
    widget.writeConfig("icon", CUSTOM_LAUNCHER_ICON);
    widget.writeConfig("useCustomButtonImage", false);
    widget.writeConfig("customButtonImage", "");
    widget.writeConfig("menuLabel", "");
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

    widget.reloadConfig();
}

function configureTasks(widget) {
    widget.currentConfigGroup = new Array("General");
    const launcherDesktopId = asLauncher("keskos-launcher.desktop");
    const existingLaunchers = widget.readConfig("launchers", "");
    const currentLaunchers = existingLaunchers
        ? existingLaunchers.split(",").map(function(entry) {
            return entry.trim();
        }).filter(function(entry) {
            return entry.length > 0;
        })
        : [];

    let updatedLaunchers = currentLaunchers.filter(function(entry) {
        return entry !== launcherDesktopId;
    });

    if (!updatedLaunchers.length) {
        updatedLaunchers = defaultLaunchers();
    }

    if (updatedLaunchers.join(",") !== currentLaunchers.join(",")) {
        widget.writeConfig("launchers", unique(updatedLaunchers).join(","));
    }
    widget.writeConfig("fill", true);
    widget.writeConfig("iconSpacing", 0);
    widget.writeConfig("indicateAudioStreams", false);
    widget.writeConfig("separateLaunchers", true);
    widget.reloadConfig();
}

function configurePager(widget) {
    if (!widget) {
        return;
    }

    widget.currentConfigGroup = new Array("General");
    widget.reloadConfig();
}

function configurePanel(panel) {
    const launcherMode = resolveLauncherMode();
    const launcherType = resolveLauncherWidgetType();

    try {
        panel.screen = 0;
    } catch (error) {
    }

    panel.location = "bottom";
    panel.lengthMode = "fill";
    panel.hiding = "none";
    panel.height = BOTTOM_PANEL_HEIGHT;

    try {
        panel.floating = false;
    } catch (error) {
    }

    try {
        panel.floatingApplets = false;
    } catch (error) {
    }

    try {
        panel.opacityMode = 1;
    } catch (error) {
    }

    panel.currentConfigGroup = new Array("General");
    panel.writeConfig("keskosPanel", MARKER);

    let launcher = null;
    if (launcherType) {
        removeWidgets(panel, [KESKOS_LAUNCHER_WIDGET, KICKOFF_WIDGET, KICKER_WIDGET].filter(function(widgetType) {
            return widgetType !== launcherType;
        }));
        launcher = findWidget(panel, [launcherType]);
        if (!launcher) {
            launcher = panel.addWidget(launcherType);
        }
    }

    removeWidgets(panel, LEGACY_TASK_WIDGETS);
    let tasks = findWidget(panel, [TASKS_WIDGET]);
    if (!tasks) {
        tasks = panel.addWidget(TASKS_WIDGET);
    }

    const workspaceType = resolveWorkspaceWidgetType();
    let workspaceWidget = null;

    if (workspaceType === WORKSPACE_WIDGET && widgetAvailable(WORKSPACE_WIDGET)) {
        removeWidgets(panel, LEGACY_PAGER_WIDGETS);
        workspaceWidget = findWidget(panel, [WORKSPACE_WIDGET]);
        if (!workspaceWidget) {
            workspaceWidget = panel.addWidget(WORKSPACE_WIDGET);
        }
    } else {
        workspaceWidget = findWidget(panel, WORKSPACE_WIDGET_CANDIDATES);
        if (!workspaceWidget) {
            workspaceWidget = panel.addWidget(workspaceType);
        }
    }
    removeWidgets(panel, ["org.kde.plasma.clipboard", "org.kde.plasma.systemtray", "org.kde.plasma.digitalclock"]);

    if (launcher) {
        launcher.index = 0;
    }

    tasks.index = launcher ? 1 : 0;
    workspaceWidget.index = launcher ? 2 : 1;

    if (launcher && launcher.type === KESKOS_LAUNCHER_WIDGET) {
        configureKeskosLauncher(launcher);
    } else {
        configureKdeLauncher(launcher);
    }
    configureTasks(tasks);
    configurePager(workspaceWidget);

    const appletOrder = [];
    if (launcher) {
        appletOrder.push(String(launcher.id));
    }
    appletOrder.push(String(tasks.id));
    appletOrder.push(String(workspaceWidget.id));

    panel.currentConfigGroup = new Array("General");
    panel.writeConfig("AppletOrder", appletOrder.join(";"));
    panel.reloadConfig();
}

removeManagedPanel(TOP_RESERVE_MARKER);

let panel = findManagedPanel(MARKER);

if (panelNeedsReset(panel)) {
    removeDuplicateManagedPanels(MARKER, null);
    panel = new Panel;
}

removeDuplicateManagedPanels(MARKER, panel);
removeConflictingBottomPanels(panel);
configurePanel(panel);
