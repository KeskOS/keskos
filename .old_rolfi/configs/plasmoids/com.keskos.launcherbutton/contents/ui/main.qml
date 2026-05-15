import QtQuick
import QtQuick.Layouts
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.plasma.plasmoid

PlasmoidItem {
    id: root

    readonly property color accent: "#ce6a35"
    readonly property color base: "#080706"
    readonly property color hoverBase: "#15100d"
    readonly property color pressedBase: "#1f120d"
    readonly property string defaultCommand: "bash -lc 'if [ -x \"$HOME/.local/bin/keskos-toggle-wolfi\" ]; then exec \"$HOME/.local/bin/keskos-toggle-wolfi\"; elif [ -x /usr/bin/keskos-toggle-wolfi ]; then exec /usr/bin/keskos-toggle-wolfi; elif [ -x /usr/local/bin/keskos-toggle-wolfi ]; then exec /usr/local/bin/keskos-toggle-wolfi; elif [ -x \"$HOME/.local/bin/keskos-launcher\" ]; then exec \"$HOME/.local/bin/keskos-launcher\" --mode main; elif [ -x /usr/local/bin/keskos-launcher ]; then exec /usr/local/bin/keskos-launcher --mode main; elif [ -x /usr/bin/keskos-launcher ]; then exec /usr/bin/keskos-launcher --mode main; else exit 1; fi'"
    readonly property string buttonCommand: plasmoid.configuration.command || defaultCommand
    readonly property url logoSource: Qt.resolvedUrl("../assets/kesk-logo.png")

    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    Layout.minimumWidth: 82
    Layout.preferredWidth: 82
    Layout.minimumHeight: 46
    Layout.fillHeight: true

    implicitWidth: 82
    implicitHeight: 46

    function launch() {
        commandRunner.exec(buttonCommand)
    }

    Plasma5Support.DataSource {
        id: commandRunner
        engine: "executable"
        connectedSources: []

        function exec(command) {
            connectSource(command)
        }

        onNewData: function(sourceName, data) {
            disconnectSource(sourceName)
        }
    }

    Rectangle {
        anchors.fill: parent
        color: buttonMouse.pressed ? root.pressedBase : (buttonMouse.containsMouse ? root.hoverBase : root.base)
        border.width: 1
        border.color: root.accent
    }

    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: "#35ce6a35"
    }

    Rectangle {
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        width: 1
        color: root.accent
    }

    Image {
        anchors.centerIn: parent
        source: root.logoSource
        width: 26
        height: 26
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
        sourceSize.width: 52
        sourceSize.height: 52
    }

    MouseArea {
        id: buttonMouse
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.launch()
    }
}
