#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected snippet not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_regex_once(path: Path, pattern: str, replacement: str, *, flags: int = re.MULTILINE | re.DOTALL) -> None:
    text = path.read_text(encoding="utf-8")
    updated_text, replacements = re.subn(pattern, lambda _: replacement, text, count=1, flags=flags)
    if replacements != 1:
        raise RuntimeError(f"expected regex snippet not found in {path}")
    path.write_text(updated_text, encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: keskos_calamares_ui.py <calamares-source-root>")

    root = Path(sys.argv[1]).resolve()

    replace_once(
        root / "src/calamares/CalamaresWindow.cpp",
        '    logoLabel->setFixedSize( 80, 80 );\n',
        '    logoLabel->setFixedSize( 56, 56 );\n',
    )
    replace_once(
        root / "src/calamares/CalamaresWindow.cpp",
        """    // %1 is the distribution name
    CALAMARES_RETRANSLATE( const auto* branding = Calamares::Branding::instance();
                           setWindowTitle( Calamares::Settings::instance()->isSetupMode()
                                               ? tr( "%1 Setup Program" ).arg( branding->productName() )
                                               : tr( "%1 Installer" ).arg( branding->productName() ) ); );
""",
        """    CALAMARES_RETRANSLATE( const auto* branding = Calamares::Branding::instance();
                           setWindowTitle( branding->productName() ); );
""",
    )

    replace_once(
        root / "src/calamares/progresstree/ProgressTreeDelegate.cpp",
        "static constexpr int const item_margin = 8;\n",
        "static constexpr int const item_margin = 6;\n",
    )
    replace_once(
        root / "src/calamares/progresstree/ProgressTreeDelegate.cpp",
        """static inline int
item_fontsize()
{
    return Calamares::defaultFontSize() + 4;
}
""",
        """static inline int
item_fontsize()
{
    return Calamares::defaultFontSize();
}
""",
    )
    replace_once(
        root / "src/calamares/progresstree/ProgressTreeDelegate.cpp",
        """static void
paintViewStep( QPainter* painter, const QStyleOptionViewItem& option, const QModelIndex& index )
{
    QRect textRect = option.rect.adjusted( item_margin, item_margin, -item_margin, -item_margin );
    QFont font = qApp->font();
    font.setPointSize( item_fontsize() );
    font.setBold( false );
    painter->setFont( font );

    if ( index.row() == index.data( Calamares::ViewManager::ProgressTreeItemCurrentIndex ).toInt() )
    {
        painter->setPen( Calamares::Branding::instance()->styleString( Calamares::Branding::SidebarTextCurrent ) );
        QString textHighlight
            = Calamares::Branding::instance()->styleString( Calamares::Branding::SidebarBackgroundCurrent );
        if ( textHighlight.isEmpty() )
        {
            painter->setBrush( CalamaresApplication::instance()->mainWindow()->palette().window() );
        }
        else
        {
            painter->setBrush( QColor( textHighlight ) );
        }
    }

    // Draw the text at least once. If it doesn't fit, then shrink the font
    // being used by 1 pt on each iteration, up to a maximum of maximumShrink
    // times. On each loop, we'll have to blank out the rectangle again, so this
    // is an expensive (in terms of drawing operations) thing to do.
    //
    // (The loop uses <= because the counter is incremented at the start).
    static constexpr int const maximumShrink = 4;
    int shrinkSteps = 0;
    do
    {
        painter->fillRect( option.rect, painter->brush().color() );
        shrinkSteps++;

        QRectF boundingBox;
        painter->drawText(
            textRect, Qt::AlignHCenter | Qt::AlignVCenter | Qt::TextSingleLine, index.data().toString(), &boundingBox );

        // The extra check here is to avoid the changing-font-size if we're not going to use
        // it in the next iteration of the loop anyway.
        if ( ( shrinkSteps <= maximumShrink ) && ( boundingBox.width() > textRect.width() ) )
        {
            font.setPointSize( item_fontsize() - shrinkSteps );
            painter->setFont( font );
        }
        else
        {
            break;  // It fits
        }
    } while ( shrinkSteps <= maximumShrink );
}
""",
        """static void
paintViewStep( QPainter* painter, const QStyleOptionViewItem& option, const QModelIndex& index )
{
    static constexpr int const leftPadding = 16;
    static constexpr int const rightPadding = 10;
    static constexpr int const activeBorderWidth = 2;

    const bool current = index.row() == index.data( Calamares::ViewManager::ProgressTreeItemCurrentIndex ).toInt();
    QRect fullRect = option.rect.adjusted( 0, 1, 0, -1 );
    QRect textRect = fullRect.adjusted(
        leftPadding + ( current ? activeBorderWidth + 6 : 0 ), item_margin, -rightPadding, -item_margin );

    QFont font = qApp->font();
    font.setPointSize( item_fontsize() );
    font.setBold( false );
    painter->setFont( font );

    const QColor baseBackground
        = QColor( Calamares::Branding::instance()->styleString( Calamares::Branding::SidebarBackground ) );
    const QColor activeBackground
        = QColor( Calamares::Branding::instance()->styleString( Calamares::Branding::SidebarBackgroundCurrent ) );
    const QColor inactiveText = QColor( Calamares::Branding::instance()->styleString( Calamares::Branding::SidebarText ) );
    const QColor activeText
        = QColor( Calamares::Branding::instance()->styleString( Calamares::Branding::SidebarTextCurrent ) );

    painter->fillRect( fullRect, current ? activeBackground : baseBackground );
    if ( current )
    {
        painter->fillRect( QRect( fullRect.left(), fullRect.top(), activeBorderWidth, fullRect.height() ), activeText );
    }
    painter->setPen( current ? activeText : inactiveText );
    const QString label
        = painter->fontMetrics().elidedText( index.data().toString(), Qt::ElideRight, textRect.width() );
    painter->drawText( textRect, Qt::AlignLeft | Qt::AlignVCenter | Qt::TextSingleLine, label );
}
""",
    )
    replace_once(
        root / "src/calamares/progresstree/ProgressTreeDelegate.cpp",
        """QSize
ProgressTreeDelegate::sizeHint( const QStyleOptionViewItem& option, const QModelIndex& index ) const
{
    if ( !index.isValid() )
    {
        return option.rect.size();
    }

    QFont font = qApp->font();

    font.setPointSize( item_fontsize() );
    QFontMetrics fm( font );
    int height = fm.height();

    height += 2 * item_margin;

    return QSize( option.rect.width(), height );
}
""",
        """QSize
ProgressTreeDelegate::sizeHint( const QStyleOptionViewItem& option, const QModelIndex& index ) const
{
    if ( !index.isValid() )
    {
        return option.rect.size();
    }

    QFont font = qApp->font();

    font.setPointSize( item_fontsize() );
    QFontMetrics fm( font );
    const int height = qMax( fm.height() + ( 2 * item_margin ), Calamares::defaultFontHeight() + 18 );

    return QSize( option.rect.width(), height );
}
""",
    )
    replace_once(
        root / "src/libcalamaresui/viewpages/Slideshow.cpp",
        """    m_qmlShow->setSizePolicy( QSizePolicy::Expanding, QSizePolicy::Expanding );
    m_qmlShow->setResizeMode( QQuickWidget::SizeRootObjectToView );
    m_qmlShow->engine()->addImportPath( Calamares::qmlModulesDir().absolutePath() );
""",
        """    m_qmlShow->setSizePolicy( QSizePolicy::Expanding, QSizePolicy::Expanding );
    m_qmlShow->setResizeMode( QQuickWidget::SizeRootObjectToView );
    m_qmlShow->setClearColor( Qt::black );
    m_qmlShow->engine()->addImportPath( Calamares::qmlModulesDir().absolutePath() );
""",
    )

    replace_once(
        root / "src/modules/packagechooser/PackageChooserPage.h",
        """#include <QAbstractItemModel>
#include <QWidget>
""",
        """#include <QAbstractItemModel>
#include <QStandardItemModel>
#include <QWidget>
""",
    )
    replace_once(
        root / "src/modules/packagechooser/PackageChooserPage.h",
        """private:
    Ui::PackageChooserPage* ui;
    PackageItem m_introduction;
};
""",
        """private:
    bool usesCheckList() const;

    Ui::PackageChooserPage* ui;
    PackageItem m_introduction;
    PackageChooserMode m_mode;
    QStandardItemModel* m_checkModel = nullptr;
};
""",
    )
    replace_once(
        root / "src/modules/packagechooser/PackageChooserPage.cpp",
        """#include <QLabel>
""",
        """#include <QLabel>
#include <QStandardItemModel>
""",
    )
    replace_once(
        root / "src/modules/packagechooser/PackageChooserPage.cpp",
        """PackageChooserPage::PackageChooserPage( PackageChooserMode mode, QWidget* parent )
    : QWidget( parent )
    , ui( new Ui::PackageChooserPage )
    , m_introduction( QString(),
                      QString(),
                      tr( "Package Selection" ),
                      tr( "Please pick a product from the list. The selected product will be installed." ) )
{
""",
        """PackageChooserPage::PackageChooserPage( PackageChooserMode mode, QWidget* parent )
    : QWidget( parent )
    , ui( new Ui::PackageChooserPage )
    , m_introduction( QString(),
                      QString(),
                      tr( "Package Selection" ),
                      tr( "Please pick a product from the list. The selected product will be installed." ) )
    , m_mode( mode )
{
""",
    )
    replace_once(
        root / "src/modules/packagechooser/PackageChooserPage.cpp",
        """    switch ( mode )
    {
    case PackageChooserMode::Optional:
        [[fallthrough]];
    case PackageChooserMode::Required:
        ui->products->setSelectionMode( QAbstractItemView::SingleSelection );
        break;
    case PackageChooserMode::OptionalMultiple:
        [[fallthrough]];
    case PackageChooserMode::RequiredMultiple:
        ui->products->setSelectionMode( QAbstractItemView::ExtendedSelection );
    }
""",
        """    switch ( mode )
    {
    case PackageChooserMode::Optional:
        [[fallthrough]];
    case PackageChooserMode::Required:
        ui->products->setSelectionMode( QAbstractItemView::SingleSelection );
        break;
    case PackageChooserMode::OptionalMultiple:
        [[fallthrough]];
    case PackageChooserMode::RequiredMultiple:
        ui->products->setSelectionMode( QAbstractItemView::SingleSelection );
        ui->products->setEditTriggers( QAbstractItemView::NoEditTriggers );
        break;
    }
""",
    )
    replace_once(
        root / "src/modules/packagechooser/PackageChooserPage.cpp",
        """}

void
PackageChooserPage::currentChanged( const QModelIndex& index )
{
    if ( !index.isValid() || !ui->products->selectionModel()->hasSelection() )
    {
        ui->productName->setText( m_introduction.name.get() );
        ui->productScreenshot->setPixmap( m_introduction.screenshot );
        ui->productDescription->setText( m_introduction.description.get() );
    }
    else
    {
        const auto* model = ui->products->model();

        ui->productName->setText( model->data( index, PackageListModel::NameRole ).toString() );
        ui->productDescription->setText( model->data( index, PackageListModel::DescriptionRole ).toString() );

        QPixmap currentScreenshot = model->data( index, PackageListModel::ScreenshotRole ).value< QPixmap >();
        if ( currentScreenshot.isNull() )
        {
            ui->productScreenshot->setPixmap( m_introduction.screenshot );
        }
        else
        {
            ui->productScreenshot->setPixmap( currentScreenshot );
        }
    }
}
""",
        """}

bool
PackageChooserPage::usesCheckList() const
{
    return ( m_mode == PackageChooserMode::OptionalMultiple ) || ( m_mode == PackageChooserMode::RequiredMultiple );
}

void
PackageChooserPage::currentChanged( const QModelIndex& index )
{
    if ( !index.isValid() )
    {
        ui->productName->setText( m_introduction.name.get() );
        ui->productScreenshot->setPixmap( m_introduction.screenshot );
        ui->productDescription->setText( m_introduction.description.get() );
    }
    else
    {
        const auto* model = ui->products->model();

        ui->productName->setText( model->data( index, PackageListModel::NameRole ).toString() );
        ui->productDescription->setText( model->data( index, PackageListModel::DescriptionRole ).toString() );

        QPixmap currentScreenshot = model->data( index, PackageListModel::ScreenshotRole ).value< QPixmap >();
        if ( currentScreenshot.isNull() )
        {
            ui->productScreenshot->setPixmap( m_introduction.screenshot );
        }
        else
        {
            ui->productScreenshot->setPixmap( currentScreenshot );
        }
    }
}
""",
    )
    replace_once(
        root / "src/modules/packagechooser/PackageChooserPage.cpp",
        """void
PackageChooserPage::updateLabels()
{
    if ( ui && ui->products && ui->products->selectionModel() )
    {
        currentChanged( ui->products->selectionModel()->currentIndex() );
    }
    else
    {
        currentChanged( QModelIndex() );
    }
    emit selectionChanged();
}
""",
        """void
PackageChooserPage::updateLabels()
{
    if ( ui && ui->products )
    {
        currentChanged( ui->products->currentIndex() );
    }
    else
    {
        currentChanged( QModelIndex() );
    }
    emit selectionChanged();
}
""",
    )
    replace_once(
        root / "src/modules/packagechooser/PackageChooserPage.cpp",
        """void
PackageChooserPage::setModel( QAbstractItemModel* model )
{
    ui->products->setModel( model );
    currentChanged( QModelIndex() );
    connect( ui->products->selectionModel(),
             &QItemSelectionModel::selectionChanged,
             this,
             &PackageChooserPage::updateLabels );
}
""",
        """void
PackageChooserPage::setModel( QAbstractItemModel* model )
{
    if ( usesCheckList() )
    {
        delete m_checkModel;
        m_checkModel = new QStandardItemModel( this );

        const int rows = model ? model->rowCount( QModelIndex() ) : 0;
        for ( int row = 0; row < rows; ++row )
        {
            const QModelIndex sourceIndex = model->index( row, 0 );
            auto* item = new QStandardItem( model->data( sourceIndex, PackageListModel::NameRole ).toString() );
            item->setEditable( false );
            item->setCheckable( true );
            item->setCheckState( Qt::Unchecked );
            item->setData( model->data( sourceIndex, PackageListModel::NameRole ), PackageListModel::NameRole );
            item->setData( model->data( sourceIndex, PackageListModel::DescriptionRole ),
                           PackageListModel::DescriptionRole );
            item->setData( model->data( sourceIndex, PackageListModel::ScreenshotRole ),
                           PackageListModel::ScreenshotRole );
            item->setData( model->data( sourceIndex, PackageListModel::IdRole ), PackageListModel::IdRole );
            m_checkModel->appendRow( item );
        }

        ui->products->setModel( m_checkModel );
        currentChanged( QModelIndex() );

        connect( ui->products->selectionModel(),
                 &QItemSelectionModel::currentChanged,
                 this,
                 &PackageChooserPage::currentChanged );
        connect(
            m_checkModel,
            &QStandardItemModel::itemChanged,
            this,
            [this]( QStandardItem* item )
            {
                if ( !item )
                {
                    currentChanged( QModelIndex() );
                    emit selectionChanged();
                    return;
                }

                const QModelIndex index = item->index();
                if ( ui && ui->products && ui->products->selectionModel() && index.isValid() )
                {
                    ui->products->selectionModel()->setCurrentIndex(
                        index, QItemSelectionModel::ClearAndSelect | QItemSelectionModel::Rows );
                }
                currentChanged( index );
                emit selectionChanged();
            } );
        connect(
            ui->products,
            &QListView::clicked,
            this,
            [this]( const QModelIndex& index )
            {
                if ( !index.isValid() || !m_checkModel )
                {
                    return;
                }

                ui->products->selectionModel()->setCurrentIndex(
                    index, QItemSelectionModel::ClearAndSelect | QItemSelectionModel::Rows );

                auto* item = m_checkModel->itemFromIndex( index );
                if ( !item )
                {
                    return;
                }

                item->setCheckState( item->checkState() == Qt::Checked ? Qt::Unchecked : Qt::Checked );
            } );
        return;
    }

    ui->products->setModel( model );
    currentChanged( QModelIndex() );
    connect( ui->products->selectionModel(),
             &QItemSelectionModel::selectionChanged,
             this,
             &PackageChooserPage::updateLabels );
    connect(
        ui->products->selectionModel(), &QItemSelectionModel::currentChanged, this, &PackageChooserPage::currentChanged );
}
""",
    )
    replace_once(
        root / "src/modules/packagechooser/PackageChooserPage.cpp",
        """void
PackageChooserPage::setSelection( const QModelIndex& index )
{
    if ( index.isValid() )
    {
        ui->products->selectionModel()->select( index, QItemSelectionModel::Select );
    }
    currentChanged( index );
}
""",
        """void
PackageChooserPage::setSelection( const QModelIndex& index )
{
    if ( usesCheckList() )
    {
        if ( index.isValid() && m_checkModel )
        {
            const QModelIndex mappedIndex = m_checkModel->index( index.row(), index.column() );
            ui->products->selectionModel()->setCurrentIndex(
                mappedIndex, QItemSelectionModel::ClearAndSelect | QItemSelectionModel::Rows );
            if ( auto* item = m_checkModel->itemFromIndex( mappedIndex ) )
            {
                item->setCheckState( Qt::Checked );
            }
            currentChanged( mappedIndex );
            emit selectionChanged();
            return;
        }
        currentChanged( QModelIndex() );
        return;
    }

    if ( index.isValid() )
    {
        ui->products->selectionModel()->select( index, QItemSelectionModel::Select );
    }
    currentChanged( index );
}
""",
    )
    replace_once(
        root / "src/modules/packagechooser/PackageChooserPage.cpp",
        """bool
PackageChooserPage::hasSelection() const
{
    return ui && ui->products && ui->products->selectionModel() && ui->products->selectionModel()->hasSelection();
}
""",
        """bool
PackageChooserPage::hasSelection() const
{
    if ( usesCheckList() )
    {
        if ( !m_checkModel )
        {
            return false;
        }

        for ( int row = 0; row < m_checkModel->rowCount(); ++row )
        {
            const auto* item = m_checkModel->item( row );
            if ( item && item->checkState() == Qt::Checked )
            {
                return true;
            }
        }
        return false;
    }

    return ui && ui->products && ui->products->selectionModel() && ui->products->selectionModel()->hasSelection();
}
""",
    )
    replace_once(
        root / "src/modules/packagechooser/PackageChooserPage.cpp",
        """QStringList
PackageChooserPage::selectedPackageIds() const
{
    if ( !( ui && ui->products && ui->products->selectionModel() ) )
    {
        return QStringList();
    }

    const auto* model = ui->products->model();
    QStringList ids;
    for ( const auto& index : ui->products->selectionModel()->selectedIndexes() )
    {
        QString pid = model->data( index, PackageListModel::IdRole ).toString();
        if ( !pid.isEmpty() )
        {
            ids.append( pid );
        }
    }
    return ids;
}
""",
        """QStringList
PackageChooserPage::selectedPackageIds() const
{
    if ( usesCheckList() )
    {
        if ( !m_checkModel )
        {
            return QStringList();
        }

        QStringList ids;
        for ( int row = 0; row < m_checkModel->rowCount(); ++row )
        {
            const auto* item = m_checkModel->item( row );
            if ( item && item->checkState() == Qt::Checked )
            {
                const QString pid = item->data( PackageListModel::IdRole ).toString();
                if ( !pid.isEmpty() )
                {
                    ids.append( pid );
                }
            }
        }
        return ids;
    }

    if ( !( ui && ui->products && ui->products->selectionModel() ) )
    {
        return QStringList();
    }

    const auto* model = ui->products->model();
    QStringList ids;
    for ( const auto& index : ui->products->selectionModel()->selectedIndexes() )
    {
        QString pid = model->data( index, PackageListModel::IdRole ).toString();
        if ( !pid.isEmpty() )
        {
            ids.append( pid );
        }
    }
    return ids;
}
""",
    )

    for relative_path, old, new in (
        (
            "src/modules/welcome/WelcomeViewStep.cpp",
            '    return tr( "Welcome", "@title" );\n',
            '    return tr( "01 PRE-FLIGHT", "@title" );\n',
        ),
        (
            "src/modules/locale/LocaleViewStep.cpp",
            '    return tr( "Location", "@label" );\n',
            '    return tr( "02 LOCATION", "@label" );\n',
        ),
        (
            "src/modules/keyboard/KeyboardViewStep.cpp",
            '    return tr( "Keyboard", "@label" );\n',
            '    return tr( "03 KEYBOARD", "@label" );\n',
        ),
        (
            "src/modules/partition/PartitionViewStep.cpp",
            '    return tr( "Partitions", "@label" );\n',
            '    return tr( "04 DISK TARGET", "@label" );\n',
        ),
        (
            "src/modules/users/UsersViewStep.cpp",
            '    return tr( "Users" );\n',
            '    return tr( "05 USER PROFILE" );\n',
        ),
        (
            "src/modules/finished/FinishedViewStep.cpp",
            '    return tr( "Finish", "@label" );\n',
            '    return tr( "08 COMPLETE", "@label" );\n',
        ),
        (
            "src/libcalamaresui/viewpages/ExecutionViewStep.cpp",
            '    return Calamares::Settings::instance()->isSetupMode() ? tr( "Set Up", "@label" ) : tr( "Install", "@label" );\n',
            '    return Calamares::Settings::instance()->isSetupMode() ? tr( "07 SET UP", "@label" ) : tr( "07 INSTALL", "@label" );\n',
        ),
    ):
        replace_once(root / relative_path, old, new)

    replace_regex_once(
        root / "src/modules/finished/FinishedPage.cpp",
        r'ui->mainText->setText\(\s*tr\(\s*"<h1>All done\.</h1><br/>"\s*"%1 has been installed on your computer\.<br/>"\s*"You may now restart into your new system, or continue "\s*"using the %2 Live environment\.",\s*"@info" \)\s*\.arg\( branding->versionedName\(\), branding->productName\(\) \)\s*\);',
        """ui->mainText->setText( tr( "<h1>All done.</h1><br/>"
                                    "%1 has been deployed on your computer.<br/>"
                                    "After reboot and login, Kesk Welcome will guide first-boot setup.",
                                    "@info" )
                                    .arg( branding->versionedName() ) );""",
    )

    replace_once(
        root / "src/modules/welcome/Config.cpp",
        """QString
Config::genericWelcomeMessage() const
{
    QString message;

    const auto* settings = Calamares::Settings::instance();
    const auto* branding = Calamares::Branding::instance();
    const bool welcomeStyle = branding ? branding->welcomeStyleCalamares() : true;

    if ( settings ? settings->isSetupMode() : false )
    {
        message = welcomeStyle ? tr( "<h1>Welcome to the Calamares setup program for %1</h1>" )
                               : tr( "<h1>Welcome to %1 setup</h1>" );
    }
    else
    {
        message = welcomeStyle ? tr( "<h1>Welcome to the Calamares installer for %1</h1>" )
                               : tr( "<h1>Welcome to the %1 installer</h1>" );
    }

    return message;
}
""",
        """QString
Config::genericWelcomeMessage() const
{
    return tr(
        "<div style=\\"font-size:28px; font-weight:600; color:#e8ddd4;\\">KESKOS LIVE ENVIRONMENT DETECTED</div>"
        "<div style=\\"margin-top:8px; font-size:15px; color:#8f8a84;\\">Deployment console initialized. Select your installation profile to continue.</div>" );
}
""",
    )
    replace_once(
        root / "src/modules/welcome/Config.cpp",
        """        m_warningMessage = tr( "This program will ask you some questions and "
                               "set up %2 on your computer." )
                               .arg( branding ? branding->productName() : QString() );
""",
        """        m_warningMessage = tr(
            "Deployment console initialized. Review locale, support options, and deployment checks below." );
""",
    )

    replace_once(
        root / "src/modules/welcome/WelcomePage.cpp",
        """    const int defaultFontHeight = Calamares::defaultFontHeight();
    ui->setupUi( this );

    // insert system-check widget below welcome text
    const int welcome_text_idx = ui->verticalLayout->indexOf( ui->mainText );
    ui->verticalLayout->insertWidget( welcome_text_idx + 1, m_checkingWidget );

    // insert optional logo banner image above welcome text
    QString bannerPath = Branding::instance()->imagePath( Branding::ProductBanner );
    if ( !bannerPath.isEmpty() )
    {
        // If the name is not empty, the file exists -- Branding checks that at startup
        QPixmap bannerPixmap = QPixmap( bannerPath );
        if ( !bannerPixmap.isNull() )
        {
            QLabel* bannerLabel = new QLabel;
            bannerLabel->setPixmap( bannerPixmap );
            bannerLabel->setMinimumHeight( 64 );
            bannerLabel->setAlignment( Qt::AlignCenter );
            ui->aboveTextSpacer->changeSize( 20, defaultFontHeight );  // Shrink it down
            ui->aboveTextSpacer->invalidate();
            ui->verticalLayout->insertSpacing( welcome_text_idx, defaultFontHeight );
            ui->verticalLayout->insertWidget( welcome_text_idx, bannerLabel );
        }
    }

    initLanguages();
""",
        """    const int defaultFontHeight = Calamares::defaultFontHeight();
    ui->setupUi( this );
    ui->mainText->setAlignment( Qt::AlignLeft | Qt::AlignVCenter );
    ui->mainText->setWordWrap( true );
    ui->verticalLayout->setSpacing( defaultFontHeight / 2 );
    ui->horizontalLayout_3->setSpacing( defaultFontHeight / 2 );

    // insert system-check widget below welcome text
    const int welcome_text_idx = ui->verticalLayout->indexOf( ui->mainText );
    ui->verticalLayout->insertWidget( welcome_text_idx + 1, m_checkingWidget );

    // insert optional logo banner image above welcome text
    QString bannerPath = Branding::instance()->imagePath( Branding::ProductBanner );
    if ( !bannerPath.isEmpty() )
    {
        // If the name is not empty, the file exists -- Branding checks that at startup
        QPixmap bannerPixmap = QPixmap( bannerPath );
        if ( !bannerPixmap.isNull() )
        {
            QLabel* bannerLabel = new QLabel;
            bannerLabel->setPixmap( bannerPixmap );
            bannerLabel->setMinimumHeight( 48 );
            bannerLabel->setAlignment( Qt::AlignCenter );
            ui->aboveTextSpacer->changeSize( 20, defaultFontHeight / 2 );
            ui->aboveTextSpacer->invalidate();
            ui->verticalLayout->insertSpacing( welcome_text_idx, defaultFontHeight / 2 );
            ui->verticalLayout->insertWidget( welcome_text_idx, bannerLabel );
        }
    }

    auto* localeProfileLabel = new QLabel( tr( "LOCALE PROFILE", "@title" ), this );
    localeProfileLabel->setObjectName( "localeProfileLabel" );
    ui->verticalLayout->insertWidget( ui->verticalLayout->indexOf( ui->mainText ) + 2, localeProfileLabel );

    initLanguages();
""",
    )
    replace_once(
        root / "src/modules/welcome/WelcomePage.cpp",
        """    //language icon
    auto icon = Calamares::Branding::instance()->image( m_conf->languageIcon(), QSize( 48, 48 ) );
    if ( !icon.isNull() )
    {
        setLanguageIcon( icon );
    }
}
""",
        """    // language icon
    auto icon = Calamares::Branding::instance()->image( m_conf->languageIcon(), QSize( 48, 48 ) );
    if ( !icon.isNull() )
    {
        setLanguageIcon( icon );
    }
    ui->languageIcon->hide();
    ui->supportButton->setFlat( false );
}
""",
    )
    replace_once(
        root / "src/modules/welcome/WelcomePage.cpp",
        """    const QString message = m_conf->genericWelcomeMessage();

    ui->mainText->setText( message.arg( Calamares::Branding::instance()->versionedName() ) );
    ui->retranslateUi( this );
    ui->supportButton->setText(
        tr( "%1 Support", "@action" ).arg( Calamares::Branding::instance()->shortProductName() ) );
}
""",
        """    const QString message = m_conf->genericWelcomeMessage();

    ui->mainText->setText( message );
    ui->retranslateUi( this );
    ui->supportButton->setText(
        tr( "[ %1 SUPPORT ]", "@action" ).arg( Calamares::Branding::instance()->shortProductName() ) );
}
""",
    )

    replace_once(
        root / "src/modules/welcome/checker/ResultsListWidget.cpp",
        """    if ( requirementsSatisfied )
    {
        delete m_centralWidget;
        m_centralWidget = nullptr;

        if ( !Calamares::Branding::instance()->imagePath( Calamares::Branding::ProductWelcome ).isEmpty() )
        {
            QPixmap theImage
                = QPixmap( Calamares::Branding::instance()->imagePath( Calamares::Branding::ProductWelcome ) );
            if ( !theImage.isNull() )
            {
                QLabel* imageLabel;
                if ( Calamares::Branding::instance()->welcomeExpandingLogo() )
                {
                    FixedAspectRatioLabel* p = new FixedAspectRatioLabel;
                    p->setPixmap( theImage );
                    imageLabel = p;
                }
                else
                {
                    imageLabel = new QLabel;
                    imageLabel->setPixmap( theImage );
                }

                imageLabel->setContentsMargins( 4, Calamares::defaultFontHeight() * 3 / 4, 4, 4 );
                imageLabel->setAlignment( Qt::AlignCenter );
                imageLabel->setSizePolicy( QSizePolicy::Expanding, QSizePolicy::Expanding );
                imageLabel->setObjectName( "welcomeLogo" );
                // This specifically isn't assigned to m_centralWidget
                m_centralLayout->addWidget( imageLabel );
            }
        }
        m_explanation->setAlignment( Qt::AlignCenter );
    }
""",
        """    if ( requirementsSatisfied )
    {
        delete m_centralWidget;
        m_centralWidget = nullptr;
        m_explanation->hide();

        auto* dashboard = new QWidget( this );
        dashboard->setObjectName( "welcomeDashboard" );
        auto* dashboardLayout = new QHBoxLayout( dashboard );
        dashboardLayout->setContentsMargins( 0, Calamares::defaultFontHeight() / 2, 0, 0 );
        dashboardLayout->setSpacing( Calamares::defaultFontHeight() / 2 );

        auto* brandCard = new QWidget( dashboard );
        brandCard->setObjectName( "welcomeBrandCard" );
        auto* brandLayout = new QVBoxLayout( brandCard );
        brandLayout->setContentsMargins( 18, 16, 18, 16 );
        brandLayout->setSpacing( 6 );

        auto* brandTitle = new QLabel( tr( "K E S K   O S", "@title" ), brandCard );
        brandTitle->setObjectName( "welcomeBrandTitle" );
        auto* brandEdition = new QLabel( tr( "S.P.L.I.T. EDITION", "@info" ), brandCard );
        brandEdition->setObjectName( "welcomeBrandMeta" );
        auto* brandTagline = new QLabel( tr( "BUILT DIFFERENT.", "@info" ), brandCard );
        brandTagline->setObjectName( "welcomeBrandMeta" );

        brandLayout->addWidget( brandTitle );
        brandLayout->addWidget( brandEdition );
        brandLayout->addStretch();
        brandLayout->addWidget( brandTagline );

        auto* statusPanel = new QWidget( dashboard );
        statusPanel->setObjectName( "welcomeStatusPanel" );
        auto* statusLayout = new QVBoxLayout( statusPanel );
        statusLayout->setContentsMargins( 18, 16, 18, 16 );
        statusLayout->setSpacing( 8 );

        auto* statusHeading = new QLabel( tr( "SYSTEM STATUS", "@title" ), statusPanel );
        statusHeading->setObjectName( "welcomeStatusHeading" );
        auto* statusText = new QLabel( statusPanel );
        statusText->setObjectName( "welcomeStatusText" );
        statusText->setTextFormat( Qt::RichText );
        statusText->setText(
            tr( "<span style=\\"color:#ce6a35;\\">[ OK ]</span> display stack online<br/>"
                "<span style=\\"color:#ce6a35;\\">[ OK ]</span> installer backend loaded<br/>"
                "<span style=\\"color:#ce6a35;\\">[ OK ]</span> package manifest ready<br/>"
                "<span style=\\"color:#ce6a35;\\">[ OK ]</span> target scanner armed",
                "@info" ) );

        statusLayout->addWidget( statusHeading );
        statusLayout->addWidget( statusText );
        statusLayout->addStretch();

        dashboardLayout->addWidget( brandCard, 1 );
        dashboardLayout->addWidget( statusPanel, 2 );
        m_centralLayout->addWidget( dashboard );
    }
""",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
