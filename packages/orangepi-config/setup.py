from setuptools import setup, find_packages

setup(
    name="orangepi-config",
    version="0.2.1",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "orangepi-config = orangepi_config.cli:main",
        ],
    },
)
