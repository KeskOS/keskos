import QtQuick
import org.kde.kirigami as Kirigami

Item {
    id: root

    required property var items
    required property int currentIndex
    required property color accentColor
    required property color textColor
    required property color dimTextColor
    required property color hoverColor
    required property color selectedColor
    required property color borderColor
    property bool showSubtitle: true

    signal indexChangedByUser(int index)
    signal itemActivated(var item)

    function ensureVisible(index) {
        if (index < 0 || index >= listView.count) {
            return
        }
        listView.positionViewAtIndex(index, ListView.Contain)
    }

    ListView {
        id: listView
        anchors.fill: parent
        clip: true
        spacing: 2
        model: root.items || []
        currentIndex: root.currentIndex

        delegate: Rectangle {
            required property var modelData
            required property int index

            width: ListView.view.width
            height: root.showSubtitle ? 44 : 36
            color: mouseArea.containsMouse ? root.hoverColor : (root.currentIndex === index ? root.selectedColor : "transparent")
            border.width: root.currentIndex === index ? 1 : 0
            border.color: root.borderColor

            Row {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 8
                spacing: 8

                Kirigami.Icon {
                    width: 18
                    height: 18
                    anchors.verticalCenter: parent.verticalCenter
                    source: modelData.icon || "application-x-executable"
                    color: root.currentIndex === index ? root.accentColor : root.textColor
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 40
                    spacing: 1

                    Text {
                        width: parent.width
                        text: modelData.name || ""
                        color: root.currentIndex === index ? root.accentColor : root.textColor
                        font.family: "JetBrains Mono"
                        font.pixelSize: 17
                        elide: Text.ElideRight
                    }

                    Text {
                        visible: root.showSubtitle && !!(modelData.comment || modelData.genericName)
                        width: parent.width
                        text: modelData.comment || modelData.genericName || ""
                        color: root.dimTextColor
                        font.family: "JetBrains Mono"
                        font.pixelSize: 13
                        elide: Text.ElideRight
                    }
                }
            }

            MouseArea {
                id: mouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onEntered: root.indexChangedByUser(index)
                onClicked: {
                    root.indexChangedByUser(index)
                    root.itemActivated(modelData)
                }
            }
        }
    }
}
