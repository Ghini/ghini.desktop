import toml
import os

version_data = {}
with open("bauble/version.py") as f:
    exec(f.read(), version_data)

bauble_version = version_data.get("version")  

def create_pyproject():
    pyproject_data = {
        "build-system": {
            "requires": ["setuptools>=65.5.0", "wheel", "toml"],
            "build-backend": "setuptools.build_meta",
        },
        "tool": {
            "setuptools": {
                "include-package-data": True,
                "packages": {
                    "find": {
                        "where": ["."],
                        "include": ["bauble", "bauble.*"],
                        "exclude": ["test", "bauble.*.test", "ghini.*.test"],
                    }
                },
            },
            "ghini": {
                "platforms": ["Linux", "Windows", "macOS"],
            },
        },
        "project": {
            "name": "ghini-desktop",
            "version": bauble_version,
            "description": "Ghini: a biodiversity collection manager",
            "readme": {
                "file": "README.rst",  # Use README.rst instead of README.md
                "content-type": "text/x-rst",  # Specify reStructuredText format
            },
            "keywords": [
                "database",
                "biodiversity",
                "botany",
                "collection",
                "herbarium",
                "arboretum",
            ],
            "license": "GPL-2.0-or-later",
            "authors": [
                {"name": "Brett Adams", "email": "brett@belizebotanic.org"},
                {"name": "Mario Frasca", "email": "mario@anche.no"},
                {"name": "Ross Demuth", "email": "rossdemuth123@gmail.com"},
                {"name": "Chris Wyse", "email": "chris.wyse@wysechoice.net"},  
            ],
            "dependencies": [
                # Main requirements from requirements.txt and constraints.txt
                #                                        Latest as of 11/19/24
                "certifi==2024.8.30",                    # 2024.8.30
                "chardet==5.2.0",                        # 5.2.0
                "ecdsa==0.19.0",                         # 0.19.0
                "fibra==0.0.20",                         # 0.0.20
                "gdata-python3==3.0.1",                  # 3.0.1
                "idna==3.4",                             # 3.4
                "Jinja2==3.1.2",                         # 3.1.2
                "lxml==5.3.0",                           # 5.3.0
                "Mako==1.2.4",                           # 1.2.4
                "MarkupSafe==3.0.2",                     # 3.0.2
                "Pillow==10.0.1",                        # 10.0.1
                "psycopg2==2.9.10",                      # 2.9.10
                "pycairo==1.27.0",                       # 1.27.0
                "PyGObject==3.50.0",                     # 3.50.0
                "pyparsing==3.1.1",                      # 3.1.1
                "PyQRCode==1.2.1",                       # 1.2.1
                "python-dateutil==2.8.2",                # 2.8.2
                "raven==6.10.0",                         # 6.10.0
                "requests==2.32.3",                      # 2.32.3
                "six==1.16.0",                           # 1.16.0
                "SQLAlchemy==2.0.36",                    # 2.0.36
                "tlslite-ng==0.7.6",                     # 0.7.6
                "urllib3==2.1.0",                        # 2.1.0
            ],
            "requires-python": ">=3.9,<4.0",  # Specify Python version requirement
            "optional-dependencies": {
                "dev": [
                    # Development dependencies from dev-requirements.txt and dev-constraints.txt
                    "pytest==7.4.0",                     # 7.4.0
                    "pytest-cov==6.0.0",                 # 6.0.0
                    "tox==4.8.0",                        # 4.8.0
                    # Add additional dev dependencies here
                ],
                "docs": [
                    # Documentation dependencies from doc-requirements.txt and doc-constraints.txt
                    "Sphinx==7.4.7",                     # 7.4.7
                    "sphinx-rtd-theme==3.0.2",           # 3.0.2
                    "sphinx-autodoc-typehints==2.3.0",   # 2.3.0
                    # Add additional doc dependencies here
                ],
            },
        },
        "project_urls": {
            "homepage": "http://ghini.github.io/",
            "repository": "https://github.com/ghini/ghini.desktop",
            "documentation": "http://ghini.github.io/docs",
        },
    }

    print("pyproject.toml generation started.")
    # Write to pyproject.toml
    with open("/app/pyproject.toml", "w") as file:
        toml.dump(pyproject_data, file)
    print("pyproject.toml has been generated successfully.")

import os
print("Contents of /app:", os.listdir('.'))

if __name__ == "__main__":
    create_pyproject()
