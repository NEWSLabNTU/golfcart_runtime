cmake_minimum_required(VERSION 3.8)
project(golfcart_runtime)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)

# Install Python modules
ament_python_install_package(${PROJECT_NAME})

# No launch wrapper is generated here any more. golfcart.service delegates to
# the workspace's scripts/multi_machine/launch_unit_exec.sh, which is the same
# entry point golfcart-launch.service uses, so this package no longer carries a
# second implementation of starting the stack.

# Install the main golfcart CLI script to bin directory (added to PATH automatically)
install(
  PROGRAMS
    scripts/golfcart
  DESTINATION bin
)

# Install systemd service templates
install(
  DIRECTORY systemd/
  DESTINATION share/${PROJECT_NAME}/systemd
  FILES_MATCHING PATTERN "*.service" PATTERN "*.timer" PATTERN "*.conf"
)

# Install configuration files
install(
  DIRECTORY config/
  DESTINATION share/${PROJECT_NAME}/config
  FILES_MATCHING PATTERN "*.conf" PATTERN "*.yaml"
)

# Install launch files
install(
  DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
  FILES_MATCHING PATTERN "*launch.[pxy][yma]*"
)

# Install documentation
install(
  FILES
    README.md
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()