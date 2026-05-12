from setuptools import find_packages, setup

package_name = "rosmaster_aiformula_bridge"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ROSMASTER AI Formula Maintainers",
    maintainer_email="dev@example.com",
    description="Topic compatibility bridge between ROSMASTER hardware topics and AI Formula/Sophia topics.",
    license="Proprietary",
    entry_points={
        "console_scripts": [
            "compat_bridge = rosmaster_aiformula_bridge.compat_bridge:main",
            "joy_diff_drive_mapper = rosmaster_aiformula_bridge.joy_diff_drive_mapper:main",
            "rosmaster_driver_x3 = rosmaster_aiformula_bridge.rosmaster_driver_x3:main",
        ],
    },
)
