#pragma once

#include "keskmodulebase.h"

#include <QVariantList>

class VersionKcm : public KeskModuleBase
{
    Q_OBJECT
    Q_PROPERTY(QVariantList infoEntries READ infoEntries NOTIFY infoChanged)

public:
    explicit VersionKcm(QObject *parent, const KPluginMetaData &data);

    QVariantList infoEntries() const;

    Q_INVOKABLE void refresh();
    Q_INVOKABLE void openWebsite();
    Q_INVOKABLE void openDocs();
    Q_INVOKABLE void openGitHub();

Q_SIGNALS:
    void infoChanged();

private:
    QVariantList m_infoEntries;
};
