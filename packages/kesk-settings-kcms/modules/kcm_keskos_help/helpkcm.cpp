#include "helpkcm.h"

#include <KPluginFactory>

K_PLUGIN_CLASS_WITH_JSON(HelpKcm, "kcm_keskos_help.json")

HelpKcm::HelpKcm(QObject *parent, const KPluginMetaData &data)
    : KeskModuleBase(parent, data)
{
}

void HelpKcm::openDocs()
{
    openExternalUrl(QStringLiteral("https://docs.keskos.org"), QStringLiteral("Could not open browser. Visit https://docs.keskos.org manually."));
}

#include "helpkcm.moc"
