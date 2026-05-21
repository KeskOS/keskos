import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kcmutils as KCMUtils
import org.kde.kirigami as Kirigami

KCMUtils.ScrollViewKCM {
    id: root

    implicitWidth: Kirigami.Units.gridUnit * 36
    implicitHeight: Kirigami.Units.gridUnit * 30

    property var modeOptions: [
        qsTr("KeskOS Orange"),
        qsTr("KDE Defaults")
    ]

    ColumnLayout {
        width: root.availableWidth
        spacing: Kirigami.Units.largeSpacing

        QQC2.Label {
            Layout.fillWidth: true
            text: qsTr("Control the KeskOS visual style. KeskOS currently uses the fixed orange accent color #ce6a35.")
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

            GridLayout {
                width: parent.width
                columns: 2
                columnSpacing: Kirigami.Units.largeSpacing
                rowSpacing: Kirigami.Units.smallSpacing

                QQC2.Label {
                    text: qsTr("Current accent color")
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Rectangle {
                        implicitWidth: Kirigami.Units.gridUnit * 2
                        implicitHeight: Kirigami.Units.gridUnit
                        color: "#ce6a35"
                        border.color: Kirigami.Theme.textColor
                        border.width: 1
                    }

                    QQC2.Label {
                        text: kcm.currentAccentColor
                    }
                }

                QQC2.Label {
                    text: qsTr("Theme mode")
                }

                QQC2.ComboBox {
                    id: modeCombo
                    Layout.fillWidth: true
                    model: root.modeOptions
                    currentIndex: kcm.currentMode === "KDE Defaults" ? 1 : 0
                }

                QQC2.Label {
                    text: qsTr("Accent colors")
                }

                QQC2.Label {
                    Layout.fillWidth: true
                    text: qsTr("Custom accent colors are not supported yet.")
                    wrapMode: Text.Wrap
                    opacity: 0.8
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            QQC2.Button {
                text: qsTr("Apply KeskOS Orange")
                enabled: !kcm.busy
                onClicked: kcm.applyKeskTheme()
            }

            QQC2.Button {
                text: qsTr("Switch to KDE Defaults")
                enabled: !kcm.busy
                onClicked: kcm.applyKdeDefaults()
            }

            QQC2.Button {
                text: qsTr("Reset KeskOS Theme")
                enabled: !kcm.busy
                onClicked: kcm.resetKeskTheme()
            }
        }
    }
}
