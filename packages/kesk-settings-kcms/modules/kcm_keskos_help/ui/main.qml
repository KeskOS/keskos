import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kcmutils as KCMUtils
import org.kde.kirigami as Kirigami

KCMUtils.ScrollViewKCM {
    id: root

    implicitWidth: Kirigami.Units.gridUnit * 34
    implicitHeight: Kirigami.Units.gridUnit * 28

    ColumnLayout {
        width: root.availableWidth
        spacing: Kirigami.Units.largeSpacing

        Rectangle {
            color: "transparent"
            border.color: Kirigami.Theme.linkColor
            border.width: 1
            implicitHeight: badgeLabel.implicitHeight + Kirigami.Units.smallSpacing * 2
            implicitWidth: badgeLabel.implicitWidth + Kirigami.Units.largeSpacing

            QQC2.Label {
                id: badgeLabel
                anchors.centerIn: parent
                text: qsTr("Support: Native")
                font.bold: true
            }
        }

        QQC2.Label {
            Layout.fillWidth: true
            text: qsTr("Open the KeskOS documentation, install guides and troubleshooting pages.")
            wrapMode: Text.Wrap
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: kcm.statusMessage.length > 0
            text: kcm.statusMessage
            type: kcm.statusLevel === "error"
                ? Kirigami.MessageType.Error
                : Kirigami.MessageType.Positive
        }

        QQC2.Frame {
            Layout.fillWidth: true

            ColumnLayout {
                width: parent.width
                spacing: Kirigami.Units.largeSpacing

                QQC2.Button {
                    text: qsTr("Open KeskOS Docs")
                    onClicked: kcm.openDocs()
                }

                QQC2.Label {
                    text: "docs.keskos.org"
                    opacity: 0.8
                }
            }
        }
    }
}
