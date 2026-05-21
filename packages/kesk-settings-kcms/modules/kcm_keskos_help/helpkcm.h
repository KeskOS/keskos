#pragma once

#include "keskmodulebase.h"

class HelpKcm : public KeskModuleBase
{
    Q_OBJECT

public:
    explicit HelpKcm(QObject *parent, const KPluginMetaData &data);

    Q_INVOKABLE void openDocs();
};
