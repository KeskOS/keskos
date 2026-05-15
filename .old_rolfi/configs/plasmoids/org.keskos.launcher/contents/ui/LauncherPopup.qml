import QtQuick
import QtQuick.Layouts
import org.kde.plasma.extras as PlasmaExtras

PlasmaExtras.Representation {
    id: root

    required property var launcherRoot
    required property var categories
    required property var favoritesModel
    required property var rootModel
    required property var runnerModel
    required property var powerItems
    required property string statusLine
    required property string errorMessage
    required property color accentColor
    required property color backgroundColor
    required property color panelColor
    required property color panelAltColor
    required property color textColor
    required property color dimTextColor
    required property color borderColor
    required property color hoverColor
    required property color selectedColor
    required property int menuWidth
    required property int menuHeight
    required property bool showPowerCategory

    property string activeCategory: "favorites"
    property int activeCategoryRow: -1
    property string searchQuery: ""
    property int currentIndex: 0
    property var visiblePowerItems: []
    property var localSearchResults: []
    readonly property bool searching: String(root.searchQuery || "").trim().length > 0
    readonly property bool powerCategoryActive: root.activeCategory === "power"
    readonly property bool runnerReady: Boolean(root.runnerModel && typeof root.runnerModel.count !== "undefined")
    readonly property int runnerResultCount: root.runnerReady ? Number(root.runnerModel.count) : 0
    readonly property int localSearchResultCount: Array.isArray(root.localSearchResults) ? root.localSearchResults.length : 0
    readonly property bool useLocalSearchResults: root.searching && root.runnerReady && root.runnerResultCount < 1 && root.localSearchResultCount > 0
    readonly property var currentAppModel: root.searching
        ? (root.useLocalSearchResults ? null : (root.runnerReady ? root.runnerModel : null))
        : (root.activeCategory === "favorites"
           ? (root.favoritesModel || null)
           : ((root.activeCategoryRow >= 0 && root.rootModel && typeof root.rootModel.modelForRow === "function")
              ? (root.rootModel.modelForRow(root.activeCategoryRow) || null)
              : null))
    readonly property int currentItemCount: root.powerCategoryActive
        ? (Array.isArray(root.visiblePowerItems) ? root.visiblePowerItems.length : 0)
        : (root.useLocalSearchResults
           ? root.localSearchResultCount
           : ((root.currentAppModel && typeof root.currentAppModel.count !== "undefined") ? Number(root.currentAppModel.count) : 0))

    signal powerRequested(string actionId)
    signal closeRequested()

    Layout.minimumWidth: root.menuWidth
    Layout.preferredWidth: root.menuWidth
    Layout.minimumHeight: root.menuHeight
    Layout.preferredHeight: root.menuHeight
    collapseMarginsHint: true

    function headerLabel() {
        const items = root.safeCategories()

        if (root.searching) {
            return "SEARCH RESULTS"
        }

        if (root.powerCategoryActive) {
            return "POWER / SESSION"
        }

        for (let i = 0; i < items.length; ++i) {
            if (items[i].key === root.activeCategory) {
                return String(items[i].label || "Applications").toUpperCase()
            }
        }

        return "APPLICATIONS"
    }

    function safeCategories() {
        return Array.isArray(root.categories) ? root.categories : []
    }

    function syncActiveCategory() {
        let found = false

        const items = root.safeCategories()

        for (let i = 0; i < items.length; ++i) {
            const entry = items[i]
            if (entry.key === root.activeCategory) {
                root.activeCategoryRow = Number(entry.row !== undefined ? entry.row : -1)
                found = true
                break
            }
        }

        if (!found && items.length > 0) {
            root.activeCategory = items[0].key
            root.activeCategoryRow = Number(items[0].row !== undefined ? items[0].row : -1)
        }
    }

    function refreshPowerItems() {
        const query = String(root.searchQuery || "").trim().toLowerCase()
        const items = Array.isArray(root.powerItems) ? root.powerItems : []

        if (!query) {
            root.visiblePowerItems = items.slice(0)
            return
        }

        root.visiblePowerItems = items.filter(function(item) {
            const haystack = [item.name || "", item.comment || "", item.id || ""].join(" ").toLowerCase()
            return haystack.indexOf(query) !== -1
        })
    }

    function matchesQuery(text, query) {
        if (!query) {
            return true
        }
        return String(text || "").toLowerCase().indexOf(query.toLowerCase()) !== -1
    }

    function modelDataValue(model, row, role, fallbackValue) {
        if (!model || !model.index || !model.data) {
            return fallbackValue
        }

        try {
            const index = model.index(row, 0)
            const value = model.data(index, role)
            if (value !== undefined && value !== null && value !== "") {
                return value
            }
        } catch (error) {
            // Ignore and fall back.
        }

        return fallbackValue
    }

    function appendSearchResult(model, row, label, comment, icon, favoriteId, url, seenKeys) {
        const key = String(favoriteId || url || label || ("row:" + row)).toLowerCase()
        if (!label || seenKeys[key]) {
            return
        }

        seenKeys[key] = true
        root.localSearchResults.push({
            "name": label,
            "comment": comment || "",
            "icon": icon || "application-x-executable",
            "sourceModel": model,
            "sourceRow": row
        })
    }

    function collectSearchResults(model, query, seenKeys, depth) {
        if (!model || depth > 4 || typeof model.count === "undefined") {
            return
        }

        for (let row = 0; row < model.count; ++row) {
            const label = String(root.modelDataValue(model, row, Qt.DisplayRole, model.labelForRow ? model.labelForRow(row) : "") || "").trim()
            const icon = root.modelDataValue(model, row, Qt.DecorationRole, "application-x-executable")
            const favoriteId = String(root.modelDataValue(model, row, Qt.UserRole + 2, ""))
            const url = String(root.modelDataValue(model, row, Qt.UserRole + 1, ""))
            const childModel = model.modelForRow ? model.modelForRow(row) : null
            const comment = String((childModel && childModel.description) ? childModel.description : "")
            const searchable = [label, comment, favoriteId, url].join(" ")

            if (childModel && typeof childModel.count !== "undefined" && childModel.count > 0 && !favoriteId && !url) {
                root.collectSearchResults(childModel, query, seenKeys, depth + 1)
                continue
            }

            if (root.matchesQuery(searchable, query)) {
                root.appendSearchResult(model, row, label, comment, icon, favoriteId, url, seenKeys)
            }
        }
    }

    function rebuildLocalSearchResults() {
        const query = String(root.searchQuery || "").trim()
        const seenKeys = {}

        root.localSearchResults = []

        if (!query) {
            return
        }

        root.collectSearchResults(root.favoritesModel || null, query, seenKeys, 0)
        root.collectSearchResults(root.rootModel || null, query, seenKeys, 0)
    }

    function resetSelection() {
        root.currentIndex = Number(root.currentItemCount) > 0 ? 0 : -1
    }

    function moveSelection(delta) {
        if (Number(root.currentItemCount) < 1) {
            root.currentIndex = -1
            return
        }

        let next = root.currentIndex + delta
        if (next < 0) {
            next = 0
        }
        if (next >= root.currentItemCount) {
            next = root.currentItemCount - 1
        }

        root.currentIndex = next

        if (root.powerCategoryActive) {
            powerList.ensureVisible(next)
        } else if (root.useLocalSearchResults) {
            fallbackSearchList.ensureVisible(next)
        } else {
            appList.ensureVisible(next)
        }
    }

    function focusSearchField() {
        searchField.forceActiveFocus()
        searchField.selectAll()
    }

    function activateCurrentItem() {
        if (root.currentIndex < 0) {
            return
        }

        if (root.powerCategoryActive) {
            if (root.visiblePowerItems && root.currentIndex < root.visiblePowerItems.length) {
                root.powerRequested(root.visiblePowerItems[root.currentIndex].id)
            }
            return
        }

        if (root.useLocalSearchResults) {
            const item = root.localSearchResults[root.currentIndex]
            if (item && item.sourceModel && item.sourceModel.trigger) {
                item.sourceModel.trigger(item.sourceRow, "", null)
                root.closeRequested()
            }
            return
        }

        if (root.currentAppModel && root.currentAppModel.trigger) {
            root.currentAppModel.trigger(root.currentIndex, "", null)
            root.closeRequested()
        }
    }

    onCategoriesChanged: syncActiveCategory()
    onActiveCategoryChanged: syncActiveCategory()
    onCurrentAppModelChanged: resetSelection()
    onCurrentItemCountChanged: {
        if (Number(root.currentItemCount) < 1) {
            root.currentIndex = -1
        } else if (root.currentIndex < 0 || root.currentIndex >= root.currentItemCount) {
            root.currentIndex = 0
        }
    }
    onSearchQueryChanged: {
        if (root.runnerModel && typeof root.runnerModel.query !== "undefined") {
            root.runnerModel.query = String(root.searchQuery || "").trim()
        }
        root.refreshPowerItems()
        root.rebuildLocalSearchResults()
        root.resetSelection()
    }
    Component.onCompleted: {
        root.syncActiveCategory()
        root.refreshPowerItems()
        root.rebuildLocalSearchResults()
        root.resetSelection()
    }

    Keys.onEscapePressed: root.closeRequested()

    Rectangle {
        anchors.fill: parent
        color: root.backgroundColor
        border.width: 1
        border.color: root.borderColor
    }

    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: Qt.rgba(206 / 255, 106 / 255, 53 / 255, 0.3)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            color: root.panelColor
            border.width: 1
            border.color: root.borderColor

            Column {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                anchors.topMargin: 8
                anchors.bottomMargin: 8
                spacing: 2

                Text {
                    text: "KESK SYSTEM MENU"
                    color: root.accentColor
                    font.family: "JetBrains Mono"
                    font.pixelSize: 24
                }

                Text {
                    text: root.statusLine || "APPLICATION INDEX ONLINE"
                    color: root.dimTextColor
                    font.family: "JetBrains Mono"
                    font.pixelSize: 13
                }
            }
        }

        Rectangle {
            visible: root.errorMessage.length > 0
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? 34 : 0
            color: root.panelAltColor
            border.width: 1
            border.color: root.borderColor

            Text {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                verticalAlignment: Text.AlignVCenter
                text: "[ WARN ] " + root.errorMessage
                color: root.accentColor
                font.family: "JetBrains Mono"
                font.pixelSize: 14
                elide: Text.ElideRight
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 8

            Rectangle {
                Layout.preferredWidth: 132
                Layout.fillHeight: true
                color: root.panelColor
                border.width: 1
                border.color: root.borderColor

                CategoryList {
                    anchors.fill: parent
                    anchors.margins: 6
                    categories: root.safeCategories().filter(function(item) {
                        return root.showPowerCategory || item.key !== "power"
                    })
                    activeCategory: root.activeCategory
                    accentColor: root.accentColor
                    textColor: root.textColor
                    dimTextColor: root.dimTextColor
                    hoverColor: root.hoverColor
                    selectedColor: root.selectedColor
                    borderColor: root.borderColor
                    onCategorySelected: function(categoryKey) {
                        root.activeCategory = categoryKey
                        root.searchQuery = ""
                        searchField.text = ""
                        root.resetSelection()
                        root.focusSearchField()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: root.panelColor
                border.width: 1
                border.color: root.borderColor

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 8

                    Text {
                        Layout.fillWidth: true
                        text: root.headerLabel()
                        color: root.accentColor
                        font.family: "JetBrains Mono"
                        font.pixelSize: 18
                    }

                    Loader {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        active: true
                        sourceComponent: root.powerCategoryActive ? powerListComponent : (root.useLocalSearchResults ? fallbackSearchComponent : appListComponent)
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 42
            color: root.panelAltColor
            border.width: 1
            border.color: root.borderColor

            Row {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 8

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: ">"
                    color: root.accentColor
                    font.family: "JetBrains Mono"
                    font.pixelSize: 18
                }

                TextInput {
                    id: searchField
                    width: parent.width - 28
                    anchors.verticalCenter: parent.verticalCenter
                    color: root.textColor
                    selectionColor: root.selectedColor
                    selectedTextColor: root.accentColor
                    clip: true
                    font.family: "JetBrains Mono"
                    font.pixelSize: 17
                    text: root.searchQuery
                    onTextChanged: root.searchQuery = text
                    Keys.onEscapePressed: root.closeRequested()
                    Keys.onUpPressed: root.moveSelection(-1)
                    Keys.onDownPressed: root.moveSelection(1)
                    Keys.onReturnPressed: root.activateCurrentItem()
                    Keys.onEnterPressed: root.activateCurrentItem()
                }
            }

            Text {
                visible: !searchField.text.length && !searchField.activeFocus
                anchors.left: parent.left
                anchors.leftMargin: 36
                anchors.verticalCenter: parent.verticalCenter
                text: "Search applications..."
                color: root.dimTextColor
                font.family: "JetBrains Mono"
                font.pixelSize: 17
            }
        }
    }

    Component {
        id: appListComponent

        Item {
            anchors.fill: parent

            KickerAppList {
                id: appList
                anchors.fill: parent
                visible: root.currentItemCount > 0
                itemsModel: root.currentAppModel || null
                currentIndex: root.currentIndex
                accentColor: root.accentColor
                textColor: root.textColor
                dimTextColor: root.dimTextColor
                hoverColor: root.hoverColor
                selectedColor: root.selectedColor
                borderColor: root.borderColor
                onIndexChangedByUser: function(index) {
                    root.currentIndex = index
                }
                onItemActivated: function(index) {
                    root.currentIndex = index
                    root.activateCurrentItem()
                }
            }

            Text {
                anchors.centerIn: parent
                visible: root.currentItemCount < 1
                text: root.searching ? "NO MATCHES" : "NO APPLICATIONS AVAILABLE"
                color: root.dimTextColor
                font.family: "JetBrains Mono"
                font.pixelSize: 16
            }
        }
    }

    Component {
        id: fallbackSearchComponent

        Item {
            anchors.fill: parent

            AppList {
                id: fallbackSearchList
                anchors.fill: parent
                visible: root.currentItemCount > 0
                items: root.localSearchResults
                currentIndex: root.currentIndex
                accentColor: root.accentColor
                textColor: root.textColor
                dimTextColor: root.dimTextColor
                hoverColor: root.hoverColor
                selectedColor: root.selectedColor
                borderColor: root.borderColor
                onIndexChangedByUser: function(index) {
                    root.currentIndex = index
                }
                onItemActivated: function(item) {
                    const idx = root.localSearchResults.indexOf(item)
                    if (idx >= 0) {
                        root.currentIndex = idx
                        root.activateCurrentItem()
                    }
                }
            }

            Text {
                anchors.centerIn: parent
                visible: root.currentItemCount < 1
                text: "NO MATCHES"
                color: root.dimTextColor
                font.family: "JetBrains Mono"
                font.pixelSize: 16
            }
        }
    }

    Component {
        id: powerListComponent

        Item {
            anchors.fill: parent

            PowerMenu {
                id: powerList
                anchors.fill: parent
                visible: root.currentItemCount > 0
                items: root.visiblePowerItems
                currentIndex: root.currentIndex
                accentColor: root.accentColor
                textColor: root.textColor
                dimTextColor: root.dimTextColor
                hoverColor: root.hoverColor
                selectedColor: root.selectedColor
                borderColor: root.borderColor
                onIndexChangedByUser: function(index) {
                    root.currentIndex = index
                }
                onItemActivated: function(item) {
                    root.powerRequested(item.id)
                }
            }

            Text {
                anchors.centerIn: parent
                visible: root.currentItemCount < 1
                text: "NO SESSION ACTIONS AVAILABLE"
                color: root.dimTextColor
                font.family: "JetBrains Mono"
                font.pixelSize: 16
            }
        }
    }
}
