import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kcmutils as KCMUtils
import org.kde.kirigami as Kirigami

KCMUtils.ScrollViewKCM {
    id: root

    implicitWidth: Kirigami.Units.gridUnit * 36
    implicitHeight: Kirigami.Units.gridUnit * 32

    ColumnLayout {
        width: root.availableWidth
        spacing: Kirigami.Units.largeSpacing

        QQC2.Label {
            Layout.fillWidth: true
            text: qsTr("View KeskOS build and system version information.")
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
                text: qsTr("Support: Native")
                font.bold: true
            }
        }

        QQC2.Frame {
            Layout.fillWidth: true

            ColumnLayout {
                width: parent.width
                spacing: Kirigami.Units.smallSpacing

                Repeater {
                    model: kcm.infoEntries

                    delegate: RowLayout {
                        width: parent.width
                        spacing: Kirigami.Units.largeSpacing

                        QQC2.Label {
                            Layout.preferredWidth: root.availableWidth * 0.32
                            text: modelData.label
                            font.bold: true
                            wrapMode: Text.Wrap
                        }

                        QQC2.Label {
                            Layout.fillWidth: true
                            text: modelData.value
                            wrapMode: Text.Wrap
                            textFormat: Text.PlainText
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            QQC2.Button {
                text: qsTr("Website")
                onClicked: kcm.openWebsite()
            }

            QQC2.Button {
                text: qsTr("Docs")
                onClicked: kcm.openDocs()
            }

            QQC2.Button {
                text: qsTr("GitHub")
                onClicked: kcm.openGitHub()
            }
        }
    }
}
