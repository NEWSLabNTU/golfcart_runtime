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

# Configure launch script with proper paths
set(ROS_DISTRO "humble")
configure_file(
  ${CMAKE_CURRENT_SOURCE_DIR}/scripts/golfcart-launch.sh.in
  ${CMAKE_CURRENT_BINARY_DIR}/scripts/golfcart-launch.sh
  @ONLY
)

# Make the generated script executable
file(CHMOD ${CMAKE_CURRENT_BINARY_DIR}/scripts/golfcart-launch.sh
  PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE
              GROUP_READ GROUP_EXECUTE
              WORLD_READ WORLD_EXECUTE)

# Install the generated launch script
install(
  PROGRAMS
    ${CMAKE_CURRENT_BINARY_DIR}/scripts/golfcart-launch.sh
  DESTINATION share/${PROJECT_NAME}/scripts
)

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