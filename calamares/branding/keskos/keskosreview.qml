import io.calamares.core 1.0

import QtQuick 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    width: parent ? parent.width : 1180
    height: parent ? parent.height : 720

    readonly property color bg: "#050505"
    readonly property color panel: "#080706"
    readonly property color block: "#11100e"
    readonly property color accent: "#ce6a35"
    readonly property color textColor: "#b8afa6"
    readonly property color dimText: "#8f8a84"
    readonly property color borderColor: "#ce6a35"

    function internetState() {
        var value = Global.value("hasInternet")
        if (value === true || value === 1 || String(value).toLowerCase() === "true") {
            return "online"
        }
        if (value === false || value === 0 || String(value).toLowerCase() === "false") {
            return "offline"
        }
        return "unknown"
    }

    function networkBannerText() {
        var state = internetState()
        if (state === "online") {
            return "[ OK ] NETWORK LINK: ONLINE"
        }
        if (state === "offline") {
            return "[ WARN ] NETWORK LINK: OFFLINE"
        }
        return "[ INFO ] NETWORK LINK: OPTIONAL DURING INSTALL"
    }

    function networkBannerColor() {
        var state = internetState()
        if (state === "online") {
            return accent
        }
        if (state === "offline") {
            return "#ff8a57"
        }
        return textColor
    }

    Rectangle {
        anchors.fill: parent
        color: bg
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: borderColor
        border.width: 1
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 14

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 112
            color: panel
            border.color: borderColor
            border.width: 1

            Column {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 6

                Text {
                    text: "DEPLOY REVIEW"
                    color: accent
                    font.family: "JetBrains Mono"
                    font.pixelSize: 30
                    font.bold: true
                }

                Text {
                    text: "Review the core KeskOS deployment profile below. Continue to start installation."
                    color: textColor
                    font.family: "JetBrains Mono"
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                }

                Text {
                    text: networkBannerText()
                    color: networkBannerColor()
                    font.family: "JetBrains Mono"
                    font.pixelSize: 14
                    font.bold: true
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 14

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: panel
                border.color: borderColor
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    Text {
                        text: "[ INSTALL PROFILE ]"
                        color: accent
                        font.family: "JetBrains Mono"
                        font.pixelSize: 18
                        font.bold: true
                    }

                    Text {
                        width: parent.width
                        text: "[ OK ] Core deployment: base system + KDE Plasma desktop"
                        color: textColor
                        font.family: "JetBrains Mono"
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        width: parent.width
                        text: "[ OK ] Branding defaults: KeskOS theme, KDE layout, and login theme apply automatically"
                        color: textColor
                        font.family: "JetBrains Mono"
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        width: parent.width
                        text: "[ OK ] Required desktop packages: installed during deployment without extra personalization pages"
                        color: textColor
                        font.family: "JetBrains Mono"
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        width: parent.width
                        text: "[ OK ] First-boot handoff: Kesk Welcome autostart remains enabled for after-login setup"
                        color: textColor
                        font.family: "JetBrains Mono"
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        width: parent.width
                        text: "[ INFO ] Browser selection, widgets, optional apps, and theme checks now continue in Kesk Welcome"
                        color: textColor
                        font.family: "JetBrains Mono"
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }
                }
            }

            Rectangle {
                Layout.preferredWidth: 340
                Layout.fillHeight: true
                color: panel
                border.color: borderColor
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    Text {
                        text: "[ DEPLOY NOTES ]"
                        color: accent
                        font.family: "JetBrains Mono"
                        font.pixelSize: 18
                        font.bold: true
                    }

                    Text {
                        width: parent.width
                        text: "First-boot personalization will continue in Kesk Welcome after login."
                        color: textColor
                        font.family: "JetBrains Mono"
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        width: parent.width
                        text: "Calamares now handles deployment only: locale, keyboard, disk target, user profile, package install, and post-install defaults."
                        color: textColor
                        font.family: "JetBrains Mono"
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        width: parent.width
                        text: internetState() === "online"
                            ? "Repository validation is available in the live environment. Welcome can continue personalization after the first login."
                            : "Network is optional during Calamares. If the live session is offline, Welcome can finish browser and optional-app setup after the system has network access."
                        color: dimText
                        font.family: "JetBrains Mono"
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }
}
