#include "bootsplashkcm.h"

#include <KPluginFactory>

#include <QFileInfo>

K_PLUGIN_CLASS_WITH_JSON(BootSplashKcm, "kcm_keskos_bootsplash.json")

BootSplashKcm::BootSplashKcm(QObject *parent, const KPluginMetaData &data)
    : KeskModuleBase(parent, data)
{
    refresh();
}

bool BootSplashKcm::plymouthInstalled() const
{
    return m_plymouthInstalled;
}

bool BootSplashKcm::themeInstalled() const
{
    return m_themeInstalled;
}

QString BootSplashKcm::currentTheme() const
{
    return m_currentTheme;
}

void BootSplashKcm::refresh()
{
    const bool nextPlymouthInstalled =
        commandExists(QStringLiteral("plymouth")) ||
        commandExists(QStringLiteral("plymouth-set-default-theme")) ||
        QFileInfo::exists(QStringLiteral("/usr/bin/plymouth-set-default-theme"));

    const bool nextThemeInstalled =
        QFileInfo::exists(QStringLiteral("/usr/share/plymouth/themes/KeskOS")) ||
        QFileInfo::exists(QStringLiteral("/usr/share/plymouth/themes/keskos"));

    QString nextTheme = readIniValue({QStringLiteral("/etc/plymouth/plymouthd.conf")}, QStringLiteral("Daemon"), QStringLiteral("Theme"));
    if (nextTheme.isEmpty()) {
        nextTheme = QStringLiteral("unavailable");
    }

    if (m_plymouthInstalled != nextPlymouthInstalled || m_themeInstalled != nextThemeInstalled || m_currentTheme != nextTheme) {
        m_plymouthInstalled = nextPlymouthInstalled;
        m_themeInstalled = nextThemeInstalled;
        m_currentTheme = nextTheme;
        Q_EMIT stateChanged();
    }
}

void BootSplashKcm::openDocs()
{
    openExternalUrl(QStringLiteral("https://docs.keskos.org"), QStringLiteral("Could not open browser. Visit https://docs.keskos.org manually."));
}

#include "bootsplashkcm.moc"
