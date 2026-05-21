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

        QQC2.Label {
            Layout.fillWidth: true
            text: qsTr("KeskOS uses the real KDE System Settings shell and adds a small set of project-owned pages for docs, theming, and desktop-specific controls.")
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

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: kcm.statusMessage.length > 0
            text: kcm.statusMessage
            type: kcm.statusLevel === "error"
                ? Kirigami.MessageType.Error
                : kcm.statusLevel === "warning"
                    ? Kirigami.MessageType.Warning
                    : Kirigami.MessageType.Positive
        }

        QQC2.Frame {
            Layout.fillWidth: true

            ColumnLayout {
                width: parent.width
                spacing: Kirigami.Units.largeSpacing

                QQC2.Label {
                    Layout.fillWidth: true
                    text: qsTr("Official KeskOS links")
                    font.bold: true
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: Kirigami.Units.largeSpacing
                    rowSpacing: Kirigami.Units.smallSpacing

                    QQC2.Button {
                        text: qsTr("Website")
                        onClicked: kcm.openWebsite()
                    }

                    QQC2.Label {
                        Layout.fillWidth: true
                        text: "https://keskos.org"
                        wrapMode: Text.WrapAnywhere
                    }

                    QQC2.Button {
                        text: qsTr("Docs")
                        onClicked: kcm.openDocs()
                    }

                    QQC2.Label {
                        Layout.fillWidth: true
                        text: "https://docs.keskos.org"
                        wrapMode: Text.WrapAnywhere
                    }

                    QQC2.Button {
                        text: qsTr("GitHub")
                        onClicked: kcm.openGitHub()
                    }

                    QQC2.Label {
                        Layout.fillWidth: true
                        text: "https://github.com/memegeko/keskos"
                        wrapMode: Text.WrapAnywhere
                    }
                }
            }
        }
    }
}
