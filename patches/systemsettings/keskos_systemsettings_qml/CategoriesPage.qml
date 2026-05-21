/*
   SPDX-FileCopyrightText: 2017 Marco Martin <mart@kde.org>

   SPDX-License-Identifier: LGPL-2.0-only
*/

pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.systemsettings

Kirigami.ScrollablePage {
    id: mainColumn
    readonly property bool searchMode: searchField.text.length > 0
    readonly property color keskAccent: "#ce6a35"
    verticalScrollBarPolicy: QQC2.ScrollBar.AlwaysOff

    Kirigami.Theme.colorSet: Kirigami.Theme.View
    Kirigami.Theme.inherit: false

    header: Kirigami.AbstractApplicationHeader {
        id: pageHeader

        // TODO Plasma 6.6 align size to grid
        height: Math.round((sizeHelper.implicitHeight + Kirigami.Units.smallSpacing * 2) * systemsettings.devicePixelRatio) / systemsettings.devicePixelRatio

        // Not visible; just to get its size so we can match this custom header
        // with the height of a standard header
        QQC2.ToolButton {
            id: sizeHelper
            visible: false
            icon.name: "go-previous"
        }

        background: Rectangle {
            color: "#050505"

            Rectangle {
                anchors {
                    left: parent.left
                    right: parent.right
                    bottom: parent.bottom
                }
                height: 1
                color: Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.35)
            }
        }

        contentItem: RowLayout {
            id: rowLayout
            // FIXME: left and right anchors shouldn't be needed here, but if
            // they're removed, the layout doesn't span the full width
            anchors {
                fill: parent
                leftMargin: Kirigami.Units.smallSpacing
                rightMargin: Kirigami.Units.smallSpacing
            }
            spacing: Kirigami.Units.smallSpacing

            Keys.onDownPressed: event => {
                categoryView.currentIndex = 0;
                event.accepted = false; // Pass to KeyNavigation.down
            }

            Kirigami.SearchField {
                id: searchField

                readonly property color keskAccent: "#ce6a35"

                focus: !Kirigami.InputMethod.willShowOnActive
                Layout.fillWidth: true
                Layout.preferredHeight: Math.round(Kirigami.Units.gridUnit * 1.65)
                Layout.alignment: Qt.AlignVCenter
                color: "#b8afa6"
                placeholderTextColor: "#8f8a84"
                leftPadding: Kirigami.Units.smallSpacing * 2
                rightPadding: Kirigami.Units.smallSpacing * 2
                topPadding: Kirigami.Units.smallSpacing * 0.75
                bottomPadding: Kirigami.Units.smallSpacing * 0.75
                onTextChanged: {
                    systemsettings.searchModel.filterRegExp = text;
                }

                background: Rectangle {
                    radius: 1
                    color: "#050505"
                    border.width: 1
                    border.color: searchField.activeFocus ? searchField.keskAccent : Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.35)
                }

                KeyNavigation.right: hamburgerMenuButton

                KeyNavigation.down: categoryView

                KeyNavigation.backtab: KeyNavigation.left
                KeyNavigation.tab: KeyNavigation.right

                Keys.onDownPressed: event => rowLayout.Keys.downPressed(event)
                onActiveFocusChanged: {
                    if (activeFocus) {
                        systemsettings.giveFocus();
                    }
                }
            }

            HamburgerMenuButton {
                id: hamburgerMenuButton

                KeyNavigation.left: searchField

                KeyNavigation.down: categoryView

                KeyNavigation.backtab: KeyNavigation.left
                KeyNavigation.tab: KeyNavigation.down

                Keys.onDownPressed: event => rowLayout.Keys.downPressed(event)
            }
        }
    }

    // We don't want it to go into default property and be reparented to a
    // ScrollView, otherwise after clearing search term the scrollbar would
    // appear and shift the fading out placeholder to the left.
    property Item __placeholder: Loader {
        parent: mainColumn
        anchors.centerIn: parent
        width: parent.width - (Kirigami.Units.gridUnit * 4)
        opacity: categoryView.count === 0 ? 1 : 0
        active: opacity > 0
        visible: active
        Behavior on opacity {
            NumberAnimation {
                duration: Kirigami.Units.longDuration
                easing.type: Easing.InOutQuad
            }
        }
        sourceComponent: Kirigami.PlaceholderMessage {
            width: parent.width
            icon.name: "edit-none"
            text: i18nc("A search yielded no results", "No items matching your search")
        }
    }

    Binding {
        target: categoryView
        property: "currentIndex"
        value: mainColumn.searchMode
            ? systemsettings.activeSearchRow
            : systemsettings.activeCategoryRow
    }

    ListView {
        id: categoryView

        model: mainColumn.searchMode ? systemsettings.searchModel : systemsettings.categoryModel

        activeFocusOnTab: true
        keyNavigationWraps: true
        Accessible.role: Accessible.List

        KeyNavigation.up: searchField
        KeyNavigation.backtab: hamburgerMenuButton
        Keys.onUpPressed: event => {
            if (categoryView.currentIndex === 0) {
                categoryView.currentIndex = -1;
            }
            event.accepted = false; // Pass to KeyNavigation.up
        }
        Keys.onTabPressed: {
            systemsettings.focusNext();
        }

        section {
            property: "categoryDisplayRole"
            delegate: Item {
                required property string section

                width: ListView.view.width
                implicitHeight: Math.round(Kirigami.Units.gridUnit * 1.1)

                RowLayout {
                    anchors {
                        fill: parent
                        leftMargin: Kirigami.Units.smallSpacing * 2
                        rightMargin: Kirigami.Units.smallSpacing * 2
                    }
                    spacing: Kirigami.Units.smallSpacing

                    QQC2.Label {
                        text: section
                        color: "#8f8a84"
                        font.weight: Font.DemiBold
                        textFormat: Text.PlainText
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        implicitHeight: 1
                        color: Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.18)
                    }
                }
            }
        }

        QQC2.ScrollBar.vertical: QQC2.ScrollBar {
            id: categoryScrollBar
            width: 6
            policy: QQC2.ScrollBar.AsNeeded

            background: Rectangle {
                color: "#050505"
                radius: 0
            }

            contentItem: Rectangle {
                implicitWidth: 6
                radius: 0
                color: categoryScrollBar.pressed || categoryScrollBar.hovered
                    ? "#ce6a35"
                    : Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.45)
            }
        }

        delegate: CategoryItem {
            id: delegate

            required property int index
            required property var model
            required property bool isCategory
            required property int depth
            required property bool isKCM
            required property string iconName

            text: model.display
            icon.name: iconName

            showArrow: {
                if (!isCategory) {
                    return false;
                }
                const modelIndex = delegate.ListView.view.model.index(index, 0)
                return delegate.ListView.view.model.rowCount(modelIndex) > 1
            }
            // Only indent subcategory icons in the search view
            leadingPadding: (depth > 1 && searchField.text.length > 0) ? (( depth - 1 ) * Kirigami.Units.iconSizes.smallMedium) + Kirigami.Units.largeSpacing : 0

            hoverEnabled: !isCategory || !mainColumn.searchMode
            enabled: !isCategory || !mainColumn.searchMode

            highlighted: ListView.isCurrentItem

            onClicked: {
                if (!enabled) { return; }
                if (isKCM || mainColumn.searchMode || systemsettings.activeCategoryRow !== index) {
                    systemsettings.loadModule(categoryView.model.index(index, 0));
                }
                if (!mainColumn.searchMode && root.pageStack.depth > 1) {
                    root.pageStack.currentIndex = 1;
                }
            }
            onFocusChanged: {
                if (isCategory && mainColumn.searchMode) {
                    return;
                }
                if (focus) {
                    categoryView.positionViewAtIndex(index, ListView.Contain);
                }
            }
            Keys.onEnterPressed: clicked();
            Keys.onReturnPressed: clicked();

            Keys.onLeftPressed: {
                if (LayoutMirroring.enabled) {
                    clicked();
                }
            }
            Keys.onRightPressed: {
                if (!LayoutMirroring.enabled) {
                    clicked();
                }
            }
        }
    }
}
