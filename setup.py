from setuptools import find_packages, setup

setup(
    name="sqlalchemy-pydantic-codegen",
    version="0.1.0",
    author="Dsanmart",
    description="A library to generate Pydantic models from SQLAlchemy models.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/dsanmart/sqlalchemy-pydantic-codegen",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "sqlalchemy-pydantic-codegen=sqlalchemy_pydantic_codegen.cli:main",
        ],
    },
)
