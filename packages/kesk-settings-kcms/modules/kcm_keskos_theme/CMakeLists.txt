kcmutils_add_qml_kcm(kcm_keskos_theme
    SOURCES
        themekcm.cpp
)

target_link_libraries(kcm_keskos_theme PRIVATE
    kesk_kcm_common
    Qt::Core
    Qt::Qml
    Qt::Quick
    KF6::KCMUtils
    KF6::KCMUtilsQuick
)
