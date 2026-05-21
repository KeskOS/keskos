import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kcmutils as KCMUtils
import org.kde.kirigami as Kirigami

KCMUtils.ScrollViewKCM {
    id: root

    implicitWidth: Kirigami.Units.gridUnit * 36
    implicitHeight: Kirigami.Units.gridUnit * 30

    property var launcherOptions: [
        "Meta",
        "Meta+Q",
        "Meta+Space"
    ]

    ColumnLayout {
        width: root.availableWidth
        spacing: Kirigami.Units.largeSpacing

        QQC2.Label {
            Layout.fillWidth: true
            text: qsTr("Control the KeskOS KDE launcher and panel behavior.")
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
                text: qsTr("Support: Limited")
                font.bold: true
            }
        }

        QQC2.Label {
            Layout.fillWidth: true
            text: qsTr("KeskOS currently uses the KDE launcher. Other launcher backends are not available yet.")
            wrapMode: Text.Wrap
            opacity: 0.8
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

            GridLayout {
                width: parent.width
                columns: 2
                columnSpacing: Kirigami.Units.largeSpacing
                rowSpacing: Kirigami.Units.smallSpacing

                QQC2.Label {
                    text: qsTr("Launcher backend")
                }

                QQC2.ComboBox {
                    Layout.fillWidth: true
                    model: [qsTr("KDE Launcher")]
                    enabled: false
                }

                QQC2.Label {
                    text: qsTr("Launcher shortcut")
                }

                QQC2.ComboBox {
                    id: shortcutCombo
                    Layout.fillWidth: true
                    model: root.launcherOptions
                    currentIndex: Math.max(0, root.launcherOptions.indexOf(kcm.currentLauncherShortcut))
                    onActivated: kcm.setLauncherShortcut(root.launcherOptions[currentIndex])
                }

                QQC2.Label {
                    text: qsTr("Launcher enabled")
                }

                QQC2.Switch {
                    checked: true
                    enabled: false
                }

                QQC2.Label {
                    text: qsTr("Bottom panel auto-hide")
                }

                QQC2.Switch {
                    enabled: false
                }

                QQC2.Label {
                    text: qsTr("Workspace switcher")
                }

                QQC2.Switch {
                    enabled: false
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            QQC2.Button {
                text: qsTr("Reset KDE launcher layout")
                enabled: !kcm.busy
                onClicked: kcm.resetLauncherLayout()
            }

            QQC2.Button {
                text: qsTr("Reapply KeskOS KDE panel layout")
                enabled: !kcm.busy
                onClicked: kcm.reapplyPanelLayout()
            }
        }
    }
}
