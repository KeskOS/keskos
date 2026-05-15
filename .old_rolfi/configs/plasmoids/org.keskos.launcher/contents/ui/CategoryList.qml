import QtQuick

Item {
    id: root

    required property var categories
    required property string activeCategory
    required property color accentColor
    required property color textColor
    required property color dimTextColor
    required property color hoverColor
    required property color selectedColor
    required property color borderColor

    signal categorySelected(string categoryKey)

    ListView {
        id: categoryView
        anchors.fill: parent
        clip: true
        spacing: 2
        model: root.categories

        delegate: Rectangle {
            required property var modelData

            width: ListView.view.width
            height: 32
            color: mouseArea.containsMouse ? root.hoverColor : "transparent"

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: root.activeCategory === modelData.key ? 2 : 0
                color: root.accentColor
            }

            Rectangle {
                anchors.fill: parent
                anchors.leftMargin: root.activeCategory === modelData.key ? 2 : 0
                color: root.activeCategory === modelData.key ? root.selectedColor : "transparent"
                border.width: root.activeCategory === modelData.key ? 1 : 0
                border.color: root.borderColor
            }

            Text {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 8
                verticalAlignment: Text.AlignVCenter
                text: (root.activeCategory === modelData.key ? "> " : "  ") + modelData.label.toUpperCase()
                color: root.activeCategory === modelData.key ? root.accentColor : root.dimTextColor
                font.family: "JetBrains Mono"
                font.pixelSize: 18
                elide: Text.ElideRight
            }

            MouseArea {
                id: mouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.categorySelected(modelData.key)
            }
        }
    }
}
