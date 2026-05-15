/*
    SPDX-FileCopyrightText: 2011 Martin Gräßlin <mgraesslin@kde.org>
    SPDX-FileCopyrightText: 2012 Marco Martin <mart@kde.org>
    SPDX-FileCopyrightText: 2015-2018 Eike Hein <hein@kde.org>
    SPDX-FileCopyrightText: 2021 Mikel Johnson <mikel5764@gmail.com>
    SPDX-FileCopyrightText: 2021 Noah Davis <noahadvs@gmail.com>
    SPDX-FileCopyrightText: 2023 Himprakash Deka <himprakashd@gmail.com>

    SPDX-License-Identifier: GPL-2.0-or-later
*/
import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Templates 2.15 as T
import QtQml 2.15
import org.kde.ksvg 1.0 as KSvg
import org.kde.plasma.workspace.trianglemousefilter 1.0

FocusScope {
    id: root
    KeskStyle {
        id: keskStyle
    }
    property real preferredSideBarWidth: implicitSideBarWidth
    property real preferredSideBarHeight: implicitSideBarHeight

    property alias sideBarComponent: sideBarLoader.sourceComponent
    property alias sideBarItem: sideBarLoader.item
    property alias contentAreaComponent: contentAreaLoader.sourceComponent
    property alias contentAreaItem: contentAreaLoader.item

    property alias implicitSideBarWidth: sideBarLoader.implicitWidth
    property alias implicitSideBarHeight: sideBarLoader.implicitHeight

    implicitWidth: root.preferredSideBarWidth + contentAreaLoader.implicitWidth
    implicitHeight: Math.max(root.preferredSideBarHeight, contentAreaLoader.implicitHeight)

    TriangleMouseFilter {
        id: sideBarFilter
        anchors {
            left: parent.left
            top: parent.top
            bottom: parent.bottom
        }
        LayoutMirroring.enabled: kickoff.sideBarOnRight
        implicitWidth: root.preferredSideBarWidth
        implicitHeight: root.preferredSideBarHeight
        edge: kickoff.sideBarOnRight ? Qt.LeftEdge : Qt.RightEdge
        blockFirstEnter: true

        Rectangle {
            anchors.fill: parent
            color: keskStyle.panelAltColor
            border.width: 1
            border.color: keskStyle.borderColor
            radius: keskStyle.panelCornerRadius
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            color: "transparent"
            border.width: 1
            border.color: keskStyle.innerBorderColor
            radius: keskStyle.panelCornerRadius
        }

        Repeater {
            model: Math.ceil(parent.height / 6)

            Rectangle {
                width: parent ? parent.width - 4 : 0
                height: 1
                x: 2
                y: 2 + (index * 6)
                color: Qt.rgba(1, 1, 1, 0.012)
            }
        }

        Loader {
            id: sideBarLoader
            anchors.fill: parent
            anchors.margins: 8
            // When positioned after the content area, Tab should go to the start of the header focus chain
            Keys.onTabPressed: event => {
                (kickoff.paneSwap ? kickoff.header.nextItemInFocusChain() : contentAreaLoader)
                    .forceActiveFocus(Qt.TabFocusReason);
            }
            Keys.onBacktabPressed: event => {
                (kickoff.paneSwap ? contentAreaLoader : kickoff.header.pinButton)
                    .forceActiveFocus(Qt.BacktabFocusReason);
            }
            Keys.onLeftPressed: event => {
                if (kickoff.sideBarOnRight) {
                    contentAreaLoader.forceActiveFocus();
                }
            }
            Keys.onRightPressed: event => {
                if (!kickoff.sideBarOnRight) {
                    contentAreaLoader.forceActiveFocus();
                }
            }
            Keys.onUpPressed: event => {
                kickoff.header.nextItemInFocusChain()
                    .forceActiveFocus(Qt.BacktabFocusReason);
            }
            Keys.onDownPressed: event => {
                kickoff.header.leaveButtons.nextItemInFocusChain()
                    .forceActiveFocus(Qt.TabFocusReason);
            }
        }
    }
    Item {
        id: contentAreaFrame
        anchors {
            left: sideBarFilter.right
            right: parent.right
            top: parent.top
            bottom: parent.bottom
        }
        LayoutMirroring.enabled: kickoff.sideBarOnRight

        Rectangle {
            anchors.fill: parent
            color: keskStyle.panelColor
            border.width: 1
            border.color: keskStyle.borderColor
            radius: keskStyle.panelCornerRadius
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            color: "transparent"
            border.width: 1
            border.color: keskStyle.innerBorderColor
            radius: keskStyle.panelCornerRadius
        }

        Repeater {
            model: Math.ceil(parent.height / 6)

            Rectangle {
                width: parent ? parent.width - 4 : 0
                height: 1
                x: 2
                y: 2 + (index * 6)
                color: Qt.rgba(1, 1, 1, 0.012)
            }
        }

        Loader {
            id: contentAreaLoader
            focus: true
            anchors.fill: parent
            anchors.margins: 10
            // When positioned after the sidebar, Tab should go to the start of the header focus chain
            Keys.onTabPressed: event => {
                (kickoff.paneSwap ? sideBarLoader : kickoff.header.nextItemInFocusChain())
                    .forceActiveFocus(Qt.TabFocusReason)
            }
            Keys.onBacktabPressed: event => {
                (kickoff.paneSwap ? kickoff.header.avatar : sideBarLoader)
                    .forceActiveFocus(Qt.BacktabFocusReason)
            }
            Keys.onLeftPressed: event => {
                if (!kickoff.sideBarOnRight) {
                    sideBarLoader.forceActiveFocus();
                }
            }
            Keys.onRightPressed: event => {
                if (kickoff.sideBarOnRight) {
                    sideBarLoader.forceActiveFocus();
                }
            }
            Keys.onUpPressed: event => {
                kickoff.searchField.forceActiveFocus(Qt.BacktabFocusReason);
            }
            Keys.onDownPressed: event => {
                kickoff.header.leaveButtons.nextItemInFocusChain()
                    .forceActiveFocus(Qt.TabFocusReason)
            }
        }
    }
}
