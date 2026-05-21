#pragma once

#include "keskmodulebase.h"

class ThemeKcm : public KeskModuleBase
{
    Q_OBJECT
    Q_PROPERTY(QString currentAccentColor READ currentAccentColor NOTIFY stateChanged)
    Q_PROPERTY(QString currentMode READ currentMode NOTIFY stateChanged)

public:
    explicit ThemeKcm(QObject *parent, const KPluginMetaData &data);

    QString currentAccentColor() const;
    QString currentMode() const;

    Q_INVOKABLE void refresh();
    Q_INVOKABLE void applyKeskTheme();
    Q_INVOKABLE void applyKdeDefaults();
    Q_INVOKABLE void resetKeskTheme();

Q_SIGNALS:
    void stateChanged();

private:
    QString m_currentAccentColor = QStringLiteral("#ce6a35");
    QString m_currentMode = QStringLiteral("KeskOS Orange");
};
