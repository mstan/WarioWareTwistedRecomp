cmake_minimum_required(VERSION 3.22)
project(WarioWareTwistedAndroid C CXX)

get_filename_component(WARIOWARE_ROOT
    "${CMAKE_CURRENT_LIST_DIR}/../../../../.." ABSOLUTE)
set(SDL_ROOT "${WARIOWARE_ROOT}/android/third_party/SDL")

set(SDL_SHARED ON CACHE BOOL "" FORCE)
set(SDL_STATIC OFF CACHE BOOL "" FORCE)
set(SDL_TEST OFF CACHE BOOL "" FORCE)
set(SDL_TESTS OFF CACHE BOOL "" FORCE)
add_subdirectory("${SDL_ROOT}" sdl_build)

add_subdirectory("${WARIOWARE_ROOT}" game_build)
