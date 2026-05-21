#pragma once

#include "keskmodulebase.h"

class BootSplashKcm : public KeskModuleBase
{
    Q_OBJECT
    Q_PROPERTY(bool plymouthInstalled READ plymouthInstalled NOTIFY stateChanged)
    Q_PROPERTY(bool themeInstalled READ themeInstalled NOTIFY stateChanged)
    Q_PROPERTY(QString currentTheme READ currentTheme NOTIFY stateChanged)

public:
    explicit BootSplashKcm(QObject *parent, const KPluginMetaData &data);

    bool plymouthInstalled() const;
    bool themeInstalled() const;
    QString currentTheme() const;

    Q_INVOKABLE void refresh();
    Q_INVOKABLE void openDocs();

Q_SIGNALS:
    void stateChanged();

private:
    bool m_plymouthInstalled = false;
    bool m_themeInstalled = false;
    QString m_currentTheme = QStringLiteral("unavailable");
};
