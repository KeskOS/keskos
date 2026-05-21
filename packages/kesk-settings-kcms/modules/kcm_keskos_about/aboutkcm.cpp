#include "aboutkcm.h"

#include <KPluginFactory>

K_PLUGIN_CLASS_WITH_JSON(AboutKcm, "kcm_keskos_about.json")

namespace
{
constexpr auto WEBSITE_URL = "https://keskos.org";
constexpr auto DOCS_URL = "https://docs.keskos.org";
constexpr auto GITHUB_URL = "https://github.com/memegeko/keskos";
}

AboutKcm::AboutKcm(QObject *parent, const KPluginMetaData &data)
    : KeskModuleBase(parent, data)
{
}

void AboutKcm::openWebsite()
{
    openExternalUrl(QString::fromLatin1(WEBSITE_URL), QStringLiteral("Could not open browser. Visit https://keskos.org manually."));
}

void AboutKcm::openDocs()
{
    openExternalUrl(QString::fromLatin1(DOCS_URL), QStringLiteral("Could not open browser. Visit https://docs.keskos.org manually."));
}

void AboutKcm::openGitHub()
{
    openExternalUrl(QString::fromLatin1(GITHUB_URL), QStringLiteral("Could not open browser. Visit https://github.com/memegeko/keskos manually."));
}

#include "aboutkcm.moc"
