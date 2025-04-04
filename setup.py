from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="instaflow",
    version="0.1.0",
    author="Bima Pangestu",
    author_email="bima@catalystlabs.id",
    description="A Python-based Instagram automation tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BimaPangestu28/InstaFlow",
    project_urls={
        "Bug Tracker": "https://github.com/BimaPangestu28/InstaFlow/issues",
        "Website": "https://instaflow.catalystlabs.id",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "instaflow=instaflow.cli:main",
        ],
    },
    install_requires=[
        "selenium>=4.1.0",
        "python-dotenv>=0.19.0",
    ],
)