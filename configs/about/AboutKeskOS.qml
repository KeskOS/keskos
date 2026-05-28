import QtQuick
import QtQuick.Window

Window {
    id: root

    width: 480
    height: 440
    visible: true
    color: "#050505"
    title: "__KESKOS_WINDOW_TITLE__"

    Rectangle {
        anchors.fill: parent
        color: "#050505"
        border.width: 1
        border.color: "#ce6a35"
    }

    Item {
        anchors.fill: parent

        Repeater {
            model: Math.ceil(root.height / 4)

            Rectangle {
                x: 0
                y: index * 4
                width: root.width
                height: 1
                color: index % 2 === 0 ? "#090807" : "#070606"
                opacity: 0.28
            }
        }
    }

    Rectangle {
        x: 18
        y: 26
        width: root.width - 36
        height: 1
        color: "#ce6a35"
        opacity: 0.75
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 72
        text: "__KESKOS_NAME_SPACED__"
        color: "#ce6a35"
        font.family: "JetBrainsMono Nerd Font"
        font.pixelSize: 34
        font.letterSpacing: 3
        renderType: Text.NativeRendering
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 136
        text: "__KESKOS_LAYER_TITLE__"
        color: "#b8afa6"
        font.family: "JetBrainsMono Nerd Font"
        font.pixelSize: 17
        font.letterSpacing: 2
        renderType: Text.NativeRendering
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 170
        text: "__KESKOS_BRAND_LINE__"
        color: "#8f8a84"
        font.family: "JetBrainsMono Nerd Font"
        font.pixelSize: 15
        font.letterSpacing: 2
        renderType: Text.NativeRendering
    }

    Rectangle {
        x: 42
        y: 218
        width: root.width - 84
        height: 1
        color: "#ce6a35"
        opacity: 0.8
    }

    Column {
        x: 52
        y: 244
        spacing: 12

        Repeater {
            model: [
                "OS: __KESKOS_BRAND_LINE__",
                "LAYER: __KESKOS_LAYER_LINE__",
                "CHANNEL: __KESKOS_CHANNEL__",
                "BUILD: __KESKOS_BUILD_ID__",
                "ARCHITECTURE: __KESKOS_ARCH__",
                "KERNEL: __KESKOS_KERNEL__"
            ]

            Text {
                required property string modelData
                text: modelData
                color: "#b8afa6"
                font.family: "JetBrainsMono Nerd Font"
                font.pixelSize: 15
                font.letterSpacing: 1.2
                renderType: Text.NativeRendering
            }
        }
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        y: root.height - 52
        text: "\u00a9 __KESKOS_COPY_YEAR__ KESKOS"
        color: "#8f8a84"
        font.family: "JetBrainsMono Nerd Font"
        font.pixelSize: 13
        font.letterSpacing: 1.6
        renderType: Text.NativeRendering
    }
}
