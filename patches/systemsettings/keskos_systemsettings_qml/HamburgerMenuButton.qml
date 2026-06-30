/*
   SPDX-FileCopyrightText: 2017 Marco Martin <mart@kde.org>
   SPDX-FileCopyrightText: 2023 ivan tkachenko <me@ratijas.tk>

   SPDX-License-Identifier: LGPL-2.0-only
*/

import QtQuick 2.15
import QtQuick.Controls 2.15 as QQC2

import org.kde.kirigami 2.20 as Kirigami

import org.kde.systemsettings

QQC2.ToolButton {
    id: control

    readonly property color keskAccent: "#ce6a35"

    icon.name: "application-menu"
    icon.color: checked || hovered || pressed || visualFocus ? keskAccent : palette.buttonText

    display: QQC2.AbstractButton.IconOnly
    padding: Kirigami.Units.smallSpacing
    implicitWidth: Math.round(Kirigami.Units.gridUnit * 1.8)
    implicitHeight: Math.round(Kirigami.Units.gridUnit * 1.8)

    checkable: true
    checked: systemsettings.actionMenuVisible
    onToggled: if (checked) {
        systemsettings.showActionMenu(mapToGlobal(0, height));
    }

    background: Rectangle {
        radius: control.checked || control.hovered || control.pressed || control.visualFocus ? 1 : 0
        color: control.pressed || control.checked ? Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.10) : "#050505"
        border.width: 1
        border.color: control.checked || control.hovered || control.pressed || control.visualFocus ? control.keskAccent : Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.35)
    }

    Accessible.role: Accessible.ButtonMenu
    Accessible.name: i18n("Show menu")
    QQC2.ToolTip.text: Accessible.name
    QQC2.ToolTip.visible: hovered && !pressed
    QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
}
