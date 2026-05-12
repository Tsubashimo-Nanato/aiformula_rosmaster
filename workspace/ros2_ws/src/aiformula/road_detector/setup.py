from glob import glob

from setuptools import find_packages, setup

package_name = "road_detector"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/config", glob("config/*.yaml")),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
        (f"share/{package_name}/weights", glob("weights/*.onnx")),
        (f"share/{package_name}/third_party/YOLOP_A1", glob("third_party/YOLOP_A1/*")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ROSMASTER AI Formula Maintainers",
    maintainer_email="dev@example.com",
    description="YOLOP_A1 road/lane mask detector for ROSMASTER AI Formula compatibility.",
    license="Proprietary",
    entry_points={
        "console_scripts": [
            "road_detector = road_detector.road_detector:main",
        ],
    },
)
