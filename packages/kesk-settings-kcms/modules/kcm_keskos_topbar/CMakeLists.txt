kcmutils_add_qml_kcm(kcm_keskos_topbar
    SOURCES
        topbarkcm.cpp
)

target_link_libraries(kcm_keskos_topbar PRIVATE
    kesk_kcm_common
    Qt::Core
    Qt::Qml
    Qt::Quick
    KF6::KCMUtils
    KF6::KCMUtilsQuick
)
