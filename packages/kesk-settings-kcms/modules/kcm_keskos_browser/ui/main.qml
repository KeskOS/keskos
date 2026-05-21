import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kcmutils as KCMUtils
import org.kde.kirigami as Kirigami

KCMUtils.ScrollViewKCM {
    id: root

    implicitWidth: Kirigami.Units.gridUnit * 36
    implicitHeight: Kirigami.Units.gridUnit * 30

    property var browserOptions: [
        { key: "librewolf", label: "LibreWolf" },
        { key: "brave", label: "Brave" },
        { key: "zen", label: "Zen Browser" },
        { key: "firefox", label: "Firefox" }
    ]
    property bool applyHomepage: true

    ColumnLayout {
        width: root.availableWidth
        spacing: Kirigami.Units.largeSpacing

        QQC2.Label {
            Layout.fillWidth: true
            text: qsTr("Choose the default browser and apply KeskOS browser settings.")
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

                QQC2.Label { text: qsTr("Preferred browser") }

                QQC2.ComboBox {
                    id: browserCombo
                    Layout.fillWidth: true
                    model: root.browserOptions
                    textRole: "label"

                    Component.onCompleted: {
                        const idx = root.browserOptions.findIndex(option => option.key === kcm.selectedBrowser)
                        currentIndex = idx >= 0 ? idx : 0
                    }

                    onActivated: {
                        kcm.selectedBrowser = root.browserOptions[currentIndex].key
                    }
                }

                QQC2.Label { text: qsTr("Status") }
                QQC2.Label {
                    Layout.fillWidth: true
                    text: kcm.selectedStatusText + (kcm.packageName.length > 0 ? " (" + kcm.packageName + ")" : "")
                    wrapMode: Text.Wrap
                }

                QQC2.Label { text: qsTr("Current default") }
                QQC2.Label {
                    Layout.fillWidth: true
                    text: kcm.currentDefaultLabel
                    wrapMode: Text.Wrap
                }

                QQC2.Label { text: qsTr("Apply KeskOS homepage") }
                QQC2.Switch {
                    checked: root.applyHomepage
                    onToggled: root.applyHomepage = checked
                }
            }
        }

        QQC2.Label {
            Layout.fillWidth: true
            visible: !kcm.homepageAssetsAvailable
            text: qsTr("KeskOS homepage assets are missing, so browser theme application is disabled.")
            wrapMode: Text.Wrap
            opacity: 0.8
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            QQC2.Button {
                text: qsTr("Set as default browser")
                enabled: kcm.selectedInstalled && !kcm.busy
                onClicked: kcm.setDefaultBrowser()
            }

            QQC2.Button {
                text: qsTr("Install selected browser")
                enabled: kcm.selectedAvailable && !kcm.selectedInstalled && !kcm.busy
                onClicked: installDialog.open()
            }

            QQC2.Button {
                text: qsTr("Apply KeskOS browser theme")
                enabled: kcm.selectedInstalled && kcm.homepageAssetsAvailable && !kcm.busy
                onClicked: kcm.applyTheme(root.applyHomepage)
            }

            QQC2.Button {
                text: qsTr("Reset browser defaults")
                enabled: kcm.selectedInstalled && !kcm.busy
                onClicked: kcm.resetBrowserDefaults()
            }

            QQC2.Button {
                text: qsTr("Open browser homepage settings")
                enabled: kcm.canOpenHomepageSettings && !kcm.busy
                onClicked: kcm.openHomepageSettings()
            }
        }

        QQC2.Dialog {
            id: installDialog
            title: qsTr("Install browser")
            modal: true
            standardButtons: QQC2.Dialog.Ok | QQC2.Dialog.Cancel

            contentItem: QQC2.Label {
                text: qsTr("Install %1 now? This requires admin access.").arg(kcm.selectedBrowserLabel)
                wrapMode: Text.Wrap
            }

            onAccepted: kcm.installSelectedBrowser()
        }
    }
}
