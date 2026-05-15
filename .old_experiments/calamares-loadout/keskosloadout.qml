import io.calamares.core 1.0

import QtQuick 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    width: parent ? parent.width : 1180
    height: parent ? parent.height : 720

    readonly property string storageKey: "packagechooser_keskos_loadout"
    readonly property color bg: "#050505"
    readonly property color panel: "#080706"
    readonly property color block: "#11100e"
    readonly property color accent: "#ce6a35"
    readonly property color textColor: "#b8afa6"
    readonly property color dimText: "#8f8a84"
    readonly property color borderColor: "#ce6a35"

    property var browserOptions: [
        {
            "key": "librewolf",
            "label": "LibreWolf",
            "tagline": "Privacy-focused Firefox-based browser.",
            "note": "Recommended for KeskOS. Hardened defaults."
        },
        {
            "key": "zen",
            "label": "Zen Browser",
            "tagline": "Modern Firefox-based browser with a clean workflow.",
            "note": "Clean workspace feel with Firefox foundations."
        },
        {
            "key": "brave",
            "label": "Brave",
            "tagline": "Chromium-based browser with built-in ad/tracker blocking.",
            "note": "Wide site compatibility with built-in blocking."
        }
    ]

    property var bundleOptions: [
        { "key": "gaming", "label": "Gaming", "packages": "steam · lutris · heroic · mangohud · gamemode · goverlay" },
        { "key": "chat", "label": "Chat", "packages": "discord · vesktop · telegram · signal" },
        { "key": "development", "label": "Development", "packages": "git · base-devel · code · vscodium · docker · nodejs" },
        { "key": "media", "label": "Media", "packages": "vlc · obs-studio · gimp · krita · audacity · kdenlive" },
        { "key": "office", "label": "Office", "packages": "libreoffice · okular · thunderbird" },
        { "key": "system_tools", "label": "System Tools", "packages": "fastfetch · btop · htop · gparted · timeshift · kdeconnect" },
        { "key": "customization", "label": "Customization", "packages": "kvantum · papirus-icon-theme · qt6ct" },
        { "key": "drivers_gaming", "label": "Drivers / Gaming Support", "packages": "vulkan-tools · vulkan-icd-loader · mesa-utils" }
    ]

    property var featureOptions: [
        { "key": "quickshell_topbar", "label": "Install KeskOS HUD / Quickshell top bar" },
        { "key": "kde_bottom_taskbar", "label": "Use KDE Plasma taskbar bottom panel" },
        { "key": "plasma_theme", "label": "Apply KeskOS Plasma theme" },
        { "key": "window_borders", "label": "Apply KeskOS window borders" },
        { "key": "sddm_theme", "label": "Apply KeskOS SDDM login theme" },
        { "key": "plymouth", "label": "Apply KeskOS Plymouth boot splash" },
        { "key": "browser_startpage", "label": "Install KeskOS browser startpage" },
        { "key": "gaming_tools", "label": "Install gaming performance tools" },
        { "key": "bluetooth", "label": "Enable Bluetooth tools" },
        { "key": "printing", "label": "Enable printing support" },
        { "key": "docker", "label": "Enable Docker support" },
        { "key": "nvidia", "label": "Enable NVIDIA support" }
    ]

    property var state: ({
        "browser": "librewolf",
        "apply_browser_theme": true,
        "bundles": [],
        "extra_packages": "",
        "features": {
            "quickshell_topbar": true,
            "kde_bottom_taskbar": true,
            "plasma_theme": true,
            "window_borders": true,
            "sddm_theme": true,
            "plymouth": true,
            "browser_startpage": true,
            "gaming_tools": false,
            "bluetooth": false,
            "printing": false,
            "docker": false,
            "nvidia": false
        }
    })

    function defaultState() {
        return {
            "browser": "librewolf",
            "apply_browser_theme": true,
            "bundles": [],
            "extra_packages": "",
            "features": {
                "quickshell_topbar": true,
                "kde_bottom_taskbar": true,
                "plasma_theme": true,
                "window_borders": true,
                "sddm_theme": true,
                "plymouth": true,
                "browser_startpage": true,
                "gaming_tools": false,
                "bluetooth": false,
                "printing": false,
                "docker": false,
                "nvidia": false
            }
        }
    }

    function parseState() {
        var parsed = defaultState()
        try {
            var stored = Global.value(storageKey)
            if (stored && String(stored).length > 0) {
                var raw = JSON.parse(String(stored))
                if (raw.browser) parsed.browser = raw.browser
                if (raw.apply_browser_theme !== undefined) parsed.apply_browser_theme = !!raw.apply_browser_theme
                if (raw.bundles && raw.bundles.length) parsed.bundles = raw.bundles
                if (raw.extra_packages !== undefined) parsed.extra_packages = raw.extra_packages
                if (raw.features) {
                    for (var key in parsed.features) {
                        if (raw.features[key] !== undefined) {
                            parsed.features[key] = !!raw.features[key]
                        }
                    }
                }
            }
        } catch (error) {
        }
        return parsed
    }

    function syncChoice() {
        Global.insert(storageKey, JSON.stringify(state))
    }

    function hasInternet() {
        return !!Global.value("hasInternet")
    }

    function bundleSelected(key) {
        return !!state.bundles && state.bundles.indexOf(key) !== -1
    }

    function toggleBundle(key) {
        var next = state.bundles.slice(0)
        var index = next.indexOf(key)
        if (index === -1) {
            next.push(key)
        } else {
            next.splice(index, 1)
        }
        state.bundles = next
        syncChoice()
    }

    function featureEnabled(key) {
        return !!state.features && !!state.features[key]
    }

    function setFeature(key, enabled) {
        state.features[key] = enabled
        if (key === "browser_startpage") {
            state.apply_browser_theme = enabled
        }
        syncChoice()
    }

    function browserLabel(browserKey) {
        for (var i = 0; i < browserOptions.length; ++i) {
            if (browserOptions[i].key === browserKey) {
                return browserOptions[i].label
            }
        }
        return "LibreWolf"
    }

    function selectedBundleLabels() {
        var labels = []
        for (var i = 0; i < bundleOptions.length; ++i) {
            if (bundleSelected(bundleOptions[i].key)) {
                labels.push(bundleOptions[i].label)
            }
        }
        return labels
    }

    function extraPackageList() {
        if (!state.extra_packages || state.extra_packages.trim().length === 0) {
            return []
        }
        return state.extra_packages.trim().split(/[\s,]+/).filter(function(item) { return item.length > 0 })
    }

    function enabledFeatureLabels() {
        var labels = []
        for (var i = 0; i < featureOptions.length; ++i) {
            if (featureEnabled(featureOptions[i].key)) {
                labels.push(featureOptions[i].label)
            }
        }
        return labels
    }

    Component.onCompleted: {
        state = parseState()
        syncChoice()
    }

    Rectangle {
        anchors.fill: parent
        color: bg
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: borderColor
        border.width: 1
    }

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight + 48
        clip: true

        ColumnLayout {
            id: contentColumn
            width: parent.width - 36
            x: 18
            y: 18
            spacing: 14

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 92
                color: panel
                border.color: borderColor
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 20

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Text {
                            text: "SOFTWARE LOADOUT"
                            color: accent
                            font.family: "JetBrains Mono"
                            font.pixelSize: 28
                            font.bold: true
                        }

                        Text {
                            text: "Select browser, package bundles, custom packages, and feature flags before deployment."
                            color: textColor
                            font.family: "JetBrains Mono"
                            font.pixelSize: 14
                            wrapMode: Text.WordWrap
                        }
                    }

                    Rectangle {
                        Layout.preferredWidth: 260
                        Layout.fillHeight: true
                        color: block
                        border.color: borderColor
                        border.width: 1

                        Column {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 6

                            Text {
                                text: "NETWORK LINK"
                                color: dimText
                                font.family: "JetBrains Mono"
                                font.pixelSize: 12
                            }

                            Text {
                                text: hasInternet() ? "ONLINE" : "OFFLINE"
                                color: hasInternet() ? accent : "#ff8a57"
                                font.family: "JetBrains Mono"
                                font.pixelSize: 20
                                font.bold: true
                            }

                            Text {
                                text: hasInternet()
                                    ? "Package validation and optional installs are available."
                                    : "Optional package installs may be skipped. You can still continue with a base install."
                                color: textColor
                                font.family: "JetBrains Mono"
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                                width: parent.width
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                spacing: 14

                Rectangle {
                    Layout.preferredWidth: 230
                    Layout.fillHeight: true
                    color: panel
                    border.color: borderColor
                    border.width: 1

                    Column {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 10

                        Repeater {
                            model: [
                                "DEFAULT BROWSER",
                                "BROWSER THEME",
                                "PACKAGE BUNDLES",
                                "CUSTOM PACKAGES",
                                "FEATURE FLAGS",
                                "QUEUE SUMMARY"
                            ]

                            delegate: Rectangle {
                                width: parent ? parent.width : 180
                                height: 38
                                color: index === 0 ? Qt.rgba(0.8078, 0.4157, 0.2078, 0.16) : block
                                border.color: borderColor
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: (index + 1 < 10 ? "0" + (index + 1) : index + 1) + " " + modelData
                                    color: textColor
                                    font.family: "JetBrains Mono"
                                    font.pixelSize: 12
                                    font.bold: index === 0
                                }
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 14

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 250
                        color: panel
                        border.color: borderColor
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12

                            Text {
                                text: "DEFAULT BROWSER"
                                color: accent
                                font.family: "JetBrains Mono"
                                font.pixelSize: 18
                                font.bold: true
                            }

                            Text {
                                text: "Choose your default browser. LibreWolf is preselected as the recommended KeskOS fit."
                                color: textColor
                                font.family: "JetBrains Mono"
                                font.pixelSize: 13
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12

                                Repeater {
                                    model: browserOptions

                                    delegate: Rectangle {
                                        Layout.fillWidth: true
                                        implicitHeight: 138
                                        color: state.browser === modelData.key ? Qt.rgba(0.8078, 0.4157, 0.2078, 0.16) : block
                                        border.color: state.browser === modelData.key ? accent : Qt.rgba(0.8078, 0.4157, 0.2078, 0.45)
                                        border.width: 1

                                        MouseArea {
                                            anchors.fill: parent
                                            onClicked: {
                                                state.browser = modelData.key
                                                syncChoice()
                                            }
                                        }

                                        Column {
                                            anchors.fill: parent
                                            anchors.margins: 14
                                            spacing: 8

                                            Text {
                                                text: modelData.label
                                                color: accent
                                                font.family: "JetBrains Mono"
                                                font.pixelSize: 17
                                                font.bold: true
                                            }

                                            Text {
                                                text: modelData.tagline
                                                color: textColor
                                                font.family: "JetBrains Mono"
                                                font.pixelSize: 12
                                                wrapMode: Text.WordWrap
                                                width: parent.width
                                            }

                                            Text {
                                                text: modelData.note
                                                color: dimText
                                                font.family: "JetBrains Mono"
                                                font.pixelSize: 11
                                                wrapMode: Text.WordWrap
                                                width: parent.width
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 86
                        color: panel
                        border.color: borderColor
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 14

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4

                                Text {
                                    text: "BROWSER THEME / STARTPAGE"
                                    color: accent
                                    font.family: "JetBrains Mono"
                                    font.pixelSize: 18
                                    font.bold: true
                                }

                                Text {
                                    text: "Apply the local KeskOS browser startpage and best-effort browser styling."
                                    color: textColor
                                    font.family: "JetBrains Mono"
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }

                            Rectangle {
                                Layout.preferredWidth: 128
                                Layout.preferredHeight: 40
                                color: state.apply_browser_theme ? Qt.rgba(0.8078, 0.4157, 0.2078, 0.16) : block
                                border.color: accent
                                border.width: 1

                                Row {
                                    anchors.centerIn: parent
                                    spacing: 8

                                    Text {
                                        text: state.apply_browser_theme ? "ON" : "OFF"
                                        color: state.apply_browser_theme ? accent : dimText
                                        font.family: "JetBrains Mono"
                                        font.pixelSize: 11
                                        font.bold: true
                                    }

                                    Text {
                                        text: state.apply_browser_theme ? "ENABLED" : "DISABLED"
                                        color: textColor
                                        font.family: "JetBrains Mono"
                                        font.pixelSize: 13
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        state.apply_browser_theme = !state.apply_browser_theme
                                        state.features.browser_startpage = state.apply_browser_theme
                                        syncChoice()
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 290
                        color: panel
                        border.color: borderColor
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12

                            Text {
                                text: "PACKAGE BUNDLES"
                                color: accent
                                font.family: "JetBrains Mono"
                                font.pixelSize: 18
                                font.bold: true
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: 2
                                rowSpacing: 10
                                columnSpacing: 10

                                Repeater {
                                    model: bundleOptions

                                    delegate: Rectangle {
                                        Layout.fillWidth: true
                                        implicitHeight: 86
                                        color: bundleSelected(modelData.key) ? Qt.rgba(0.8078, 0.4157, 0.2078, 0.16) : block
                                        border.color: bundleSelected(modelData.key) ? accent : Qt.rgba(0.8078, 0.4157, 0.2078, 0.45)
                                        border.width: 1

                                        MouseArea {
                                            anchors.fill: parent
                                            onClicked: toggleBundle(modelData.key)
                                        }

                                        Column {
                                            anchors.fill: parent
                                            anchors.margins: 12
                                            spacing: 6

                                            Text {
                                                text: modelData.label
                                                color: accent
                                                font.family: "JetBrains Mono"
                                                font.pixelSize: 15
                                                font.bold: true
                                            }

                                            Text {
                                                text: modelData.packages
                                                color: textColor
                                                font.family: "JetBrains Mono"
                                                font.pixelSize: 11
                                                wrapMode: Text.WordWrap
                                                width: parent.width
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 126
                        color: panel
                        border.color: borderColor
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 10

                            Text {
                                text: "CUSTOM PACKAGES"
                                color: accent
                                font.family: "JetBrains Mono"
                                font.pixelSize: 18
                                font.bold: true
                            }

                            Text {
                                text: "Search UI is not wired in this Calamares pass, so use a direct pacman package list here. Separate names with spaces or commas."
                                color: textColor
                                font.family: "JetBrains Mono"
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 44
                                color: block
                                border.color: borderColor
                                border.width: 1

                                TextInput {
                                    id: extraPackagesField
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    clip: true
                                    text: state.extra_packages
                                    color: textColor
                                    font.family: "JetBrains Mono"
                                    font.pixelSize: 13
                                    selectionColor: accent
                                    selectedTextColor: bg

                                    onTextChanged: {
                                        state.extra_packages = text
                                        syncChoice()
                                    }
                                }

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.left: parent.left
                                    anchors.leftMargin: 12
                                    text: "steam vesktop btop..."
                                    visible: extraPackagesField.text.length === 0
                                    color: dimText
                                    font.family: "JetBrains Mono"
                                    font.pixelSize: 13
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 280
                        color: panel
                        border.color: borderColor
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 10

                            Text {
                                text: "FEATURE FLAGS"
                                color: accent
                                font.family: "JetBrains Mono"
                                font.pixelSize: 18
                                font.bold: true
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: 2
                                rowSpacing: 8
                                columnSpacing: 8

                                Repeater {
                                    model: featureOptions

                                    delegate: Rectangle {
                                        Layout.fillWidth: true
                                        implicitHeight: 44
                                        color: featureEnabled(modelData.key) ? Qt.rgba(0.8078, 0.4157, 0.2078, 0.16) : block
                                        border.color: featureEnabled(modelData.key) ? accent : Qt.rgba(0.8078, 0.4157, 0.2078, 0.45)
                                        border.width: 1

                                        Row {
                                            anchors.fill: parent
                                            anchors.margins: 10
                                            spacing: 10

                                            Rectangle {
                                                width: 42
                                                height: parent.height - 4
                                                color: featureEnabled(modelData.key) ? Qt.rgba(0.8078, 0.4157, 0.2078, 0.2) : "#0a0908"
                                                border.color: accent
                                                border.width: 1

                                                Text {
                                                    anchors.centerIn: parent
                                                    text: featureEnabled(modelData.key) ? "ON" : "OFF"
                                                    color: featureEnabled(modelData.key) ? accent : dimText
                                                    font.family: "JetBrains Mono"
                                                    font.pixelSize: 10
                                                    font.bold: true
                                                }
                                            }

                                            Text {
                                                width: parent.width - 62
                                                text: modelData.label
                                                color: textColor
                                                font.family: "JetBrains Mono"
                                                font.pixelSize: 12
                                                wrapMode: Text.WordWrap
                                            }
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            onClicked: setFeature(modelData.key, !featureEnabled(modelData.key))
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 280
                    Layout.fillHeight: true
                    color: panel
                    border.color: borderColor
                    border.width: 1

                    Column {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12

                        Text {
                            text: "QUEUE SUMMARY"
                            color: accent
                            font.family: "JetBrains Mono"
                            font.pixelSize: 18
                            font.bold: true
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Qt.rgba(0.8078, 0.4157, 0.2078, 0.45)
                        }

                        Text {
                            width: parent.width
                            text: "[ OK ] Browser: " + browserLabel(state.browser)
                            color: textColor
                            font.family: "JetBrains Mono"
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            width: parent.width
                            text: "[ OK ] Theme / Startpage: " + (state.apply_browser_theme ? "enabled" : "disabled")
                            color: textColor
                            font.family: "JetBrains Mono"
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            width: parent.width
                            text: "[ OK ] Bundles: " + (selectedBundleLabels().length ? selectedBundleLabels().join(", ") : "none")
                            color: textColor
                            font.family: "JetBrains Mono"
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            width: parent.width
                            text: "[ OK ] Extra packages: " + extraPackageList().length
                            color: textColor
                            font.family: "JetBrains Mono"
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            width: parent.width
                            text: "[ OK ] Features: " + enabledFeatureLabels().length + " enabled"
                            color: textColor
                            font.family: "JetBrains Mono"
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Qt.rgba(0.8078, 0.4157, 0.2078, 0.45)
                        }

                        Text {
                            width: parent.width
                            text: "Additional packages are validated during deployment. Unavailable optional packages are skipped instead of breaking the full install."
                            color: dimText
                            font.family: "JetBrains Mono"
                            font.pixelSize: 11
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
    }
}
