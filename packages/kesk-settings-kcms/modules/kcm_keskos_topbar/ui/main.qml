import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kcmutils as KCMUtils
import org.kde.kirigami as Kirigami

KCMUtils.ScrollViewKCM {
    id: root

    implicitWidth: Kirigami.Units.gridUnit * 36
    implicitHeight: Kirigami.Units.gridUnit * 30

    ColumnLayout {
        width: root.availableWidth
        spacing: Kirigami.Units.largeSpacing

        QQC2.Label {
            Layout.fillWidth: true
            text: qsTr("Control the KeskOS top bar widgets.")
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
            text: qsTr("These controls require the current KeskOS top bar widget backend to be connected.")
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

                QQC2.Label { text: qsTr("Backend status") }
                QQC2.Label {
                    text: kcm.backendConnected ? qsTr("Limited") : qsTr("Limited (backend not connected)")
                    opacity: 0.85
                }

                QQC2.Label { text: qsTr("Enable top bar widgets") }
                QQC2.Switch { enabled: false; checked: kcm.backendConnected }

                QQC2.Label { text: qsTr("Media widget") }
                QQC2.Switch { enabled: false; checked: true }

                QQC2.Label { text: qsTr("CPU widget") }
                QQC2.Switch { enabled: false; checked: true }

                QQC2.Label { text: qsTr("Memory widget") }
                QQC2.Switch { enabled: false; checked: true }

                QQC2.Label { text: qsTr("Network widget") }
                QQC2.Switch { enabled: false; checked: true }

                QQC2.Label { text: qsTr("Widget refresh rate") }
                QQC2.ComboBox {
                    Layout.fillWidth: true
                    enabled: false
                    model: [qsTr("Slow"), qsTr("Normal"), qsTr("Fast")]
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            QQC2.Button {
                text: qsTr("Reset top bar widgets")
                enabled: kcm.canReset && !kcm.busy
                onClicked: kcm.resetWidgets()
            }

            QQC2.Button {
                text: qsTr("Restart top bar widgets")
                enabled: kcm.canRestart && !kcm.busy
                onClicked: kcm.restartWidgets()
            }
        }
    }
}
