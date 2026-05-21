kcmutils_add_qml_kcm(kcm_keskos_about
    SOURCES
        aboutkcm.cpp
)

target_link_libraries(kcm_keskos_about PRIVATE
    kesk_kcm_common
    Qt::Core
    Qt::Qml
    Qt::Quick
    KF6::KCMUtils
    KF6::KCMUtilsQuick
)
