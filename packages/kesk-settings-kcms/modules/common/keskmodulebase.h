#pragma once

#include <KQuickConfigModule>

#include <QMap>
#include <QString>
#include <QStringList>

class KeskModuleBase : public KQuickConfigModule
{
    Q_OBJECT
    Q_PROPERTY(QString statusMessage READ statusMessage NOTIFY statusChanged)
    Q_PROPERTY(QString statusLevel READ statusLevel NOTIFY statusChanged)
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)

public:
    struct CommandResult {
        bool started = false;
        bool finished = false;
        bool timedOut = false;
        int exitCode = -1;
        QString stdOut;
        QString stdErr;
    };

    explicit KeskModuleBase(QObject *parent, const KPluginMetaData &data);

    QString statusMessage() const;
    QString statusLevel() const;
    bool busy() const;

    Q_INVOKABLE void clearStatus();

Q_SIGNALS:
    void statusChanged();
    void busyChanged();

protected:
    void setStatus(const QString &message, const QString &level);
    void setBusy(bool busy);

    static QString findExecutable(const QStringList &names);
    static bool commandExists(const QString &command);
    static QString readIniValue(const QStringList &paths, const QString &group, const QString &key);
    static QMap<QString, QString> readKeyValueFile(const QString &path);

    CommandResult runCommand(const QString &program, const QStringList &arguments = {}, int timeoutMs = 30000) const;
    bool openExternalUrl(const QString &url, const QString &failureMessage);
    bool startDetachedCommand(const QString &program, const QStringList &arguments = {}) const;

private:
    QString m_statusMessage;
    QString m_statusLevel;
    bool m_busy = false;
};
