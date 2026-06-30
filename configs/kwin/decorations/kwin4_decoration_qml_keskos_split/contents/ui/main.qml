import QtQuick
import org.kde.kwin.decoration

Decoration {
    id: root

    property int sideBorder: 7
    property int titlebarHeight: 38
    property int frameLine: 1
    property int leftPadding: 12
    property int rightPadding: 10
    property int logoSize: 18
    property int buttonSize: 26
    property int buttonSpacing: 5
    property int cornerInset: 5
    property int cornerLength: 10
    property color activeAccent: "#ce6a35"
    property color inactiveAccent: "#6e4128"
    property color activeBg: "#050505"
    property color inactiveBg: "#040404"
    property color activeTitleBg: "#070707"
    property color inactiveTitleBg: "#050505"
    property color activeText: "#ce6a35"
    property color inactiveText: "#8f8a84"
    readonly property color accent: decoration.client.active ? activeAccent : inactiveAccent
    readonly property color chromeBg: decoration.client.active ? activeTitleBg : inactiveTitleBg
    readonly property color bodyBg: decoration.client.active ? activeBg : inactiveBg
    readonly property color captionColor: decoration.client.active ? activeText : inactiveText
    readonly property bool maximizedLike: decoration.client.maximized
    readonly property int titleContentY: Math.round((titlebarHeight - logoSize) / 2)

    function updateBorders() {
        borders.setBorders(sideBorder);
        borders.setTitle(titlebarHeight);
        maximizedBorders.setTitle(titlebarHeight);
    }

    alpha: false
    Component.onCompleted: {
        root.updateBorders();
    }

    Rectangle {
        id: frame

        anchors.fill: parent
        color: root.bodyBg
        border.width: root.frameLine
        border.color: root.accent
        antialiasing: false
    }

    Rectangle {
        id: titlebar

        x: root.frameLine
        y: root.frameLine
        width: Math.max(root.width - (root.frameLine * 2), 0)
        height: root.titlebarHeight - root.frameLine
        color: root.chromeBg
        antialiasing: false
    }

    Rectangle {
        id: titleSeparator

        x: root.frameLine
        y: root.titlebarHeight - root.frameLine
        width: Math.max(root.width - (root.frameLine * 2), 0)
        height: root.frameLine
        color: root.accent
        opacity: decoration.client.active ? 0.72 : 0.42
        antialiasing: false
    }

    // Deliberate bracket ticks: aligned to the same inset/length so corners read as one frame.
    Rectangle {
        x: root.cornerInset
        y: root.cornerInset
        width: root.cornerLength
        height: root.frameLine
        color: root.accent
        opacity: 0.58
        antialiasing: false
    }

    Rectangle {
        x: root.cornerInset
        y: root.cornerInset
        width: root.frameLine
        height: root.cornerLength
        color: root.accent
        opacity: 0.58
        antialiasing: false
    }

    Rectangle {
        x: root.width - root.cornerInset - root.cornerLength
        y: root.cornerInset
        width: root.cornerLength
        height: root.frameLine
        color: root.accent
        opacity: 0.58
        antialiasing: false
    }

    Rectangle {
        x: root.width - root.cornerInset - root.frameLine
        y: root.cornerInset
        width: root.frameLine
        height: root.cornerLength
        color: root.accent
        opacity: 0.58
        antialiasing: false
    }

    Rectangle {
        x: root.cornerInset
        y: root.height - root.cornerInset - root.frameLine
        width: root.cornerLength
        height: root.frameLine
        color: root.accent
        opacity: 0.58
        antialiasing: false
    }

    Rectangle {
        x: root.cornerInset
        y: root.height - root.cornerInset - root.cornerLength
        width: root.frameLine
        height: root.cornerLength
        color: root.accent
        opacity: 0.58
        antialiasing: false
    }

    Rectangle {
        x: root.width - root.cornerInset - root.cornerLength
        y: root.height - root.cornerInset - root.frameLine
        width: root.cornerLength
        height: root.frameLine
        color: root.accent
        opacity: 0.58
        antialiasing: false
    }

    Rectangle {
        x: root.width - root.cornerInset - root.frameLine
        y: root.height - root.cornerInset - root.cornerLength
        width: root.frameLine
        height: root.cornerLength
        color: root.accent
        opacity: 0.58
        antialiasing: false
    }

    Image {
        id: logoMark

        x: root.leftPadding
        y: root.titleContentY
        width: root.logoSize
        height: root.logoSize
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
        source: "../assets/kesk_os_logo-removebg.png"
    }

    Item {
        id: buttonRow

        width: buttonControls.implicitWidth
        height: root.buttonSize

        anchors {
            right: parent.right
            rightMargin: root.rightPadding
            verticalCenter: titlebar.verticalCenter
        }

        Row {
            id: buttonControls

            anchors.centerIn: parent
            spacing: root.buttonSpacing

            KeskButton {
                buttonType: DecorationOptions.DecorationButtonMinimize
            }

            KeskButton {
                buttonType: DecorationOptions.DecorationButtonMaximizeRestore
            }

            KeskButton {
                buttonType: DecorationOptions.DecorationButtonClose
            }

        }

    }

    Item {
        id: titleArea

        x: logoMark.x + logoMark.width + 8
        y: root.frameLine
        width: Math.max(buttonRow.x - x - 12, 0)
        height: root.titlebarHeight - root.frameLine
        Component.onCompleted: {
            decoration.installTitleItem(titleArea);
        }

        Text {
            text: decoration.client.caption
            color: root.captionColor
            font.family: "JetBrainsMono Nerd Font"
            font.pixelSize: 15
            font.weight: Font.DemiBold
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            renderType: Text.NativeRendering

            anchors {
                left: parent.left
                right: parent.right
                verticalCenter: parent.verticalCenter
            }

        }

    }

    Connections {
        function onMaximizedChanged() {
            root.updateBorders();
        }

        target: decoration.client
    }

}
