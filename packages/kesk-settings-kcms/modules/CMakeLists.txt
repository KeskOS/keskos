add_library(kesk_kcm_common STATIC
    common/keskmodulebase.cpp
)

set_target_properties(kesk_kcm_common PROPERTIES
    POSITION_INDEPENDENT_CODE ON
)

target_include_directories(kesk_kcm_common
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/common
)

target_link_libraries(kesk_kcm_common
    PUBLIC
        Qt::Core
        Qt::Gui
        Qt::Qml
        Qt::Quick
        KF6::CoreAddons
        KF6::KCMUtilsQuick
)

add_subdirectory(kcm_keskos_about)
add_subdirectory(kcm_keskos_help)
add_subdirectory(kcm_keskos_theme)
add_subdirectory(kcm_keskos_panels)
add_subdirectory(kcm_keskos_topbar)
add_subdirectory(kcm_keskos_browser)
add_subdirectory(kcm_keskos_bootsplash)
add_subdirectory(kcm_keskos_version)
