import Quickshell
import Quickshell.Io
import QtQuick

Scope {
    id: root

    property color accent: "#ce6a35"
    property color accentSoft: "#8f8a84"
    property color text: "#b8afa6"
    property color panelBg: "#080706"
    property color panelEdge: "#11100e"
    property color hoverFill: "#24ce6a35"
    property color activeFill: "#2dce6a35"
    property color separator: "#30ce6a35"
    property int topBarHeight: 34
    property string helperPath: "/usr/local/bin/keskos-quickshell-data"
    property string assetRoot: "/usr/share/keskos/panel-icons"
    property string activePopup: ""
    property var activePopupScreen: null
    property string commandToRun: ""
    property var barData: ({
        "cpu_percent": 0,
        "mem_percent": 0,
        "clock": "--:--",
        "net_glyph": "....",
        "net_status": "OFFLINE",
        "media_status": "OFFLINE",
        "media_active": false
    })
    property var mediaMenuData: ({
        "active": false,
        "player": "PLAYER",
        "status": "IDLE",
        "title": "No active player",
        "artist": "Start playback in a media app",
        "album": "",
        "art_url": "",
        "position": "0:00",
        "length": "0:00",
        "progress_percent": 0,
        "volume_percent": 0
    })
    property var networkMenuData: ({
        "status": "DISCONNECTED",
        "primary_connection": "No active network link",
        "wifi_enabled": false,
        "networking_enabled": false,
        "connected": [],
        "available": []
    })
    property var cpuMenuData: ({
        "usage": "0%",
        "usage_value": 0,
        "load1": "0.00",
        "load5": "0.00",
        "load15": "0.00",
        "cores": "0",
        "frequency": "n/a",
        "temperature": "n/a",
        "model": "Unknown CPU",
        "segments_filled": 0,
        "core_usages": []
    })
    property var memoryMenuData: ({
        "total": "0.00 GiB",
        "used": "0.00 GiB",
        "free": "0.00 GiB",
        "cached": "0.00 GiB",
        "swap_total": "0.00 GiB",
        "swap_used": "0.00 GiB",
        "percent": "0%",
        "percent_value": 0,
        "segments_filled": 0
    })

    function parseObjectJson(text, fallback) {
        try {
            const parsed = JSON.parse(text.trim())
            return parsed && typeof parsed === "object" ? parsed : fallback
        } catch (error) {
            return fallback
        }
    }

    function commandFor(argv) {
        return ["bash", "-lc", argv]
    }

    function shellQuote(value) {
        return "'" + String(value).replace(/'/g, "'\"'\"'") + "'"
    }

    function helperCommand(section, extraArgs) {
        let command = "helper=\"\"; "
        command += "if [ -x \"$HOME/.local/bin/keskos-quickshell-data\" ]; then helper=\"$HOME/.local/bin/keskos-quickshell-data\"; "
        command += "elif [ -x /usr/local/bin/keskos-quickshell-data ]; then helper=/usr/local/bin/keskos-quickshell-data; "
        command += "elif [ -x /usr/bin/keskos-quickshell-data ]; then helper=/usr/bin/keskos-quickshell-data; "
        command += "else exit 1; fi; exec \"$helper\" " + root.shellQuote(section)

        for (let i = 0; i < extraArgs.length; ++i) {
            command += " " + root.shellQuote(extraArgs[i])
        }

        return command
    }

    function launchCommand(command) {
        if (!command || command.length === 0) {
            return
        }

        root.commandToRun = command
        commandProc.running = false
        commandProc.running = true
    }

    function startProcess(proc) {
        proc.running = false
        proc.running = true
    }

    function closePopup() {
        root.activePopup = ""
        root.activePopupScreen = null
    }

    function popupActiveOnScreen(name, screenObject) {
        return root.activePopup === name && root.activePopupScreen === screenObject
    }

    function togglePopup(name, screenObject) {
        if (root.activePopup === name && root.activePopupScreen === screenObject) {
            root.closePopup()
            return
        }

        root.activePopup = name
        root.activePopupScreen = screenObject
        root.refreshPopupData()
    }

    function refreshBarData() {
        root.startProcess(barProc)
    }

    function refreshPopupData() {
        if (root.activePopup === "network") {
            root.startProcess(networkMenuProc)
        } else if (root.activePopup === "cpu") {
            root.startProcess(cpuMenuProc)
        } else if (root.activePopup === "memory") {
            root.startProcess(memoryMenuProc)
        } else if (root.activePopup === "media") {
            root.startProcess(mediaMenuProc)
        }

        root.refreshBarData()
    }

    function powerActionCommand(action) {
        switch (action) {
        case "lock":
            return "if command -v loginctl >/dev/null 2>&1; then loginctl lock-session; elif command -v qdbus6 >/dev/null 2>&1; then qdbus6 org.freedesktop.ScreenSaver /ScreenSaver Lock; elif command -v qdbus >/dev/null 2>&1; then qdbus org.freedesktop.ScreenSaver /ScreenSaver Lock; fi"
        case "logout":
            return "if command -v qdbus6 >/dev/null 2>&1; then qdbus6 org.kde.Shutdown /Shutdown org.kde.Shutdown.logout; elif command -v qdbus >/dev/null 2>&1; then qdbus org.kde.Shutdown /Shutdown org.kde.Shutdown.logout; fi"
        case "suspend":
            return "if command -v systemctl >/dev/null 2>&1; then systemctl suspend; fi"
        case "reboot":
            return "if command -v systemctl >/dev/null 2>&1; then systemctl reboot; fi"
        case "poweroff":
            return "if command -v systemctl >/dev/null 2>&1; then systemctl poweroff; fi"
        default:
            return ""
        }
    }

    function terminalMonitorCommand() {
        return "if command -v btop >/dev/null 2>&1; then exec konsole -e btop; elif command -v btop++ >/dev/null 2>&1; then exec konsole -e btop++; elif command -v plasma-systemmonitor >/dev/null 2>&1; then exec plasma-systemmonitor; elif command -v systemmonitor >/dev/null 2>&1; then exec systemmonitor; elif command -v ksysguard >/dev/null 2>&1; then exec ksysguard; else exec systemsettings; fi"
    }

    function mediaActionCommand(action) {
        return root.helperCommand("media-action", [action])
    }

    function networkActionCommand(action, payload) {
        const item = payload || {}
        return root.helperCommand("network-action", [
            action,
            item.connection || "",
            item.device || "",
            item.ssid || "",
            item.known === false ? "false" : "true"
        ])
    }

    function cpuRows() {
        const data = root.cpuMenuData || {}
        const rows = [
            { "label": "USAGE", "value": data.usage || "0%", "highlight": true },
            { "label": "LOAD 1 / 5 / 15", "value": (data.load1 || "0.00") + " / " + (data.load5 || "0.00") + " / " + (data.load15 || "0.00") },
            { "label": "CORES", "value": String(data.cores || "0") },
            { "label": "FREQ", "value": data.frequency || "n/a" },
            { "label": "TEMP", "value": data.temperature || "n/a" }
        ]
        const cores = data.core_usages || []

        for (let i = 0; i < Math.min(4, cores.length); ++i) {
            const value = Number(cores[i])
            rows.push({
                "label": "CORE " + (i + 1),
                "value": String(value) + "%",
                "highlight": value >= 70
            })
        }

        return rows
    }

    function memoryRows() {
        const data = root.memoryMenuData || {}
        return [
            { "label": "USAGE", "value": data.percent || "0%", "highlight": true },
            { "label": "USED / TOTAL", "value": (data.used || "0.00 GiB") + " / " + (data.total || "0.00 GiB") },
            { "label": "FREE", "value": data.free || "0.00 GiB" },
            { "label": "CACHED", "value": data.cached || "0.00 GiB" },
            { "label": "SWAP", "value": (data.swap_used || "0.00 GiB") + " / " + (data.swap_total || "0.00 GiB") }
        ]
    }

    Process {
        id: barProc
        command: root.commandFor(root.helperCommand("shell-bar", []))
        running: true

        stdout: StdioCollector {
            onStreamFinished: root.barData = root.parseObjectJson(this.text, root.barData)
        }
    }

    Timer {
        interval: 2000
        repeat: true
        running: true
        onTriggered: root.refreshBarData()
    }

    Process {
        id: mediaMenuProc
        command: root.commandFor(root.helperCommand("media-menu", []))
        running: false

        stdout: StdioCollector {
            onStreamFinished: root.mediaMenuData = root.parseObjectJson(this.text, root.mediaMenuData)
        }
    }

    Process {
        id: networkMenuProc
        command: root.commandFor(root.helperCommand("network-menu", []))
        running: false

        stdout: StdioCollector {
            onStreamFinished: root.networkMenuData = root.parseObjectJson(this.text, root.networkMenuData)
        }
    }

    Process {
        id: cpuMenuProc
        command: root.commandFor(root.helperCommand("cpu-menu", []))
        running: false

        stdout: StdioCollector {
            onStreamFinished: root.cpuMenuData = root.parseObjectJson(this.text, root.cpuMenuData)
        }
    }

    Process {
        id: memoryMenuProc
        command: root.commandFor(root.helperCommand("memory", []))
        running: false

        stdout: StdioCollector {
            onStreamFinished: root.memoryMenuData = root.parseObjectJson(this.text, root.memoryMenuData)
        }
    }

    Process {
        id: commandProc
        command: root.commandFor(root.commandToRun)
        running: false
    }

    Timer {
        id: popupRefreshTimer
        interval: 2500
        repeat: true
        running: root.activePopup.length > 0
        onTriggered: root.refreshPopupData()
    }

    Timer {
        id: actionRefreshTimer
        interval: 1200
        repeat: false
        onTriggered: root.refreshPopupData()
    }

    Variants {
        model: Quickshell.screens

        PanelWindow {
            id: panelRoot

            required property var modelData

            screen: modelData
            color: "transparent"
            focusable: false
            aboveWindows: true
            implicitHeight: root.topBarHeight
            exclusiveZone: root.topBarHeight
            anchors {
                top: true
                left: true
                right: true
            }

            TopBar {
                id: topBar
                anchors.fill: parent
                theme: root
                barData: root.barData
                activePopup: root.activePopupScreen === panelRoot.modelData ? root.activePopup : ""
                onPopupToggleRequested: function(popupName) {
                    root.togglePopup(popupName, panelRoot.modelData)
                }
            }

            PopupWindow {
                id: mediaPopup

                visible: root.popupActiveOnScreen("media", panelRoot.modelData)
                color: "transparent"
                implicitWidth: mediaMenu.implicitWidth
                implicitHeight: mediaMenu.implicitHeight

                anchor.item: topBar.mediaAnchor
                anchor.edges: Edges.Bottom | Edges.Right
                anchor.gravity: Edges.Bottom | Edges.Left
                anchor.margins.top: 6
                anchor.adjustment: PopupAdjustment.All

                onVisibleChanged: {
                    if (!visible && root.popupActiveOnScreen("media", panelRoot.modelData)) {
                        root.closePopup()
                    }
                }

                MediaMenu {
                    id: mediaMenu
                    anchors.fill: parent
                    theme: root
                    menuData: root.mediaMenuData
                    onActionSelected: function(action) {
                        root.launchCommand(root.mediaActionCommand(action))
                        actionRefreshTimer.restart()
                    }
                    onDismissRequested: root.closePopup()
                }
            }

            PopupWindow {
                id: powerPopup

                visible: root.popupActiveOnScreen("power", panelRoot.modelData)
                color: "transparent"
                implicitWidth: powerMenu.implicitWidth
                implicitHeight: powerMenu.implicitHeight

                anchor.item: topBar.powerAnchor
                anchor.edges: Edges.Bottom | Edges.Right
                anchor.gravity: Edges.Bottom | Edges.Left
                anchor.margins.top: 6
                anchor.adjustment: PopupAdjustment.All

                onVisibleChanged: {
                    if (!visible && root.popupActiveOnScreen("power", panelRoot.modelData)) {
                        root.closePopup()
                    }
                }

                PowerMenu {
                    id: powerMenu
                    anchors.fill: parent
                    theme: root
                    onActionSelected: {
                        root.closePopup()
                        root.launchCommand(root.powerActionCommand(action))
                    }
                    onDismissRequested: root.closePopup()
                }
            }

            PopupWindow {
                id: networkPopup

                visible: root.popupActiveOnScreen("network", panelRoot.modelData)
                color: "transparent"
                implicitWidth: networkMenu.implicitWidth
                implicitHeight: networkMenu.implicitHeight

                anchor.item: topBar.networkAnchor
                anchor.edges: Edges.Bottom | Edges.Right
                anchor.gravity: Edges.Bottom | Edges.Left
                anchor.margins.top: 6
                anchor.adjustment: PopupAdjustment.All

                onVisibleChanged: {
                    if (!visible && root.popupActiveOnScreen("network", panelRoot.modelData)) {
                        root.closePopup()
                    }
                }

                NetworkMenu {
                    id: networkMenu
                    anchors.fill: parent
                    theme: root
                    menuData: root.networkMenuData
                    onNetworkActionSelected: {
                        root.launchCommand(root.networkActionCommand(action, networkItem))
                        actionRefreshTimer.restart()
                    }
                    onQuickActionSelected: {
                        if (action === "open-settings") {
                            root.closePopup()
                        }
                        root.launchCommand(root.networkActionCommand(action, {}))
                        actionRefreshTimer.restart()
                    }
                }
            }

            PopupWindow {
                id: cpuPopup

                visible: root.popupActiveOnScreen("cpu", panelRoot.modelData)
                color: "transparent"
                implicitWidth: cpuMenu.implicitWidth
                implicitHeight: cpuMenu.implicitHeight

                anchor.item: topBar.cpuAnchor
                anchor.edges: Edges.Bottom | Edges.Right
                anchor.gravity: Edges.Bottom | Edges.Left
                anchor.margins.top: 6
                anchor.adjustment: PopupAdjustment.All

                onVisibleChanged: {
                    if (!visible && root.popupActiveOnScreen("cpu", panelRoot.modelData)) {
                        root.closePopup()
                    }
                }

                StatMenu {
                    id: cpuMenu
                    anchors.fill: parent
                    theme: root
                    title: "CPU DIAGNOSTICS"
                    rows: root.cpuRows()
                    footerText: root.cpuMenuData.model || ""
                    meterLabel: "CPU LOAD"
                    meterValue: root.cpuMenuData.usage_value || 0
                    actionLabel: "OPEN BTOP++"
                    onActionRequested: {
                        root.closePopup()
                        root.launchCommand(root.terminalMonitorCommand())
                    }
                    onDismissRequested: root.closePopup()
                }
            }

            PopupWindow {
                id: memoryPopup

                visible: root.popupActiveOnScreen("memory", panelRoot.modelData)
                color: "transparent"
                implicitWidth: memoryMenu.implicitWidth
                implicitHeight: memoryMenu.implicitHeight

                anchor.item: topBar.memoryAnchor
                anchor.edges: Edges.Bottom | Edges.Right
                anchor.gravity: Edges.Bottom | Edges.Left
                anchor.margins.top: 6
                anchor.adjustment: PopupAdjustment.All

                onVisibleChanged: {
                    if (!visible && root.popupActiveOnScreen("memory", panelRoot.modelData)) {
                        root.closePopup()
                    }
                }

                StatMenu {
                    id: memoryMenu
                    anchors.fill: parent
                    theme: root
                    title: "MEMORY STATUS"
                    rows: root.memoryRows()
                    footerText: "Live memory data from /proc/meminfo"
                    meterLabel: "RAM USE"
                    meterValue: root.memoryMenuData.percent_value || 0
                    actionLabel: "OPEN BTOP++"
                    onActionRequested: {
                        root.closePopup()
                        root.launchCommand(root.terminalMonitorCommand())
                    }
                    onDismissRequested: root.closePopup()
                }
            }
        }
    }
}
