kcmutils_add_qml_kcm(kcm_keskos_help
    SOURCES
        helpkcm.cpp
)

target_link_libraries(kcm_keskos_help PRIVATE
    kesk_kcm_common
    Qt::Core
    Qt::Qml
    Qt::Quick
    KF6::KCMUtils
    KF6::KCMUtilsQuick
)
