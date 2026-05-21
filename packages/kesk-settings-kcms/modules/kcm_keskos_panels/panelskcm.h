#pragma once

#include "keskmodulebase.h"

class PanelsKcm : public KeskModuleBase
{
    Q_OBJECT
    Q_PROPERTY(QString currentLauncherShortcut READ currentLauncherShortcut NOTIFY stateChanged)

public:
    explicit PanelsKcm(QObject *parent, const KPluginMetaData &data);

    QString currentLauncherShortcut() const;

    Q_INVOKABLE void refresh();
    Q_INVOKABLE void setLauncherShortcut(const QString &shortcut);
    Q_INVOKABLE void resetLauncherLayout();
    Q_INVOKABLE void reapplyPanelLayout();

Q_SIGNALS:
    void stateChanged();

private:
    QString m_currentLauncherShortcut = QStringLiteral("Meta");
};
