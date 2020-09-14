from pathlib import Path
from typing import List
from setuptools import setup, find_packages


def _get_dependencies(requirements_file: Path) -> List[str]:
    lines = requirements_file.read_text().strip().split('\n')
    return [line for line in lines if not line.startswith('#')]


INSTALL_REQUIRES = _get_dependencies(
    requirements_file=Path('requirements.txt'),
)

setup(
    name='interactions',
    package_dir={"": "src"},
    packages=find_packages(where='src'),
    version='0.1',
    install_requires=INSTALL_REQUIRES,
    entry_points="""
        [console_scripts]
        interactions=interactions.cli:main
    """,
)