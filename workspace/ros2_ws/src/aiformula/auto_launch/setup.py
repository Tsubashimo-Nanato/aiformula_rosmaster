from glob import glob

from setuptools import find_packages, setup

package_name = "auto_launch"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", glob("launch/*.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ROSMASTER AI Formula Maintainers",
    maintainer_email="dev@example.com",
    description="AI Formula perception launchers for the ROSMASTER adapter workspace.",
    license="Proprietary",
    entry_points={"console_scripts": []},
)
