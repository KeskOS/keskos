#pragma once

#include "keskmodulebase.h"

#include <QMap>

class BrowserKcm : public KeskModuleBase
{
    Q_OBJECT
    Q_PROPERTY(QString selectedBrowser READ selectedBrowser WRITE setSelectedBrowser NOTIFY stateChanged)
    Q_PROPERTY(QString selectedBrowserLabel READ selectedBrowserLabel NOTIFY stateChanged)
    Q_PROPERTY(QString selectedStatusText READ selectedStatusText NOTIFY stateChanged)
    Q_PROPERTY(QString packageName READ packageName NOTIFY stateChanged)
    Q_PROPERTY(QString currentDefaultLabel READ currentDefaultLabel NOTIFY stateChanged)
    Q_PROPERTY(bool selectedInstalled READ selectedInstalled NOTIFY stateChanged)
    Q_PROPERTY(bool selectedAvailable READ selectedAvailable NOTIFY stateChanged)
    Q_PROPERTY(bool homepageAssetsAvailable READ homepageAssetsAvailable NOTIFY stateChanged)
    Q_PROPERTY(bool canOpenHomepageSettings READ canOpenHomepageSettings NOTIFY stateChanged)

public:
    struct BrowserEntry {
        QString key;
        QString label;
        QString desktopId;
        QString packageName;
        QString executable;
        bool installed = false;
        bool available = false;
        bool currentDefault = false;
        bool homepageAssetsAvailable = false;
    };

    explicit BrowserKcm(QObject *parent, const KPluginMetaData &data);

    QString selectedBrowser() const;
    void setSelectedBrowser(const QString &browserKey);

    QString selectedBrowserLabel() const;
    QString selectedStatusText() const;
    QString packageName() const;
    QString currentDefaultLabel() const;
    bool selectedInstalled() const;
    bool selectedAvailable() const;
    bool homepageAssetsAvailable() const;
    bool canOpenHomepageSettings() const;

    Q_INVOKABLE void refresh();
    Q_INVOKABLE void setDefaultBrowser();
    Q_INVOKABLE void installSelectedBrowser();
    Q_INVOKABLE void applyTheme(bool includeHomepage);
    Q_INVOKABLE void resetBrowserDefaults();
    Q_INVOKABLE void openHomepageSettings();

Q_SIGNALS:
    void stateChanged();

private:
    BrowserEntry browserEntry() const;
    QString helperPath() const;
    bool runJsonAction(const QStringList &arguments, QString *messageOut = nullptr, bool *okOut = nullptr);

    QMap<QString, BrowserEntry> m_entries;
    QString m_selectedBrowser = QStringLiteral("librewolf");
};
