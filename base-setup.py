import setuptools
from setuptools import setup, find_packages

setup(
    name="server-automation-setup",
    install_requires=["pyyaml", "fabric", "pyinvoke", "paramiko"],
    packages=find_packages(),
    python_requires='>3.0',
    entry_points={
        "console_scripts": [
            "serverautomation = serverautomation.__main__:main"
        ]
    }
)