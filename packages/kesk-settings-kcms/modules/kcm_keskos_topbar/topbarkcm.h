#pragma once

#include "keskmodulebase.h"

class TopBarKcm : public KeskModuleBase
{
    Q_OBJECT
    Q_PROPERTY(bool backendConnected READ backendConnected NOTIFY stateChanged)
    Q_PROPERTY(bool canRestart READ canRestart NOTIFY stateChanged)
    Q_PROPERTY(bool canReset READ canReset NOTIFY stateChanged)

public:
    explicit TopBarKcm(QObject *parent, const KPluginMetaData &data);

    bool backendConnected() const;
    bool canRestart() const;
    bool canReset() const;

    Q_INVOKABLE void refresh();
    Q_INVOKABLE void restartWidgets();
    Q_INVOKABLE void resetWidgets();

Q_SIGNALS:
    void stateChanged();

private:
    bool m_backendConnected = false;
    bool m_canRestart = false;
    bool m_canReset = false;
};
