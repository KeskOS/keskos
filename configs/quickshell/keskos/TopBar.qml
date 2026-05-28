import QtQuick

Item {
    id: root

    required property var theme
    required property var barData
    required property string activePopup

    signal popupToggleRequested(string popupName)

    property alias mediaAnchor: mediaChip
    property alias cpuAnchor: cpuChip
    property alias memoryAnchor: memoryChip
    property alias networkAnchor: networkChip
    property alias powerAnchor: powerButton

    Rectangle {
        anchors.fill: parent
        color: theme.panelBg
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: theme.accent
    }

    ScanlinesOverlay {
        anchors.fill: parent
    }

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 18
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8

        Text {
            text: "K E S K   O S"
            color: theme.accent
            font.family: "JetBrainsMono Nerd Font"
            font.pixelSize: 13
            font.letterSpacing: 1.8
            renderType: Text.NativeRendering
        }

        Text {
            text: "|"
            color: theme.accentSoft
            font.family: "JetBrainsMono Nerd Font"
            font.pixelSize: 13
            renderType: Text.NativeRendering
        }

        Repeater {
            model: ["FILE", "EDIT", "VIEW", "HELP"]

            HoverChip {
                required property string modelData
                label: modelData
                theme: root.theme
            }
        }
    }

    Text {
        anchors.centerIn: parent
        text: "KeskOS // SECURE TERMINAL"
        color: theme.accent
        font.family: "JetBrainsMono Nerd Font"
        font.pixelSize: 13
        font.letterSpacing: 1.5
        renderType: Text.NativeRendering
    }

    Row {
        anchors.right: parent.right
        anchors.rightMargin: 18
        anchors.verticalCenter: parent.verticalCenter
        spacing: 14

        StatusChip {
            id: mediaChip
            label: "MEDIA"
            theme: root.theme
            textColor: barData.media_active ? root.theme.accent : root.theme.text
            active: root.activePopup === "media"
            onPressed: root.popupToggleRequested("media")
        }

        StatusChip {
            id: cpuChip
            label: "CPU " + barData.cpu_percent + "%"
            theme: root.theme
            textColor: root.theme.text
            active: root.activePopup === "cpu"
            onPressed: root.popupToggleRequested("cpu")
        }

        StatusChip {
            id: memoryChip
            label: "MEM " + barData.mem_percent + "%"
            theme: root.theme
            textColor: root.theme.text
            active: root.activePopup === "memory"
            onPressed: root.popupToggleRequested("memory")
        }

        StatusChip {
            id: networkChip
            label: "NET " + barData.net_glyph
            theme: root.theme
            textColor: root.theme.accent
            active: root.activePopup === "network"
            onPressed: root.popupToggleRequested("network")
        }

        Text {
            text: barData.clock
            color: theme.text
            font.family: "JetBrainsMono Nerd Font"
            font.pixelSize: 12
            renderType: Text.NativeRendering
        }

        AppButton {
            id: powerButton
            width: 32
            height: 24
            iconSource: theme.assetRoot + "/power.svg"
            active: root.activePopup === "power"
            theme: root.theme
            onPressed: root.popupToggleRequested("power")
        }
    }
}
