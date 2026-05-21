#include "panelskcm.h"

#include <KPluginFactory>

#include <QDir>

K_PLUGIN_CLASS_WITH_JSON(PanelsKcm, "kcm_keskos_panels.json")

namespace
{
QString shortcutsFile()
{
    return QDir::homePath() + QStringLiteral("/.config/kglobalshortcutsrc");
}

QString kwinFile()
{
    return QDir::homePath() + QStringLiteral("/.config/kwinrc");
}

QString shortcutValueFor(const QString &shortcut)
{
    return QStringLiteral("%1,%1,Activate Application Launcher").arg(shortcut);
}
}

PanelsKcm::PanelsKcm(QObject *parent, const KPluginMetaData &data)
    : KeskModuleBase(parent, data)
{
    refresh();
}

QString PanelsKcm::currentLauncherShortcut() const
{
    return m_currentLauncherShortcut;
}

void PanelsKcm::refresh()
{
    const QString shortcutValue = readIniValue({shortcutsFile()}, QStringLiteral("plasmashell"), QStringLiteral("activate application launcher"));
    QString nextShortcut = QStringLiteral("Meta");

    if (shortcutValue.startsWith(QStringLiteral("Meta+Q"))) {
        nextShortcut = QStringLiteral("Meta+Q");
    } else if (shortcutValue.startsWith(QStringLiteral("Meta+Space"))) {
        nextShortcut = QStringLiteral("Meta+Space");
    }

    if (m_currentLauncherShortcut != nextShortcut) {
        m_currentLauncherShortcut = nextShortcut;
        Q_EMIT stateChanged();
    }
}

void PanelsKcm::setLauncherShortcut(const QString &shortcut)
{
    const QString kwriteconfig = findExecutable({QStringLiteral("kwriteconfig6"), QStringLiteral("kwriteconfig5")});
    if (kwriteconfig.isEmpty()) {
        setStatus(QStringLiteral("kwriteconfig was not found on this system."), QStringLiteral("error"));
        return;
    }

    setBusy(true);

    runCommand(kwriteconfig, {
        QStringLiteral("--file"), kwinFile(),
        QStringLiteral("--group"), QStringLiteral("ModifierOnlyShortcuts"),
        QStringLiteral("--key"), QStringLiteral("Meta"),
        QStringLiteral("--delete")
    }, 10000);

    CommandResult writeShortcut;
    if (shortcut == QStringLiteral("Meta")) {
        writeShortcut = runCommand(kwriteconfig, {
            QStringLiteral("--file"), shortcutsFile(),
            QStringLiteral("--group"), QStringLiteral("plasmashell"),
            QStringLiteral("--key"), QStringLiteral("activate application launcher"),
            shortcutValueFor(QStringLiteral("Alt+F1"))
        }, 10000);
    } else {
        writeShortcut = runCommand(kwriteconfig, {
            QStringLiteral("--file"), shortcutsFile(),
            QStringLiteral("--group"), QStringLiteral("plasmashell"),
            QStringLiteral("--key"), QStringLiteral("activate application launcher"),
            shortcutValueFor(shortcut)
        }, 10000);
    }

    setBusy(false);

    if (!writeShortcut.started || !writeShortcut.finished || writeShortcut.exitCode != 0) {
        setStatus(writeShortcut.stdErr.isEmpty() ? QStringLiteral("Failed to update the launcher shortcut.") : writeShortcut.stdErr, QStringLiteral("error"));
        return;
    }

    refresh();
    setStatus(QStringLiteral("Launcher shortcut updated. Restart Plasma if the change does not appear immediately."), QStringLiteral("success"));
}

void PanelsKcm::resetLauncherLayout()
{
    QString helper = findExecutable({QStringLiteral("keskos-fix-launcher")});
    QStringList arguments;

    if (helper.isEmpty()) {
        helper = findExecutable({QStringLiteral("keskos-launcher-switch")});
        arguments << QStringLiteral("keskos");
    }

    if (helper.isEmpty()) {
        setStatus(QStringLiteral("No launcher repair helper was found on this system."), QStringLiteral("error"));
        return;
    }

    setBusy(true);
    const CommandResult result = runCommand(helper, arguments, 45000);
    setBusy(false);

    if (result.started && result.finished && result.exitCode == 0) {
        refresh();
        setStatus(QStringLiteral("KeskOS launcher wiring was restored."), QStringLiteral("success"));
        return;
    }

    setStatus(result.stdErr.isEmpty() ? QStringLiteral("Failed to reset the launcher layout.") : result.stdErr, QStringLiteral("error"));
}

void PanelsKcm::reapplyPanelLayout()
{
    const QString helper = findExecutable({QStringLiteral("keskos-reset-panel")});
    if (helper.isEmpty()) {
        setStatus(QStringLiteral("keskos-reset-panel was not found on this system."), QStringLiteral("error"));
        return;
    }

    setBusy(true);
    const CommandResult result = runCommand(helper, {}, 45000);
    setBusy(false);

    if (result.started && result.finished && result.exitCode == 0) {
        setStatus(QStringLiteral("Reapplied the KeskOS KDE panel layout."), QStringLiteral("success"));
        return;
    }

    setStatus(result.stdErr.isEmpty() ? QStringLiteral("Failed to reapply the KeskOS panel layout.") : result.stdErr, QStringLiteral("error"));
}

#include "panelskcm.moc"
