import QtQuick 2.15
import QtQuick.Layouts 1.15
import calamares.slideshow 1.0

Presentation {
    id: presentation

    property int frameIndex: 0
    property string debugText: "Awaiting Calamares session output..."
    property string stageText: "> Installer console online.\n> Waiting for partition and deploy-review stages to begin."
    property string summaryText: "> Live desktop: active\n> Installer backend: armed\n> Target root pipeline: ready"
    property string profileText: "- Filesystem: Arch defaults from Calamares\n- Bootloader: GRUB (EFI)\n- Desktop: KDE Plasma + KeskOS defaults\n- Personalization: deferred to Kesk Welcome after login\n- Login target: finished desktop with Welcome handoff"
    property string notesText: "- Calamares applies required KeskOS desktop defaults automatically.\n- Browser selection, widgets, optional apps, and theme checks continue in Kesk Welcome.\n- A sanitized install report is sent to api.keskos.org.\n- Detailed installer output is written to the per-user cache directory as keskos/calamares-installer.log"
    property var stageFrames: [
        "> Installer console online.\n> Waiting for partition and deploy-review stages to begin.",
        "> Pre-flight checks complete.\n> Locale, keyboard, and storage modules are standing by.",
        "> Deploy review armed.\n> Core desktop defaults and post-install hooks will be applied automatically.",
        "> Target deployment pipeline ready.\n> Calamares will hand off to the KeskOS post-install hooks automatically."
    ]
    property var summaryFrames: [
        "> Live desktop: active\n> Installer backend: armed\n> Target root pipeline: ready",
        "> Network path: optional\n> Locale + time: staged\n> User profile module: armed",
        "> Package manifest: loaded\n> Desktop defaults: staged\n> Plasma theme profile: ready",
        "> Welcome handoff: staged\n> Bootloader target: GRUB (EFI)\n> Post-install hooks: staged"
    ]
    property var debugFrames: [
        "[ OK ] calamares branding loaded\n[ OK ] display stack online\n[ OK ] package manifest loaded\n[ .. ] waiting for installer interaction",
        "[ OK ] locale + keyboard modules online\n[ OK ] storage probe armed\n[ OK ] deploy review page ready\n[ .. ] awaiting confirmation",
        "[ OK ] target root pipeline staged\n[ OK ] desktop defaults queued for apply\n[ OK ] Welcome handoff staged\n[ .. ] deployment begins after confirmation",
        "[ OK ] live session helpers available\n[ OK ] install logs still written to cache\n[ OK ] first-boot personalization moves to Welcome\n[ .. ] installer running in guided deployment mode"
    ]

    function refreshDebug() {
        var stageIndex = frameIndex % stageFrames.length
        var summaryIndex = frameIndex % summaryFrames.length
        var debugIndex = frameIndex % debugFrames.length

        stageText = stageFrames[stageIndex]
        summaryText = summaryFrames[summaryIndex]
        debugText = debugFrames[debugIndex]
        frameIndex = frameIndex + 1
    }

    Timer {
        interval: 1200
        repeat: true
        running: true
        triggeredOnStart: true
        onTriggered: presentation.refreshDebug()
    }

    Slide {
        id: slide
        anchors.fill: parent
        clip: true

        Rectangle {
            anchors.fill: parent
            color: "#050403"

            Image {
                anchors.fill: parent
                source: "wallpaper.png"
                fillMode: Image.PreserveAspectCrop
                opacity: 0.08
                smooth: true
            }

            Rectangle {
                anchors.fill: parent
                color: "#050403"
                opacity: 0.94
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 14

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 42
                    spacing: 14

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 2
                        color: "#ce6a35"
                        opacity: 0.75
                    }

                    Text {
                        text: "[ KESKOS INSTALLATION CONSOLE ]"
                        color: "#ce6a35"
                        font.family: "VT323"
                        font.pixelSize: 30
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 2
                        color: "#ce6a35"
                        opacity: 0.75
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.max(188, slide.height * 0.28)
                    spacing: 14

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#040303"
                        border.color: "#8f4f2a"
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 10

                            Text {
                                text: "[ DEPLOY STATUS ]"
                                color: "#ce6a35"
                                font.family: "VT323"
                                font.pixelSize: 28
                            }

                            Text {
                                Layout.fillWidth: true
                                text: presentation.stageText
                                color: "#e7c9b3"
                                wrapMode: Text.WordWrap
                                font.family: "JetBrainsMono Nerd Font"
                                font.pixelSize: 15
                                lineHeight: 1.14
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 1
                                color: "#7a4e36"
                            }

                            Text {
                                Layout.fillWidth: true
                                text: presentation.summaryText
                                color: "#e7c9b3"
                                wrapMode: Text.WordWrap
                                font.family: "JetBrainsMono Nerd Font"
                                font.pixelSize: 14
                                lineHeight: 1.12
                            }
                        }
                    }

                    Rectangle {
                        Layout.preferredWidth: Math.max(360, slide.width * 0.36)
                        Layout.fillHeight: true
                        color: "#040303"
                        border.color: "#8f4f2a"
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 10

                            Text {
                                text: "[ INSTALL PROFILE ]"
                                color: "#ce6a35"
                                font.family: "VT323"
                                font.pixelSize: 28
                            }

                            Text {
                                Layout.fillWidth: true
                                text: presentation.profileText
                                color: "#e7c9b3"
                                wrapMode: Text.WordWrap
                                font.family: "JetBrainsMono Nerd Font"
                                font.pixelSize: 14
                                lineHeight: 1.12
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 1
                                color: "#7a4e36"
                            }

                            Text {
                                text: "[ LIVE SYSTEM NOTES ]"
                                color: "#ce6a35"
                                font.family: "VT323"
                                font.pixelSize: 22
                            }

                            Text {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                text: presentation.notesText
                                color: "#e7c9b3"
                                wrapMode: Text.WordWrap
                                font.family: "JetBrainsMono Nerd Font"
                                font.pixelSize: 13
                                lineHeight: 1.1
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#040303"
                    border.color: "#8f4f2a"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            Text {
                                text: "[ LIVE DEBUG STREAM ]"
                                color: "#ce6a35"
                                font.family: "VT323"
                                font.pixelSize: 30
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 1
                                color: "#7a4e36"
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            text: "> Installer state preview active. Detailed logs are still written to the per-user cache directory."
                            color: "#ce6a35"
                            wrapMode: Text.WordWrap
                            font.family: "JetBrainsMono Nerd Font"
                            font.pixelSize: 13
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            color: "#7a4e36"
                        }

                        Text {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            text: presentation.debugText
                            color: "#e7c9b3"
                            wrapMode: Text.WordWrap
                            font.family: "JetBrainsMono Nerd Font"
                            font.pixelSize: 14
                            lineHeight: 1.1
                            clip: true
                        }
                    }
                }
            }
        }
    }
}
