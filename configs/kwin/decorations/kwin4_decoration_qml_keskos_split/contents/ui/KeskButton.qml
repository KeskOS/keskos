import QtQuick
import org.kde.kwin.decoration

DecorationButton {
    id: button

    property color accentActive: "#ce6a35"
    property color accentInactive: "#845236"
    property color fillIdle: "#0d0b09"
    property color fillHover: "#1a120d"
    property color fillPressed: "#24160f"
    property color textIdle: decoration.client.active ? accentActive : accentInactive
    readonly property bool isMinimize: button.buttonType === DecorationOptions.DecorationButtonMinimize
    readonly property bool isMaximizeRestore: button.buttonType === DecorationOptions.DecorationButtonMaximizeRestore
    readonly property bool isClose: button.buttonType === DecorationOptions.DecorationButtonClose

    width: 26
    height: 26
    implicitWidth: width
    implicitHeight: height

    Rectangle {
        anchors.fill: parent
        color: button.pressed ? button.fillPressed : (button.hovered ? button.fillHover : button.fillIdle)
        border.width: 1
        border.color: button.textIdle
        antialiasing: false
    }

    Item {
        anchors.centerIn: parent
        width: 12
        height: 12

        Rectangle {
            visible: button.isMinimize
            x: 1
            y: 8
            width: 10
            height: 1
            color: button.textIdle
            antialiasing: false
        }

        Rectangle {
            visible: button.isMaximizeRestore && !decoration.client.maximized
            x: 1
            y: 2
            width: 9
            height: 7
            color: "transparent"
            border.width: 1
            border.color: button.textIdle
            antialiasing: false
        }

        Item {
            visible: button.isMaximizeRestore && decoration.client.maximized
            anchors.fill: parent

            Rectangle {
                x: 1
                y: 3
                width: 7
                height: 6
                color: "transparent"
                border.width: 1
                border.color: button.textIdle
                antialiasing: false
            }

            Rectangle {
                x: 4
                y: 1
                width: 7
                height: 6
                color: "transparent"
                border.width: 1
                border.color: button.textIdle
                antialiasing: false
            }

        }

        Item {
            visible: button.isClose
            anchors.fill: parent

            Rectangle {
                x: 1
                y: 6
                width: 10
                height: 1
                color: button.textIdle
                rotation: 45
                transformOrigin: Item.Center
                antialiasing: false
            }

            Rectangle {
                x: 1
                y: 6
                width: 10
                height: 1
                color: button.textIdle
                rotation: -45
                transformOrigin: Item.Center
                antialiasing: false
            }

        }

    }

}
