#include "versionkcm.h"

#include <KPluginFactory>

#include <QDir>
#include <QFile>
#include <QTextStream>
#include <QVariantMap>

K_PLUGIN_CLASS_WITH_JSON(VersionKcm, "kcm_keskos_version.json")

namespace
{
QString firstLineOf(const QString &path)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return {};
    }

    QTextStream stream(&file);
    return stream.readLine().trimmed();
}

QString firstValue(const QString &text, const QString &prefix)
{
    const QStringList lines = text.split(u'\n', Qt::SkipEmptyParts);
    for (const QString &line : lines) {
        if (line.trimmed().startsWith(prefix)) {
            return line.section(u':', 1).trimmed();
        }
    }
    return {};
}

QString graphicsPlatform()
{
    const QString sessionType = qEnvironmentVariable("XDG_SESSION_TYPE").trimmed();
    if (sessionType.compare(QStringLiteral("wayland"), Qt::CaseInsensitive) == 0) {
        return QStringLiteral("Wayland");
    }
    if (sessionType.compare(QStringLiteral("x11"), Qt::CaseInsensitive) == 0) {
        return QStringLiteral("X11");
    }
    return sessionType.isEmpty() ? QStringLiteral("unavailable") : sessionType;
}
}

VersionKcm::VersionKcm(QObject *parent, const KPluginMetaData &data)
    : KeskModuleBase(parent, data)
{
    refresh();
}

QVariantList VersionKcm::infoEntries() const
{
    return m_infoEntries;
}

void VersionKcm::refresh()
{
    const QMap<QString, QString> osRelease = readKeyValueFile(QStringLiteral("/etc/os-release"));
    const QMap<QString, QString> keskRelease = readKeyValueFile(QStringLiteral("/etc/kesk-release"));
    const QMap<QString, QString> keskVersion = readKeyValueFile(QStringLiteral("/usr/share/kesk/version"));
    const QString rawVersionLine = firstLineOf(QStringLiteral("/usr/share/kesk/version"));

    const QString versionName =
        osRelease.value(QStringLiteral("PRETTY_NAME"),
        keskRelease.value(QStringLiteral("PRETTY_NAME"),
        keskRelease.value(QStringLiteral("NAME"),
        keskVersion.value(QStringLiteral("PRETTY_NAME"),
        rawVersionLine.isEmpty() ? QStringLiteral("unknown") : rawVersionLine))));

    const QString buildLayer =
        osRelease.value(QStringLiteral("BUILD_ID"),
        keskRelease.value(QStringLiteral("BUILD_ID"),
        keskRelease.value(QStringLiteral("LAYER"),
        keskVersion.value(QStringLiteral("BUILD_ID"),
        keskVersion.value(QStringLiteral("VERSION"), QStringLiteral("unknown"))))));

    const QString updateChannel = osRelease.value(QStringLiteral("BUILD_ID"), QStringLiteral("unavailable"));
    const QString isoBuildDate =
        osRelease.value(QStringLiteral("BUILD_DATE"),
        osRelease.value(QStringLiteral("IMAGE_BUILD_DATE"),
        keskRelease.value(QStringLiteral("BUILD_DATE"), QStringLiteral("unavailable"))));

    QString gitCommit = QStringLiteral("unavailable");
    const QStringList sourceRoots = {
        QDir::homePath() + QStringLiteral("/.local/share/keskos/source"),
        QStringLiteral("/usr/local/share/keskos/source"),
        QStringLiteral("/usr/share/keskos/source")
    };
    const QString git = findExecutable({QStringLiteral("git")});
    if (!git.isEmpty()) {
        for (const QString &sourceRoot : sourceRoots) {
            if (!QFile::exists(sourceRoot + QStringLiteral("/.git"))) {
                continue;
            }
            const CommandResult gitResult = runCommand(git, {QStringLiteral("-C"), sourceRoot, QStringLiteral("rev-parse"), QStringLiteral("--short"), QStringLiteral("HEAD")}, 10000);
            if (gitResult.started && gitResult.finished && gitResult.exitCode == 0 && !gitResult.stdOut.isEmpty()) {
                gitCommit = gitResult.stdOut;
                break;
            }
        }
    }

    const QString uname = findExecutable({QStringLiteral("uname")});
    const QString kernel = uname.isEmpty() ? QStringLiteral("unavailable") : runCommand(uname, {QStringLiteral("-r")}, 5000).stdOut;

    const QString plasmashell = findExecutable({QStringLiteral("plasmashell")});
    const QString plasmaVersion = plasmashell.isEmpty() ? QStringLiteral("unavailable") : runCommand(plasmashell, {QStringLiteral("--version")}, 10000).stdOut;

    const QString kfconfig = findExecutable({QStringLiteral("kf6-config")});
    const QString frameworksVersion = kfconfig.isEmpty() ? QStringLiteral("unavailable") : runCommand(kfconfig, {QStringLiteral("--version")}, 10000).stdOut;

    const QString lscpu = findExecutable({QStringLiteral("lscpu")});
    const QString cpuText = lscpu.isEmpty() ? QString() : runCommand(lscpu, {}, 10000).stdOut;
    const QString cpuModel = cpuText.isEmpty() ? QStringLiteral("unavailable") : firstValue(cpuText, QStringLiteral("Model name"));

    const QString freeCmd = findExecutable({QStringLiteral("free")});
    const QString freeText = freeCmd.isEmpty() ? QString() : runCommand(freeCmd, {QStringLiteral("-h")}, 10000).stdOut;
    QString ram = QStringLiteral("unavailable");
    for (const QString &line : freeText.split(u'\n', Qt::SkipEmptyParts)) {
        if (line.trimmed().startsWith(QStringLiteral("Mem:"))) {
            const QStringList parts = line.simplified().split(u' ');
            if (parts.size() >= 2) {
                ram = parts.at(1);
            }
            break;
        }
    }

    const QString df = findExecutable({QStringLiteral("df")});
    const QString dfText = df.isEmpty() ? QString() : runCommand(df, {QStringLiteral("-h"), QStringLiteral("/")}, 10000).stdOut;
    QString disk = QStringLiteral("unavailable");
    const QStringList dfLines = dfText.split(u'\n', Qt::SkipEmptyParts);
    if (dfLines.size() >= 2) {
        const QStringList parts = dfLines.at(1).simplified().split(u' ');
        if (parts.size() >= 5) {
            disk = QStringLiteral("%1 total, %2 used, %3 available").arg(parts.at(1), parts.at(2), parts.at(3));
        }
    }

    const QString lspci = findExecutable({QStringLiteral("lspci")});
    const QString lspciText = lspci.isEmpty() ? QString() : runCommand(lspci, {}, 10000).stdOut;
    QString gpu = QStringLiteral("unavailable");
    for (const QString &line : lspciText.split(u'\n', Qt::SkipEmptyParts)) {
        if (line.contains(QStringLiteral("VGA compatible controller")) ||
            line.contains(QStringLiteral("3D controller")) ||
            line.contains(QStringLiteral("Display controller"))) {
            gpu = line.section(QStringLiteral(": "), 1);
            break;
        }
    }

    QVariantList nextEntries;
    const auto addEntry = [&nextEntries](const QString &label, const QString &value) {
        nextEntries.append(QVariantMap{
            {QStringLiteral("label"), label},
            {QStringLiteral("value"), value.isEmpty() ? QStringLiteral("unavailable") : value}
        });
    };

    addEntry(QStringLiteral("KeskOS version"), versionName);
    addEntry(QStringLiteral("Layer/build version"), buildLayer);
    addEntry(QStringLiteral("ISO build date"), isoBuildDate);
    addEntry(QStringLiteral("Git commit/build ID"), gitCommit);
    addEntry(QStringLiteral("Update channel"), updateChannel);
    addEntry(QStringLiteral("Base system"), osRelease.value(QStringLiteral("NAME"), QStringLiteral("Arch Linux")));
    addEntry(QStringLiteral("Kernel version"), kernel);
    addEntry(QStringLiteral("KDE Plasma version"), plasmaVersion);
    addEntry(QStringLiteral("KDE Frameworks version"), frameworksVersion);
    addEntry(QStringLiteral("Qt version"), QString::fromLatin1(qVersion()));
    addEntry(QStringLiteral("Graphics platform"), graphicsPlatform());
    addEntry(QStringLiteral("CPU"), cpuModel);
    addEntry(QStringLiteral("GPU"), gpu);
    addEntry(QStringLiteral("RAM"), ram);
    addEntry(QStringLiteral("Disk"), disk);

    m_infoEntries = nextEntries;
    Q_EMIT infoChanged();
}

void VersionKcm::openWebsite()
{
    openExternalUrl(QStringLiteral("https://keskos.org"), QStringLiteral("Could not open browser. Visit https://keskos.org manually."));
}

void VersionKcm::openDocs()
{
    openExternalUrl(QStringLiteral("https://docs.keskos.org"), QStringLiteral("Could not open browser. Visit https://docs.keskos.org manually."));
}

void VersionKcm::openGitHub()
{
    openExternalUrl(QStringLiteral("https://github.com/memegeko/keskos"), QStringLiteral("Could not open browser. Visit https://github.com/memegeko/keskos manually."));
}

#include "versionkcm.moc"
