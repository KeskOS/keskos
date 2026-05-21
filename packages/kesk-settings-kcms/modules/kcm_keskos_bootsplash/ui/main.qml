import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kcmutils as KCMUtils
import org.kde.kirigami as Kirigami

KCMUtils.ScrollViewKCM {
    id: root

    implicitWidth: Kirigami.Units.gridUnit * 36
    implicitHeight: Kirigami.Units.gridUnit * 28

    ColumnLayout {
        width: root.availableWidth
        spacing: Kirigami.Units.largeSpacing

        QQC2.Label {
            Layout.fillWidth: true
            text: qsTr("KeskOS boot splash support is under development. Plymouth is not integrated yet.")
            wrapMode: Text.Wrap
        }

        Rectangle {
            color: "transparent"
            border.color: Kirigami.Theme.linkColor
            border.width: 1
            implicitHeight: badgeLabel.implicitHeight + Kirigami.Units.smallSpacing * 2
            implicitWidth: badgeLabel.implicitWidth + Kirigami.Units.largeSpacing

            QQC2.Label {
                id: badgeLabel
                anchors.centerIn: parent
                text: qsTr("Support: Under Works")
                font.bold: true
            }
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

            GridLayout {
                width: parent.width
                columns: 2
                columnSpacing: Kirigami.Units.largeSpacing
                rowSpacing: Kirigami.Units.smallSpacing

                QQC2.Label { text: qsTr("Status") }
                QQC2.Label { text: qsTr("Under works") }

                QQC2.Label { text: qsTr("Plymouth installed") }
                QQC2.Label { text: kcm.plymouthInstalled ? qsTr("yes") : qsTr("no") }

                QQC2.Label { text: qsTr("KeskOS Plymouth theme installed") }
                QQC2.Label { text: kcm.themeInstalled ? qsTr("yes") : qsTr("no") }

                QQC2.Label { text: qsTr("Current boot splash") }
                QQC2.Label {
                    Layout.fillWidth: true
                    text: kcm.currentTheme
                    wrapMode: Text.Wrap
                }
            }
        }

        QQC2.Label {
            Layout.fillWidth: true
            text: qsTr("Boot Splash settings are not available yet because Plymouth support has not been added to KeskOS.")
            wrapMode: Text.Wrap
            opacity: 0.8
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            QQC2.Button {
                text: qsTr("Preview")
                enabled: false
            }

            QQC2.Button {
                text: qsTr("Apply boot splash")
                enabled: false
            }

            QQC2.Button {
                text: qsTr("Open boot splash docs")
                onClicked: kcm.openDocs()
            }
        }
    }
}
