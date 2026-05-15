/*
 *  SPDX-FileCopyrightText: 2026 memegeko
 *  SPDX-FileCopyrightText: 2025 Walter Rodrigues <wmr2@cin.ufpe.br>
 *  SPDX-License-Identifier: GPL-3.0-or-later
 */

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.plasma.plasmoid
import org.kde.plasma.private.kicker 0.1 as Kicker

PlasmoidItem {
    id: root

    readonly property color accentColor: plasmoid.configuration.accentColor || "#ce6a35"
    readonly property color backgroundColor: "#050505"
    readonly property color panelColor: "#080706"
    readonly property color panelAltColor: "#11100e"
    readonly property color textColor: "#b8afa6"
    readonly property color dimTextColor: "#8f8a84"
    readonly property color borderColor: Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.85)
    readonly property color hoverColor: Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.18)
    readonly property color selectedColor: Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.28)
    readonly property bool showLabel: plasmoid.configuration.showLabel !== false
    readonly property bool showPowerCategory: plasmoid.configuration.showPowerCategory !== false
    readonly property int configuredMenuWidth: Math.max(320, plasmoid.configuration.menuWidth || 360)
    readonly property int configuredMenuHeight: Math.max(360, plasmoid.configuration.menuHeight || 420)
    readonly property url logoSource: Qt.resolvedUrl("../images/keskos-launcher.svg")
    readonly property QtObject globalFavorites: rootModel ? rootModel.favoritesModel : null
    readonly property QtObject systemFavorites: rootModel ? rootModel.systemFavoritesModel : null
    readonly property string statusLine: runnerModel.querying
        ? "SEARCH PIPELINE ACTIVE"
        : (rootModel.count > 0 ? "APPLICATION INDEX ONLINE" : "INITIALIZING APPLICATION INDEX")
    readonly property var powerItems: [
        { "id": "lock", "name": "Lock Session", "comment": "Require credentials to return", "icon": "system-lock-screen" },
        { "id": "logout", "name": "Log Out", "comment": "Close the current Plasma session", "icon": "system-log-out" },
        { "id": "sleep", "name": "Sleep", "comment": "Suspend this machine safely", "icon": "system-suspend" },
        { "id": "restart", "name": "Restart", "comment": "Reboot the system", "icon": "system-reboot" },
        { "id": "shutdown", "name": "Shut Down", "comment": "Power off the system", "icon": "system-shutdown" }
    ]

    property var categoryItems: [{ "key": "favorites", "label": "Favorites", "row": -1 }]
    property string powerErrorMessage: ""
    property string currentPowerAction: ""

    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    Plasmoid.icon: "keskos-launcher"
    Plasmoid.status: PlasmaCore.Types.ActiveStatus
    Plasmoid.title: "KeskOS Launcher"

    preferredRepresentation: compactRepresentation

    Layout.minimumWidth: showLabel ? 92 : 46
    Layout.preferredWidth: showLabel ? 92 : 46
    Layout.minimumHeight: 46
    Layout.fillHeight: true

    implicitWidth: showLabel ? 92 : 46
    implicitHeight: 46

    function rebuildCategories() {
        const next = [{ "key": "favorites", "label": "Favorites", "row": -1 }]
        const seen = { "favorites": true }

        for (let row = 0; row < rootModel.count; ++row) {
            let label = ""

            try {
                label = rootModel.labelForRow(row)
            } catch (error) {
                label = ""
            }

            if (!label) {
                try {
                    label = rootModel.data(rootModel.index(row, 0), Qt.DisplayRole)
                } catch (error) {
                    label = ""
                }
            }

            label = String(label || "").trim()
            if (!label) {
                continue
            }

            const normalized = label.toLowerCase()
            if (seen[normalized]) {
                continue
            }

            seen[normalized] = true
            next.push({
                "key": "row:" + row,
                "label": label,
                "row": row
            })
        }

        if (root.showPowerCategory) {
            next.push({
                "key": "power",
                "label": "Power / Session",
                "row": -1
            })
        }

        root.categoryItems = next
    }

    function commandForPowerAction(actionId) {
        switch (actionId) {
        case "lock":
            return "qdbus org.kde.screensaver /ScreenSaver Lock"
        case "logout":
            return "qdbus org.kde.Shutdown /Shutdown org.kde.Shutdown.logout"
        case "sleep":
            return "qdbus org.kde.Solid.PowerManagement /org/kde/Solid/PowerManagement/Actions/SuspendSession org.kde.Solid.PowerManagement.Actions.SuspendSession.suspend"
        case "restart":
            return "qdbus org.kde.Shutdown /Shutdown org.kde.Shutdown.logoutAndReboot"
        case "shutdown":
            return "qdbus org.kde.Shutdown /Shutdown org.kde.Shutdown.logoutAndShutdown"
        default:
            return ""
        }
    }

    function fallbackPowerCommand(actionId) {
        switch (actionId) {
        case "lock":
            return "loginctl lock-session"
        case "logout":
            return "qdbus org.kde.ksmserver /KSMServer logout 1 0 0"
        case "sleep":
            return "systemctl suspend"
        case "restart":
            return "systemctl reboot"
        case "shutdown":
            return "systemctl poweroff"
        default:
            return ""
        }
    }

    function triggerPowerAction(actionId) {
        const command = commandForPowerAction(actionId)
        if (!command) {
            return
        }

        root.powerErrorMessage = ""
        root.currentPowerAction = actionId
        commandRunner.exec(command)
        root.expanded = false
    }

    Kicker.RootModel {
        id: rootModel

        autoPopulate: true
        appNameFormat: 0
        flat: false
        sorted: true
        showSeparators: false
        showTopLevelItems: false
        appletInterface: root
        showAllApps: true
        showAllAppsCategorized: true
        showRecentApps: false
        showRecentDocs: false
        showPowerSession: false

        onRefreshed: root.rebuildCategories()
        onCountChanged: root.rebuildCategories()

        Component.onCompleted: {
            favoritesModel.initForClient("org.kde.plasma.kicker.favorites.instance-" + Plasmoid.id)

            if (!Plasmoid.configuration.favoritesPortedToKAstats) {
                if (favoritesModel.count < 1) {
                    favoritesModel.portOldFavorites(Plasmoid.configuration.favoriteApps)
                }
                Plasmoid.configuration.favoritesPortedToKAstats = true
            }

            root.rebuildCategories()
            refresh()
        }
    }

    Connections {
        target: rootModel

        function onRowsInserted() {
            root.rebuildCategories()
        }

        function onRowsRemoved() {
            root.rebuildCategories()
        }

        function onModelReset() {
            root.rebuildCategories()
        }
    }

    Connections {
        target: globalFavorites

        function onFavoritesChanged() {
            if (target) {
                Plasmoid.configuration.favoriteApps = target.favorites
            }
        }
    }

    Connections {
        target: systemFavorites

        function onFavoritesChanged() {
            if (target) {
                Plasmoid.configuration.favoriteSystemActions = target.favorites
            }
        }
    }

    Connections {
        target: Plasmoid.configuration

        function onFavoriteAppsChanged() {
            if (globalFavorites) {
                globalFavorites.favorites = Plasmoid.configuration.favoriteApps
            }
        }

        function onFavoriteSystemActionsChanged() {
            if (systemFavorites) {
                systemFavorites.favorites = Plasmoid.configuration.favoriteSystemActions
            }
        }
    }

    Kicker.RunnerModel {
        id: runnerModel
        appletInterface: root
        favoritesModel: globalFavorites
        mergeResults: true
        runners: [
            "krunner_services",
            "krunner_systemsettings",
            "krunner_sessions",
            "krunner_powerdevil",
            "calculator",
            "unitconverter"
        ]
    }

    Plasma5Support.DataSource {
        id: commandRunner
        engine: "executable"
        connectedSources: []

        function exec(command) {
            if (command) {
                connectSource(command)
            }
        }

        onNewData: function(sourceName, data) {
            const exitCode = Number(data["exit code"] || 1)
            const action = root.currentPowerAction

            if (action) {
                if (exitCode !== 0) {
                    const fallback = root.fallbackPowerCommand(action)
                    if (fallback && fallback !== sourceName) {
                        commandRunner.exec(fallback)
                        disconnectSource(sourceName)
                        return
                    }

                    root.powerErrorMessage = data["stderr"] || ("Power action failed: " + action)
                } else {
                    root.powerErrorMessage = ""
                }

                root.currentPowerAction = ""
            }

            disconnectSource(sourceName)
        }
    }

    compactRepresentation: Item {
        Layout.minimumWidth: root.showLabel ? 92 : 46
        Layout.preferredWidth: root.showLabel ? 92 : 46
        Layout.minimumHeight: 46
        Layout.fillHeight: true

        Rectangle {
            anchors.fill: parent
            color: mouseArea.pressed ? Qt.darker(root.panelColor, 1.35) : (mouseArea.containsMouse ? root.hoverColor : root.panelColor)
            border.width: 1
            border.color: root.borderColor
        }

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.35)
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: root.showLabel ? 8 : 0
            anchors.rightMargin: root.showLabel ? 8 : 0
            anchors.topMargin: 6
            anchors.bottomMargin: 6
            spacing: 6

            Image {
                Layout.alignment: Qt.AlignVCenter
                Layout.preferredWidth: 22
                Layout.preferredHeight: 22
                source: root.logoSource
                fillMode: Image.PreserveAspectFit
                smooth: true
                mipmap: true
                sourceSize.width: 44
                sourceSize.height: 44
            }

            Text {
                Layout.fillWidth: true
                visible: root.showLabel
                text: "KESK"
                color: root.accentColor
                font.family: "JetBrains Mono"
                font.pixelSize: 18
                font.letterSpacing: 2
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.expanded = !root.expanded
        }
    }

    onExpandedChanged: {
        if (root.expanded) {
            rootModel.refresh()
            Qt.callLater(function() {
                if (fullRepresentationItem && fullRepresentationItem.focusSearchField) {
                    fullRepresentationItem.focusSearchField()
                }
            })
        }
    }

    fullRepresentation: LauncherPopup {
        launcherRoot: root
        categories: root.categoryItems
        favoritesModel: root.globalFavorites
        rootModel: root.rootModel
        runnerModel: runnerModel
        powerItems: root.powerItems
        statusLine: root.statusLine
        errorMessage: root.powerErrorMessage
        accentColor: root.accentColor
        backgroundColor: root.backgroundColor
        panelColor: root.panelColor
        panelAltColor: root.panelAltColor
        textColor: root.textColor
        dimTextColor: root.dimTextColor
        borderColor: root.borderColor
        hoverColor: root.hoverColor
        selectedColor: root.selectedColor
        menuWidth: root.configuredMenuWidth
        menuHeight: root.configuredMenuHeight
        showPowerCategory: root.showPowerCategory
        onPowerRequested: function(actionId) {
            root.triggerPowerAction(actionId)
        }
        onCloseRequested: {
            root.expanded = false
        }
    }
}
