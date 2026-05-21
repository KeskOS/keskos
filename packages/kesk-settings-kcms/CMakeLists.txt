cmake_minimum_required(VERSION 3.16)

project(kesk-settings-kcms LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(ECM 6.0 REQUIRED NO_MODULE)
set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH} ${CMAKE_CURRENT_SOURCE_DIR}/cmake)

include(KDEInstallDirs)
include(KDECompilerSettings NO_POLICY_SCOPE)
include(KDECMakeSettings)

find_package(Qt6 6.5 REQUIRED COMPONENTS Core Gui Qml Quick)
find_package(KF6 6.0 REQUIRED COMPONENTS CoreAddons KCMUtils)

install(FILES categories/settings-keskos.desktop DESTINATION ${KDE_INSTALL_DATADIR}/systemsettings/categories)
install(PROGRAMS scripts/kesk-apply-kde-defaults scripts/kesk-browser-settings DESTINATION ${KDE_INSTALL_BINDIR})

if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/modules/CMakeLists.txt")
    add_subdirectory(modules)
else()
    message(STATUS "No modules/CMakeLists.txt found; installing desktop category and helper scripts only.")
endif()
