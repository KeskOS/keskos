#include "browserkcm.h"

#include <KPluginFactory>

#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

K_PLUGIN_CLASS_WITH_JSON(BrowserKcm, "kcm_keskos_browser.json")

BrowserKcm::BrowserKcm(QObject *parent, const KPluginMetaData &data)
    : KeskModuleBase(parent, data)
{
    refresh();
}

QString BrowserKcm::selectedBrowser() const
{
    return m_selectedBrowser;
}

void BrowserKcm::setSelectedBrowser(const QString &browserKey)
{
    if (browserKey.isEmpty() || m_selectedBrowser == browserKey) {
        return;
    }

    m_selectedBrowser = browserKey;
    Q_EMIT stateChanged();
}

BrowserKcm::BrowserEntry BrowserKcm::browserEntry() const
{
    return m_entries.value(m_selectedBrowser);
}

QString BrowserKcm::selectedBrowserLabel() const
{
    const BrowserEntry entry = browserEntry();
    return entry.label.isEmpty() ? QStringLiteral("Browser") : entry.label;
}

QString BrowserKcm::selectedStatusText() const
{
    const BrowserEntry entry = browserEntry();
    if (entry.installed) {
        return QStringLiteral("Installed");
    }
    if (entry.available) {
        return QStringLiteral("Not installed");
    }
    return QStringLiteral("Package unavailable");
}

QString BrowserKcm::packageName() const
{
    return browserEntry().packageName;
}

QString BrowserKcm::currentDefaultLabel() const
{
    for (const BrowserEntry &entry : m_entries) {
        if (entry.currentDefault) {
            return entry.label;
        }
    }
    return QStringLiteral("Unknown");
}

bool BrowserKcm::selectedInstalled() const
{
    return browserEntry().installed;
}

bool BrowserKcm::selectedAvailable() const
{
    return browserEntry().available;
}

bool BrowserKcm::homepageAssetsAvailable() const
{
    return browserEntry().homepageAssetsAvailable;
}

bool BrowserKcm::canOpenHomepageSettings() const
{
    const BrowserEntry entry = browserEntry();
    return entry.installed && !entry.executable.isEmpty();
}

QString BrowserKcm::helperPath() const
{
    return findExecutable({QStringLiteral("kesk-browser-settings")});
}

bool BrowserKcm::runJsonAction(const QStringList &arguments, QString *messageOut, bool *okOut)
{
    const QString helper = helperPath();
    if (helper.isEmpty()) {
        setStatus(QStringLiteral("kesk-browser-settings was not found on this system."), QStringLiteral("error"));
        if (okOut) {
            *okOut = false;
        }
        return false;
    }

    const CommandResult result = runCommand(helper, arguments, 45000);
    if (!result.started || !result.finished || result.exitCode != 0) {
        const QString message = result.stdErr.isEmpty() ? QStringLiteral("Browser helper command failed.") : result.stdErr;
        setStatus(message, QStringLiteral("error"));
        if (messageOut) {
            *messageOut = message;
        }
        if (okOut) {
            *okOut = false;
        }
        return false;
    }

    QJsonParseError parseError;
    const QJsonDocument document = QJsonDocument::fromJson(result.stdOut.toUtf8(), &parseError);
    if (document.isNull() || !document.isObject()) {
        const QString message = QStringLiteral("Browser helper returned invalid JSON.");
        setStatus(message, QStringLiteral("error"));
        if (messageOut) {
            *messageOut = message;
        }
        if (okOut) {
            *okOut = false;
        }
        return false;
    }

    const QJsonObject object = document.object();
    const QString message = object.value(QStringLiteral("message")).toString().trimmed();
    const bool ok = object.value(QStringLiteral("ok")).toBool(false);

    if (messageOut) {
        *messageOut = message;
    }
    if (okOut) {
        *okOut = ok;
    }

    return true;
}

void BrowserKcm::refresh()
{
    const QString helper = helperPath();
    if (helper.isEmpty()) {
        setStatus(QStringLiteral("kesk-browser-settings was not found on this system."), QStringLiteral("error"));
        return;
    }

    const CommandResult result = runCommand(helper, {QStringLiteral("status")}, 20000);
    if (!result.started || !result.finished || result.exitCode != 0) {
        setStatus(result.stdErr.isEmpty() ? QStringLiteral("Could not read browser status.") : result.stdErr, QStringLiteral("error"));
        return;
    }

    QJsonParseError parseError;
    const QJsonDocument document = QJsonDocument::fromJson(result.stdOut.toUtf8(), &parseError);
    if (document.isNull() || !document.isObject()) {
        setStatus(QStringLiteral("Browser status returned invalid JSON."), QStringLiteral("error"));
        return;
    }

    const QJsonArray browsers = document.object().value(QStringLiteral("browsers")).toArray();
    QMap<QString, BrowserEntry> nextEntries;
    for (const QJsonValue &value : browsers) {
        const QJsonObject object = value.toObject();
        BrowserEntry entry;
        entry.key = object.value(QStringLiteral("key")).toString();
        entry.label = object.value(QStringLiteral("label")).toString();
        entry.desktopId = object.value(QStringLiteral("desktop_id")).toString();
        entry.packageName = object.value(QStringLiteral("package_name")).toString();
        entry.executable = object.value(QStringLiteral("executable")).toString();
        entry.installed = object.value(QStringLiteral("installed")).toBool(false);
        entry.available = object.value(QStringLiteral("available")).toBool(false);
        entry.currentDefault = object.value(QStringLiteral("current_default")).toBool(false);
        entry.homepageAssetsAvailable = object.value(QStringLiteral("homepage_assets_available")).toBool(false);
        nextEntries.insert(entry.key, entry);
    }

    m_entries = nextEntries;
    if (!m_entries.contains(m_selectedBrowser) && !m_entries.isEmpty()) {
        m_selectedBrowser = m_entries.first().key;
    }

    Q_EMIT stateChanged();
}

void BrowserKcm::setDefaultBrowser()
{
    setBusy(true);
    QString message;
    bool ok = false;
    const bool ran = runJsonAction({QStringLiteral("set-default"), m_selectedBrowser}, &message, &ok);
    setBusy(false);
    if (!ran) {
        return;
    }

    refresh();
    setStatus(message.isEmpty() ? QStringLiteral("Updated the default browser.") : message, ok ? QStringLiteral("success") : QStringLiteral("error"));
}

void BrowserKcm::installSelectedBrowser()
{
    setBusy(true);
    QString message;
    bool ok = false;
    const bool ran = runJsonAction({QStringLiteral("install"), m_selectedBrowser}, &message, &ok);
    setBusy(false);
    if (!ran) {
        return;
    }

    setStatus(message.isEmpty() ? QStringLiteral("Started the browser install task.") : message, ok ? QStringLiteral("success") : QStringLiteral("error"));
}

void BrowserKcm::applyTheme(bool includeHomepage)
{
    setBusy(true);
    QString message;
    bool ok = false;
    const bool ran = runJsonAction({
        QStringLiteral("apply-theme"),
        m_selectedBrowser,
        QStringLiteral("--homepage"),
        includeHomepage ? QStringLiteral("yes") : QStringLiteral("no")
    }, &message, &ok);
    setBusy(false);
    if (!ran) {
        return;
    }

    setStatus(message.isEmpty() ? QStringLiteral("Applied the browser settings.") : message, ok ? QStringLiteral("success") : QStringLiteral("warning"));
}

void BrowserKcm::resetBrowserDefaults()
{
    setBusy(true);
    QString message;
    bool ok = false;
    const bool ran = runJsonAction({QStringLiteral("reset"), m_selectedBrowser}, &message, &ok);
    setBusy(false);
    if (!ran) {
        return;
    }

    setStatus(message.isEmpty() ? QStringLiteral("Reset browser defaults.") : message, ok ? QStringLiteral("success") : QStringLiteral("warning"));
}

void BrowserKcm::openHomepageSettings()
{
    const BrowserEntry entry = browserEntry();
    if (entry.executable.isEmpty()) {
        setStatus(QStringLiteral("This browser is not installed yet."), QStringLiteral("error"));
        return;
    }

    QString page = QStringLiteral("about:preferences#home");
    if (m_selectedBrowser == QStringLiteral("brave")) {
        page = QStringLiteral("brave://settings/getStarted");
    }

    if (startDetachedCommand(entry.executable, {page})) {
        setStatus(QStringLiteral("Opened %1 homepage settings.").arg(entry.label), QStringLiteral("success"));
        return;
    }

    setStatus(QStringLiteral("Could not open browser homepage settings."), QStringLiteral("error"));
}

#include "browserkcm.moc"
