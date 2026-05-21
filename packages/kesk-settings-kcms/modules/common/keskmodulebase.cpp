#include "keskmodulebase.h"

#include <QFile>
#include <QProcess>
#include <QSettings>
#include <QStandardPaths>
#include <QTextStream>

KeskModuleBase::KeskModuleBase(QObject *parent, const KPluginMetaData &data)
    : KQuickConfigModule(parent, data)
{
    setButtons({});
}

QString KeskModuleBase::statusMessage() const
{
    return m_statusMessage;
}

QString KeskModuleBase::statusLevel() const
{
    return m_statusLevel;
}

bool KeskModuleBase::busy() const
{
    return m_busy;
}

void KeskModuleBase::clearStatus()
{
    if (m_statusMessage.isEmpty() && m_statusLevel.isEmpty()) {
        return;
    }

    m_statusMessage.clear();
    m_statusLevel.clear();
    Q_EMIT statusChanged();
}

void KeskModuleBase::setStatus(const QString &message, const QString &level)
{
    if (m_statusMessage == message && m_statusLevel == level) {
        return;
    }

    m_statusMessage = message;
    m_statusLevel = level;
    Q_EMIT statusChanged();
}

void KeskModuleBase::setBusy(bool busy)
{
    if (m_busy == busy) {
        return;
    }

    m_busy = busy;
    Q_EMIT busyChanged();
}

QString KeskModuleBase::findExecutable(const QStringList &names)
{
    for (const QString &name : names) {
        const QString resolved = QStandardPaths::findExecutable(name);
        if (!resolved.isEmpty()) {
            return resolved;
        }
    }

    return {};
}

bool KeskModuleBase::commandExists(const QString &command)
{
    return !QStandardPaths::findExecutable(command).isEmpty();
}

QString KeskModuleBase::readIniValue(const QStringList &paths, const QString &group, const QString &key)
{
    for (const QString &path : paths) {
        if (path.isEmpty() || !QFile::exists(path)) {
            continue;
        }

        QSettings settings(path, QSettings::IniFormat);
        settings.beginGroup(group);
        const QString value = settings.value(key).toString().trimmed();
        settings.endGroup();
        if (!value.isEmpty()) {
            return value;
        }
    }

    return {};
}

QMap<QString, QString> KeskModuleBase::readKeyValueFile(const QString &path)
{
    QMap<QString, QString> values;
    QFile file(path);

    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return values;
    }

    QTextStream stream(&file);
    while (!stream.atEnd()) {
        const QString line = stream.readLine().trimmed();
        if (line.isEmpty() || line.startsWith(u'#')) {
            continue;
        }

        const int separator = line.indexOf(u'=');
        if (separator <= 0) {
            continue;
        }

        const QString key = line.left(separator).trimmed();
        QString value = line.mid(separator + 1).trimmed();
        if (value.startsWith(u'"') && value.endsWith(u'"') && value.size() >= 2) {
            value = value.mid(1, value.size() - 2);
        }
        values.insert(key, value);
    }

    return values;
}

KeskModuleBase::CommandResult KeskModuleBase::runCommand(const QString &program, const QStringList &arguments, int timeoutMs) const
{
    CommandResult result;

    if (program.isEmpty()) {
        result.stdErr = QStringLiteral("Executable was not found.");
        return result;
    }

    QProcess process;
    process.start(program, arguments);
    if (!process.waitForStarted(5000)) {
        result.stdErr = process.errorString();
        return result;
    }

    result.started = true;
    if (!process.waitForFinished(timeoutMs)) {
        result.timedOut = true;
        process.kill();
        process.waitForFinished(2000);
    } else {
        result.finished = true;
    }

    result.exitCode = process.exitCode();
    result.stdOut = QString::fromUtf8(process.readAllStandardOutput()).trimmed();
    result.stdErr = QString::fromUtf8(process.readAllStandardError()).trimmed();
    return result;
}

bool KeskModuleBase::openExternalUrl(const QString &url, const QString &failureMessage)
{
    const QString xdgOpen = findExecutable({QStringLiteral("xdg-open")});
    if (xdgOpen.isEmpty()) {
        setStatus(failureMessage, QStringLiteral("error"));
        return false;
    }

    QProcess process;
    process.start(xdgOpen, {url});
    if (!process.waitForStarted(5000)) {
        setStatus(failureMessage, QStringLiteral("error"));
        return false;
    }

    if (!process.waitForFinished(8000)) {
        setStatus(QStringLiteral("Opened %1").arg(url), QStringLiteral("success"));
        return true;
    }

    if (process.exitStatus() == QProcess::NormalExit && process.exitCode() == 0) {
        setStatus(QStringLiteral("Opened %1").arg(url), QStringLiteral("success"));
        return true;
    }

    setStatus(failureMessage, QStringLiteral("error"));
    return false;
}

bool KeskModuleBase::startDetachedCommand(const QString &program, const QStringList &arguments) const
{
    if (program.isEmpty()) {
        return false;
    }

    return QProcess::startDetached(program, arguments);
}
