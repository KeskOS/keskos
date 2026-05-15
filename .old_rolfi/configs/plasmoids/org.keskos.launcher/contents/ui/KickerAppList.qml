import QtQuick
import org.kde.kirigami as Kirigami

Item {
    id: root

    required property var itemsModel
    required property int currentIndex
    required property color accentColor
    required property color textColor
    required property color dimTextColor
    required property color hoverColor
    required property color selectedColor
    required property color borderColor

    signal indexChangedByUser(int index)
    signal itemActivated(int index)

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
        model: root.itemsModel
        currentIndex: root.currentIndex

        delegate: Rectangle {
            id: delegateRoot

            required property int index

            function modelIndex() {
                if (!root.itemsModel || !root.itemsModel.index) {
                    return null
                }

                try {
                    return root.itemsModel.index(index, 0)
                } catch (error) {
                    return null
                }
            }

            function dataFor(role, fallbackValue) {
                const idx = modelIndex()
                if (!idx || !root.itemsModel || !root.itemsModel.data) {
                    return fallbackValue
                }

                try {
                    const value = root.itemsModel.data(idx, role)
                    if (value !== undefined && value !== null && value !== "") {
                        return value
                    }
                } catch (error) {
                    // Ignore and fall through to fallback.
                }

                return fallbackValue
            }

            function modelProperty(name, fallbackValue) {
                if (typeof model !== "undefined" && model !== null && typeof model[name] !== "undefined" && model[name] !== null && model[name] !== "") {
                    return model[name]
                }
                return fallbackValue
            }

            readonly property string titleText: String(dataFor(Qt.DisplayRole, modelProperty("display", modelProperty("name", root.itemsModel && root.itemsModel.labelForRow ? root.itemsModel.labelForRow(index) : ""))))
            readonly property string subtitleText: String(modelProperty("description", modelProperty("subTitle", "")))
            readonly property var iconSource: dataFor(Qt.DecorationRole, modelProperty("decoration", "application-x-executable"))
            readonly property bool separatorItem: Boolean(modelProperty("separator", false))
            readonly property bool disabledItem: Boolean(modelProperty("disabled", false))

            width: ListView.view.width
            height: delegateRoot.separatorItem ? 8 : ((delegateRoot.subtitleText.length > 0) ? 44 : 36)
            color: hoverArea.containsMouse
                ? root.hoverColor
                : (root.currentIndex === index ? root.selectedColor : "transparent")
            border.width: (!delegateRoot.separatorItem && root.currentIndex === index) ? 1 : 0
            border.color: root.borderColor

            Rectangle {
                visible: delegateRoot.separatorItem
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: 6
                anchors.rightMargin: 6
                height: 1
                color: Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.3)
            }

            Row {
                visible: !delegateRoot.separatorItem
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 8
                spacing: 8

                Kirigami.Icon {
                    width: 18
                    height: 18
                    anchors.verticalCenter: parent.verticalCenter
                    source: delegateRoot.iconSource
                    color: root.currentIndex === index ? root.accentColor : root.textColor
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 40
                    spacing: 1

                    Text {
                        width: parent.width
                        text: delegateRoot.titleText
                        color: delegateRoot.disabledItem
                            ? root.dimTextColor
                            : (root.currentIndex === index ? root.accentColor : root.textColor)
                        font.family: "JetBrains Mono"
                        font.pixelSize: 17
                        elide: Text.ElideRight
                    }

                    Text {
                        visible: delegateRoot.subtitleText.length > 0
                        width: parent.width
                        text: delegateRoot.subtitleText
                        color: root.dimTextColor
                        font.family: "JetBrains Mono"
                        font.pixelSize: 13
                        elide: Text.ElideRight
                    }
                }
            }

            MouseArea {
                id: hoverArea
                anchors.fill: parent
                enabled: !delegateRoot.separatorItem && !delegateRoot.disabledItem
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onEntered: root.indexChangedByUser(index)
                onClicked: {
                    root.indexChangedByUser(index)
                    root.itemActivated(index)
                }
            }
        }
    }
}
