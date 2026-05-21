#include "topbarkcm.h"

#include <KPluginFactory>

#include <QDir>
#include <QFileInfo>

K_PLUGIN_CLASS_WITH_JSON(TopBarKcm, "kcm_keskos_topbar.json")

namespace
{
bool quickshellConfigExists()
{
    const QString home = QDir::homePath();
    const QStringList candidates = {
        home + QStringLiteral("/.config/quickshell/keskos/shell.qml"),
        QStringLiteral("/usr/local/share/keskos/source/configs/quickshell/keskos/shell.qml"),
        QStringLiteral("/usr/share/keskos/source/configs/quickshell/keskos/shell.qml")
    };

    for (const QString &candidate : candidates) {
        if (QFileInfo::exists(candidate)) {
            return true;
        }
    }

    return false;
}
}

TopBarKcm::TopBarKcm(QObject *parent, const KPluginMetaData &data)
    : KeskModuleBase(parent, data)
{
    refresh();
}

bool TopBarKcm::backendConnected() const
{
    return m_backendConnected;
}

bool TopBarKcm::canRestart() const
{
    return m_canRestart;
}

bool TopBarKcm::canReset() const
{
    return m_canReset;
}

void TopBarKcm::refresh()
{
    const bool connected = commandExists(QStringLiteral("quickshell")) && quickshellConfigExists();
    const bool restartAvailable = connected && !findExecutable({QStringLiteral("keskos-shell")}).isEmpty();
    const bool resetAvailable = !findExecutable({QStringLiteral("keskos-configure-user")}).isEmpty();

    if (m_backendConnected != connected || m_canRestart != restartAvailable || m_canReset != resetAvailable) {
        m_backendConnected = connected;
        m_canRestart = restartAvailable;
        m_canReset = resetAvailable;
        Q_EMIT stateChanged();
    }
}

void TopBarKcm::restartWidgets()
{
    const QString helper = findExecutable({QStringLiteral("keskos-shell")});
    if (helper.isEmpty() || !commandExists(QStringLiteral("quickshell"))) {
        setStatus(QStringLiteral("The current top bar widget backend is not available."), QStringLiteral("error"));
        return;
    }

    setBusy(true);
    const QString pkill = findExecutable({QStringLiteral("pkill")});
    if (!pkill.isEmpty()) {
        runCommand(pkill, {QStringLiteral("-x"), QStringLiteral("quickshell")}, 5000);
    }

    const bool started = startDetachedCommand(helper);
    setBusy(false);

    if (started) {
        setStatus(QStringLiteral("Restarted the KeskOS top bar widget backend."), QStringLiteral("success"));
        return;
    }

    setStatus(QStringLiteral("Could not restart the top bar widget backend."), QStringLiteral("error"));
}

void TopBarKcm::resetWidgets()
{
    const QString helper = findExecutable({QStringLiteral("keskos-configure-user")});
    if (helper.isEmpty()) {
        setStatus(QStringLiteral("keskos-configure-user was not found on this system."), QStringLiteral("error"));
        return;
    }

    setBusy(true);
    const QString currentUser = qEnvironmentVariable("USER");
    const CommandResult result = currentUser.isEmpty()
        ? runCommand(helper, {QStringLiteral("--force")}, 60000)
        : runCommand(helper, {QStringLiteral("--user"), currentUser, QStringLiteral("--force")}, 60000);
    setBusy(false);

    if (result.started && result.finished && result.exitCode == 0) {
        setStatus(QStringLiteral("Reapplied the current KeskOS top bar widget configuration."), QStringLiteral("success"));
        return;
    }

    setStatus(result.stdErr.isEmpty() ? QStringLiteral("Failed to reset the top bar widget configuration.") : result.stdErr, QStringLiteral("error"));
}

#include "topbarkcm.moc"
