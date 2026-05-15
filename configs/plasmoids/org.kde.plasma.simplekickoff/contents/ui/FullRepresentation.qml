/*
    SPDX-FileCopyrightText: 2011 Martin Gräßlin <mgraesslin@kde.org>
    SPDX-FileCopyrightText: 2012 Gregor Taetzner <gregor@freenet.de>
    SPDX-FileCopyrightText: 2012 Marco Martin <mart@kde.org>
    SPDX-FileCopyrightText: 2013 2014 David Edmundson <davidedmundson@kde.org>
    SPDX-FileCopyrightText: 2014 Sebastian Kügler <sebas@kde.org>
    SPDX-FileCopyrightText: 2021 Mikel Johnson <mikel5764@gmail.com>
    SPDX-FileCopyrightText: 2021 Noah Davis <noahadvs@gmail.com>
    SPDX-FileCopyrightText: 2023 Himprakash Deka <himprakashd@gmail.com>

    SPDX-License-Identifier: GPL-2.0-or-later
*/
import QtQuick 2.15
import QtQuick.Templates 2.15 as T
import QtQuick.Layouts 1.15
import QtQml 2.15
import org.kde.plasma.plasmoid 2.0
import org.kde.kirigami 2.20 as Kirigami
import org.kde.plasma.extras 2.0 as PlasmaExtras

EmptyPage {
    id: root

    KeskStyle {
        id: keskStyle
    }

    // kickoff is Kickoff.qml
    leftPadding: 14
    rightPadding: 14
    topPadding: 12
    bottomPadding: 10
    readonly property var appletInterface: kickoff

    Layout.minimumWidth: implicitWidth
    Layout.maximumWidth: Kirigami.Units.gridUnit * 80
    Layout.minimumHeight: implicitHeight
    Layout.maximumHeight: Kirigami.Units.gridUnit * 40
    Layout.preferredWidth: Math.max(implicitWidth, width)
    Layout.preferredHeight: Math.max(implicitHeight, height)

    property alias applicationsPage: applicationsPage
    property bool blockingHoverFocus: false
    spacing: 10

    background: Item {
        Rectangle {
            anchors.fill: parent
            color: keskStyle.backgroundColor
            border.width: 1
            border.color: keskStyle.accentBrightColor
            radius: keskStyle.panelCornerRadius
        }

        Repeater {
            model: Math.ceil(parent.height / 5)

            Rectangle {
                width: parent ? parent.width : 0
                height: 1
                y: index * 5
                color: index % 2 === 0 ? keskStyle.scanlineColor : Qt.rgba(1, 1, 1, 0.008)
            }
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            color: "transparent"
            border.width: 1
            border.color: keskStyle.innerBorderColor
            radius: keskStyle.panelCornerRadius
        }
    }

    /* NOTE: Important things to know about keyboard input handling:
     *
     * - Key events are passed up to parent items until the end is reached.
     * Be mindful of this when using `Keys.forwardTo`.
     *
     * - Keys defaults to BeforeItem while KeyNavigation defaults to AfterItem.
     *
     * - When Keys and KeyNavigation are using the same priority, it seems like
     * the one declared first in the QML file gets priority over the other.
     *
     * - Except for Keys.onPressed, all Keys.on*Pressed signals automatically
     * set `event.accepted = true`.
     *
     * - If you do `item.forceActiveFocus()` and `item` is a focus scope, the
     * children of `item` won't necessarily get focus. It seems like
     * `forceActiveFocus()` is better for forcing a specific thing to be focused
     * while KeyNavigation is better at passing focus down to children of the
     * thing you want to focus when dealing with focus scopes.
     *
     * - KeyNavigation uses BacktabFocusReason (TabFocusReason if mirrored) for left,
     * TabFocusReason (BacktabFocusReason if mirrored) for right,
     * BacktabFocusReason for up and TabFocusReason for down.
     *
     * - KeyNavigation does not seem to respect dynamic changes to focus chain
     * rules in the reverse direction, which can lead to confusing results.
     * It is therefore safer to use Keys for items whose position in the Tab
     * order must be changed on demand. (Tested with Qt 5.15.8 on X11.)
     */

    header: Header {
        id: header
        preferredSearchBarWidth: applicationsPage.stackViewWidth
        Binding {
            target: kickoff
            property: "header"
            value: header
            restoreMode: Binding.RestoreBinding
        }
    }

    contentItem: VerticalStackView {
        id: contentItemStackView
        focus: true
        movementTransitionsEnabled: true
        // Not using a component to prevent it from being destroyed
        initialItem: ApplicationsPage {
            id: applicationsPage
            preferredSideBarWidth: header.leaveButtons.width
            objectName: "applicationsPage"
        }

        Component {
            id: searchViewComponent
            KickoffListView {
                id: searchView
                objectName: "searchView"
                mainContentView: true
                implicitWidth: applicationsPage.implicitWidth
                implicitHeight: applicationsPage.implicitHeight
                // Forces the function be re-run every time runnerModel.count changes.
                // This is absolutely necessary to make the search view work reliably.
                model: kickoff.runnerModel.count ? kickoff.runnerModel.modelForRow(0) : null
                delegate: KickoffListDelegate {
                    width: view.availableWidth
                    isSearchResult: true
                }
                activeFocusOnTab: true
                property var interceptedPosition: null
                Keys.onTabPressed: event => {
                    kickoff.firstHeaderItem.forceActiveFocus(Qt.TabFocusReason);
                }
                Keys.onBacktabPressed: event => {
                    kickoff.lastHeaderItem.forceActiveFocus(Qt.BacktabFocusReason);
                }
                T.StackView.onActivated: {
                    kickoff.sideBar = null
                    kickoff.contentArea = searchView
                }

                Connections {
                    target: blockHoverFocusHandler
                    enabled: blockHoverFocusHandler.enabled && !searchView.interceptedPosition
                    function onPointChanged() {
                        searchView.interceptedPosition = blockHoverFocusHandler.point.position
                    }
                }

                Connections {
                    target: blockHoverFocusHandler
                    enabled: blockHoverFocusHandler.enabled && searchView.interceptedPosition && root.blockingHoverFocus
                    function onPointChanged() {
                        if (blockHoverFocusHandler.point.position === searchView.interceptedPosition) {
                            return;
                        }
                        root.blockingHoverFocus = false
                    }
                }

                HoverHandler {
                    id: blockHoverFocusHandler
                    enabled: !contentItemStackView.busy && (!searchView.interceptedPosition || root.blockingHoverFocus)
                }

                Loader {
                    anchors.centerIn: searchView.view
                    width: searchView.view.width - (Kirigami.Units.gridUnit * 4)

                    active: searchView.view.count === 0
                    visible: active
                    asynchronous: true

                    sourceComponent: PlasmaExtras.PlaceholderMessage {
                        id: emptyHint

                        iconName: "edit-none"
                        opacity: 0
                        text: i18nc("@info:status", "No matches")

                        Connections {
                            target: kickoff.runnerModel
                            function onQueryFinished() {
                                showAnimation.restart()
                            }
                        }

                        NumberAnimation {
                            id: showAnimation
                            duration: Kirigami.Units.longDuration
                            easing.type: Easing.OutCubic
                            property: "opacity"
                            target: emptyHint
                            to: 1
                        }
                    }
                }
            }
        }

        Keys.priority: Keys.AfterItem
        // This is here rather than root because events are implicitly forwarded
        // to parent items. Don't want to send multiple events to searchField.
        Keys.forwardTo: kickoff.searchField

        Connections {
            target: root.header
            function onSearchTextChanged() {
                if (root.header.searchText.length === 0 && contentItemStackView.currentItem.objectName !== "applicationsPage") {
                    root.blockingHoverFocus = false
                    contentItemStackView.reverseTransitions = true
                    contentItemStackView.replace(applicationsPage)
                } else if (root.header.searchText.length > 0) {
                    if (contentItemStackView.currentItem.objectName !== "searchView") {
                        contentItemStackView.reverseTransitions = false
                        contentItemStackView.replace(searchViewComponent)
                    } else {
                        root.blockingHoverFocus = true
                        contentItemStackView.contentItem.interceptedPosition = null
                        contentItemStackView.contentItem.currentIndex = 0
                    }
                }
            }
        }
    }

    footer: Rectangle {
        implicitHeight: 28
        color: keskStyle.panelAltColor
        border.width: 1
        border.color: keskStyle.borderColor
        radius: keskStyle.panelCornerRadius

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 8
            anchors.rightMargin: 8

            Image {
                source: Qt.resolvedUrl("../images/keskos-mark.png")
                sourceSize.width: 12
                sourceSize.height: 18
                fillMode: Image.PreserveAspectFit
                Layout.alignment: Qt.AlignVCenter
            }

            RowLayout {
                spacing: 6

                Text {
                    text: "KeskOS"
                    color: keskStyle.accentColor
                    font.family: keskStyle.uiFontFamily
                    font.pixelSize: 12
                }

                Text {
                    text: "v1.0.0"
                    color: keskStyle.textMutedColor
                    font.family: keskStyle.uiFontFamily
                    font.pixelSize: 11
                }
            }

            Item {
                Layout.fillWidth: true
            }

            Text {
                text: "SYS: ONLINE"
                color: keskStyle.accentColor
                font.family: keskStyle.uiFontFamily
                font.pixelSize: 11
            }
        }
    }

    Component.onCompleted: {
        rootModel.refresh();
    }
}
