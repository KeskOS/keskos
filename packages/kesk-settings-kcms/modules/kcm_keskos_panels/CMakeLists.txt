kcmutils_add_qml_kcm(kcm_keskos_panels
    SOURCES
        panelskcm.cpp
)

target_link_libraries(kcm_keskos_panels PRIVATE
    kesk_kcm_common
    Qt::Core
    Qt::Qml
    Qt::Quick
    KF6::KCMUtils
    KF6::KCMUtilsQuick
)
