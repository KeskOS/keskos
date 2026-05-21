#pragma once

#include "keskmodulebase.h"

class AboutKcm : public KeskModuleBase
{
    Q_OBJECT

public:
    explicit AboutKcm(QObject *parent, const KPluginMetaData &data);

    Q_INVOKABLE void openWebsite();
    Q_INVOKABLE void openDocs();
    Q_INVOKABLE void openGitHub();
};
