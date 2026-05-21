#include "themekcm.h"

#include <KPluginFactory>

#include <QDir>

K_PLUGIN_CLASS_WITH_JSON(ThemeKcm, "kcm_keskos_theme.json")

namespace
{
QString kdeGlobalsPath()
{
    return QDir::homePath() + QStringLiteral("/.config/kdeglobals");
}

QString systemKdeGlobalsPath()
{
    return QStringLiteral("/etc/xdg/kdeglobals");
}
}

ThemeKcm::ThemeKcm(QObject *parent, const KPluginMetaData &data)
    : KeskModuleBase(parent, data)
{
    refresh();
}

QString ThemeKcm::currentAccentColor() const
{
    return m_currentAccentColor;
}

QString ThemeKcm::currentMode() const
{
    return m_currentMode;
}

void ThemeKcm::refresh()
{
    const QString colorScheme = readIniValue({kdeGlobalsPath(), systemKdeGlobalsPath()}, QStringLiteral("General"), QStringLiteral("ColorScheme"));
    const QString accent = readIniValue({kdeGlobalsPath(), systemKdeGlobalsPath()}, QStringLiteral("General"), QStringLiteral("AccentColor"));

    const QString nextMode = colorScheme == QStringLiteral("KeskOSDark")
        ? QStringLiteral("KeskOS Orange")
        : QStringLiteral("KDE Defaults");
    const QString nextAccent = accent.isEmpty() ? QStringLiteral("#ce6a35") : accent;

    if (m_currentMode != nextMode || m_currentAccentColor != nextAccent) {
        m_currentMode = nextMode;
        m_currentAccentColor = nextAccent;
        Q_EMIT stateChanged();
    }
}

void ThemeKcm::applyKeskTheme()
{
    const QString helper = findExecutable({QStringLiteral("kesk-apply-theme")});
    if (helper.isEmpty()) {
        setStatus(QStringLiteral("kesk-apply-theme was not found on this system."), QStringLiteral("error"));
        return;
    }

    setBusy(true);
    const CommandResult result = runCommand(helper);
    setBusy(false);

    if (result.started && result.finished && result.exitCode == 0) {
        refresh();
        setStatus(QStringLiteral("Applied the KeskOS Orange theme stack."), QStringLiteral("success"));
        return;
    }

    setStatus(result.stdErr.isEmpty() ? QStringLiteral("Failed to apply the KeskOS theme.") : result.stdErr, QStringLiteral("error"));
}

void ThemeKcm::applyKdeDefaults()
{
    const QString helper = findExecutable({QStringLiteral("kesk-apply-kde-defaults")});
    if (helper.isEmpty()) {
        setStatus(QStringLiteral("kesk-apply-kde-defaults was not found on this system."), QStringLiteral("error"));
        return;
    }

    setBusy(true);
    const CommandResult result = runCommand(helper);
    setBusy(false);

    if (result.started && result.finished && result.exitCode == 0) {
        refresh();
        setStatus(QStringLiteral("Restored KDE defaults where supported."), QStringLiteral("success"));
        return;
    }

    setStatus(result.stdErr.isEmpty() ? QStringLiteral("Failed to restore KDE defaults.") : result.stdErr, QStringLiteral("error"));
}

void ThemeKcm::resetKeskTheme()
{
    applyKeskTheme();
}

#include "themekcm.moc"
