/*
 *   SPDX-FileCopyrightText: 2021 Jan Blackquill <uhhadd@gmail.com>
 *
 *   SPDX-License-Identifier: LGPL-2.0-only
 */
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ItemDelegate {
    id: delegate

    property bool showArrow: false
    property bool selected: delegate.highlighted
    property bool isSearching: false
    property real leadingPadding: 0
    readonly property color keskAccent: "#ce6a35"
    readonly property color outlineColor: selected ? keskAccent : (hovered && enabled ? Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.20) : "transparent")
    readonly property color fillColor: selected ? "#11100e" : (pressed ? Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.10) : (hovered && enabled ? Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.08) : "transparent"))
    readonly property color itemTextColor: selected ? "#e2d8cf" : (hovered && enabled ? "#d0c7bf" : "#b8afa6")
    readonly property color itemIconColor: selected ? keskAccent : (hovered && enabled ? "#d0c7bf" : "#8f8a84")
    required property bool showDefaultIndicator
    required property QtObject /*QAction*/ auxiliaryAction

    width: ListView.view?.width ?? 0
    implicitHeight: Math.max(Math.round(Kirigami.Units.gridUnit * 1.7), titleItem.implicitHeight + (Kirigami.Units.smallSpacing * 2))
    leftPadding: Kirigami.Units.smallSpacing * 2
    rightPadding: Kirigami.Units.smallSpacing * 2
    topPadding: Kirigami.Units.smallSpacing
    bottomPadding: Kirigami.Units.smallSpacing

    Accessible.name: text
    Accessible.onPressAction: clicked()

    background: Rectangle {
        anchors {
            left: parent.left
            right: parent.right
            verticalCenter: parent.verticalCenter
            leftMargin: Kirigami.Units.smallSpacing
            rightMargin: Kirigami.Units.smallSpacing
        }
        height: Math.max(parent.height - 2, 1)
        radius: delegate.selected || delegate.hovered ? 1 : 0
        color: delegate.fillColor
        border.width: delegate.selected || (delegate.hovered && delegate.enabled) ? 1 : 0
        border.color: delegate.outlineColor

        Rectangle {
            anchors {
                left: parent.left
                top: parent.top
                bottom: parent.bottom
            }
            width: 3
            color: delegate.keskAccent
            visible: delegate.selected
        }
    }

    contentItem: RowLayout {
        spacing: Kirigami.Units.smallSpacing

        Kirigami.Icon {
            id: itemIcon
            Layout.alignment: Qt.AlignVCenter
            Layout.leftMargin: delegate.leadingPadding + (delegate.selected ? Kirigami.Units.smallSpacing : 0)
            Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
            Layout.preferredHeight: Kirigami.Units.iconSizes.smallMedium
            source: delegate.icon.name !== "" ? delegate.icon.name : delegate.icon.source
            color: delegate.itemIconColor
        }

        Label {
            id: titleItem
            Layout.fillWidth: true
            color: delegate.itemTextColor
            text: delegate.text
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
            textFormat: Text.PlainText
        }

        Rectangle {
            Layout.alignment: Qt.AlignVCenter
            Layout.preferredWidth: Kirigami.Units.largeSpacing
            Layout.preferredHeight: Kirigami.Units.largeSpacing

            radius: delegate.selected ? 1 : 0
            visible: delegate.showDefaultIndicator && systemsettings.defaultsIndicatorsVisible
            Kirigami.Theme.colorSet: Kirigami.Theme.View
            color: delegate.selected ? delegate.keskAccent : Kirigami.Theme.neutralTextColor
        }

        Component {
            id: auxiliaryButtonActionComponent

            ToolButton {
                id: auxiliaryButton

                implicitWidth: height
                implicitHeight: Math.max(titleItem.implicitHeight, Kirigami.Units.gridUnit)
                icon.color: delegate.selected || pressed || visualFocus || hovered ? delegate.keskAccent : palette.buttonText

                display: AbstractButton.IconOnly
                text: delegate.auxiliaryAction.text
                icon.name: systemsettings.actionIconName(delegate.auxiliaryAction)
                onClicked: {
                    delegate.auxiliaryAction.trigger();
                }

                background: Rectangle {
                    radius: auxiliaryButton.hovered || auxiliaryButton.pressed || auxiliaryButton.visualFocus ? 1 : 0
                    color: auxiliaryButton.pressed ? Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.10) : "#11100e"
                    border.width: auxiliaryButton.hovered || auxiliaryButton.pressed || auxiliaryButton.visualFocus ? 1 : 0
                    border.color: auxiliaryButton.hovered || auxiliaryButton.pressed || auxiliaryButton.visualFocus ? delegate.keskAccent : "transparent"
                }

                ToolTip.text: delegate.auxiliaryAction.tooltip || delegate.auxiliaryAction.text
                ToolTip.delay: Kirigami.Units.toolTipDelay
                ToolTip.visible: ToolTip.text !== "" && (Kirigami.Settings.tabletMode ? pressed : hovered)
            }
        }

        Component {
            id: auxiliarySwitchActionComponent

            Switch {
                Accessible.name: delegate.auxiliaryAction.text
                checked: delegate.auxiliaryAction.checked
                onToggled: {
                    delegate.auxiliaryAction.trigger();
                }

                ToolTip.text: delegate.auxiliaryAction.tooltip || delegate.auxiliaryAction.text
                ToolTip.delay: Kirigami.Units.toolTipDelay
                ToolTip.visible: ToolTip.text !== "" && (Kirigami.Settings.tabletMode ? pressed : hovered)
            }
        }

        Loader {
            Layout.fillHeight: true
            Layout.topMargin: -delegate.topPadding + delegate.topInset
            Layout.bottomMargin: -delegate.bottomPadding + delegate.bottomInset
            Layout.rightMargin: -delegate.rightPadding + delegate.rightInset

            enabled: delegate.auxiliaryAction?.enabled ?? false
            visible: status === Loader.Ready
            sourceComponent: {
                const action = delegate.auxiliaryAction;
                if (action && action.visible) {
                    if (action.checkable) {
                        return auxiliarySwitchActionComponent;
                    } else {
                        return auxiliaryButtonActionComponent;
                    }
                }
                return null;
            }
        }

        Kirigami.Icon {
            Layout.alignment: Qt.AlignVCenter
            Layout.preferredWidth: Kirigami.Units.iconSizes.small
            Layout.preferredHeight: Kirigami.Units.iconSizes.small

            opacity: delegate.showArrow ? 0.7 : 0.0
            source: LayoutMirroring.enabled ? "go-next-symbolic-rtl" : "go-next-symbolic"
            color: delegate.selected ? delegate.keskAccent : delegate.itemIconColor
            visible: !delegate.auxiliaryAction?.visible ?? true
        }
    }
}
