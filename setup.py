#!/usr/bin/env python3
"""
Setup script for microlens-submit package.
"""

from setuptools import find_packages, setup

if __name__ == "__main__":
    setup(
        name="microlens-submit",
        version="0.16.3",
        packages=find_packages(include=("microlens_submit", "microlens_submit.*")),
        include_package_data=True,
        package_data={
            "microlens_submit": ["assets/*"],
        },
        install_requires=[
            "pydantic>=2.0.0",
            "typer[all]>=0.9.0",
            "rich>=13.0.0",
            "pyyaml>=6.0",
            "markdown>=3.4.0",
            'importlib_resources>=1.0.0; python_version<"3.9"',
        ],
        extras_require={
            "dev": [
                "pytest",
                "pytest-cov",
                "build",
                "twine",
                "pre-commit",
                "black",
                "isort",
                "sphinx",
                "sphinx_rtd_theme",
            ],
        },
        entry_points={
            "console_scripts": [
                "microlens-submit=microlens_submit.cli:app",
            ],
        },
        python_requires=">=3.8",
        author="Amber Malpas",
        author_email="malpas.1@osu.edu",
        description="A tool for managing and submitting microlensing solutions",
        long_description=open("README.md").read(),
        long_description_content_type="text/markdown",
        url="https://github.com/AmberLee2427/microlens-submit",
        classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: Science/Research",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Topic :: Scientific/Engineering :: Astronomy",
            "Topic :: Scientific/Engineering :: Physics",
        ],
        keywords=["astronomy", "microlensing", "data-challenge", "submission", "roman"],
    )
