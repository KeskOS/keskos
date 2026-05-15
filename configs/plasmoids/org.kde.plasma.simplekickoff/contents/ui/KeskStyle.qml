import QtQuick 2.15

QtObject {
    readonly property color backgroundColor: "#050505"
    readonly property color panelColor: "#080706"
    readonly property color panelAltColor: "#11100e"
    readonly property color accentColor: "#ce6a35"
    readonly property color accentBrightColor: Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.90)
    readonly property color accentSoftColor: Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.35)
    readonly property color accentDimColor: Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.16)
    readonly property color hoverFillColor: Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.16)
    readonly property color selectedFillColor: Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.24)
    readonly property color textColor: "#c2b8ad"
    readonly property color textMutedColor: "#8d8174"
    readonly property color borderColor: Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.55)
    readonly property color innerBorderColor: Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.22)
    readonly property color glowColor: Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.14)
    readonly property color scanlineColor: Qt.rgba(1, 1, 1, 0.018)
    readonly property string displayFontFamily: "VT323"
    readonly property string uiFontFamily: "JetBrains Mono"
    readonly property int searchCornerRadius: 2
    readonly property int panelCornerRadius: 2
}
