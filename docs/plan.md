## Part 1: Project Structure Setup
### Step 1: Create Project Directory and Files
Open VSCode's integrated terminal (`` Ctrl+` `` or `View → Terminal`) and run:
```bash
# Navigate to where you want to create the project
cd ~/Documents  # or wherever you want

# Create main project directory
mkdir ihydrocal
cd ihydrocal

# Create all directories
mkdir -p ihydrocal tests docs .github/workflows conda.recipe

# Create Python files
touch ihydrocal/__init__.py
touch ihydrocal/cli.py
touch tests/__init__.py
touch tests/test_basic.py

# Create configuration files
touch .gitignore
touch README.md
touch LICENSE
touch pyproject.toml
touch setup.py
touch MANIFEST.in
touch environment.yml
touch conda.recipe/meta.yaml

# Create GitHub workflow files
touch .github/workflows/tests.yml
touch .github/workflows/publish-pypi.yml
touch .github/workflows/publish-conda.yml
```


- Now open this folder in VSCode:
```bash
code .
```

Or in VSCode: `File → Open Folder → Select ihydrocal folder`

### Step 2: Your Directory Structure Should Look Like This

```bash
ihydrocal/
├── .github/
│   └── workflows/
│       ├── tests.yml
│       ├── publish-pypi.yml
│       └── publish-conda.yml
├── conda.recipe/
│   └── meta.yaml
├── docs/
├── src/ihydrocal/
│   ├── __init__.py
│   └── cli.py
├── tests/
│   ├── __init__.py
│   └── test_basic.py
├── .gitignore
├── environment.yml
├── LICENSE
├── MANIFEST.in
├── pyproject.toml
├── README.md
└── setup.py
```

## Part 2: Fill in All Files (Copy-Paste Ready)

### Open each file in VSCode and paste the content:

#### 📄 `.gitignore`

```gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/
cover/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/
docs/_static/
docs/_templates/

# PyBuilder
.pybuilder/
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
.python-version

# pipenv
Pipfile.lock

# PEP 582
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Cython debug symbols
cython_debug/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~
*.sublime-project
*.sublime-workspace

# OS specific
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project specific
workspace/
outputs/
results/
*.log
*.bak
*~
test_data/
scratch/


### 4. `requirements.txt`

numpy>=1.20.0
pandas>=1.3.0
matplotlib>=3.4.0
scipy>=1.7.0
pyyaml>=5.4.0
pyemu>=1.2.0
flopy>=3.3.5


### 5. `requirements-dev.txt`

-r requirements.txt
pytest>=7.0.0
pytest-cov>=3.0.0
black>=22.0.0
flake8>=4.0.0
mypy>=0.950
sphinx>=4.5.0
sphinx-rtd-theme>=1.0.0
twine>=4.0.0
build>=0.7.0

```

#### 📄 `README.md`
````markdown
# iHydroCal

**Integrated Hydrological Model Calibration and Uncertainty Analysis**

[![Tests](https://github.com/yourusername/ihydrocal/workflows/Tests/badge.svg)](https://github.com/yourusername/ihydrocal/actions)
[![PyPI version](https://badge.fury.io/py/ihydrocal.svg)](https://badge.fury.io/py/ihydrocal)
[![Conda version](https://img.shields.io/conda/vn/conda-forge/ihydrocal.svg)](https://anaconda.org/conda-forge/ihydrocal)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

iHydroCal provides a unified framework for calibration and uncertainty analysis of integrated hydrological models including:

- SWAT (Soil and Water Assessment Tool)
- SWAT+ (SWAT Plus)
- SWAT-MODFLOW (coupled surface-groundwater model)
- APEX-MODFLOW-RT3D-Salt (integrated modeling system)

## Features

- 🎯 **Unified Calibration Framework**: Single interface for multiple model types
- 📊 **Uncertainty Analysis**: Comprehensive sensitivity and uncertainty quantification
- 🔧 **PEST++ Integration**: Leverage industry-standard optimization tools
- 🐍 **Python-Based**: Built on pyemu and flopy
- 📈 **Visualization**: Built-in plotting and reporting capabilities

## Installation

### From PyPI (coming soon)
```bash
pip install ihydrocal
```

### From conda (coming soon)
```bash
conda install -c conda-forge ihydrocal
```

### Development Installation
```bash
git clone https://github.com/yourusername/ihydrocal.git
cd ihydrocal
pip install -e .[dev]
```

## Quick Start
```python
import ihydrocal as ihc

# Load configuration
config = ihc.load_config("config.yaml")

# Initialize model
model = ihc.create_model("swat-modflow", config)

# Run calibration
calibrator = ihc.Calibrator(model, config.calibration)
results = calibrator.run()

# Uncertainty analysis
uncertainty = ihc.UncertaintyAnalysis(model, results)
uncertainty.sensitivity_analysis()
```

## Documentation

Full documentation is available at [https://ihydrocal.readthedocs.io](https://ihydrocal.readthedocs.io) (coming soon)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Citation

If you use iHydroCal in your research, please cite:
```bibtex
@software{ihydrocal2026,
  author = {Seonggyu Park},
  title = {iHydroCal: Integrated Hydrological Model Calibration and Uncertainty Analysis},
  year = {2026},
  url = {https://github.com/spark-hydro/ihydrocal}
}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

This project builds upon:
- [PEST++](https://github.com/usgs/pestpp) by USGS
- [pyemu](https://github.com/pypest/pyemu) 
- [flopy](https://github.com/modflowpy/flopy)

## Contact

- **Author**: Seonggyu Park
- **Email**: your.email@example.com
- **GitHub**: [yourusername](https://github.com/yourusername)
```

### 2. `LICENSE` (MIT License)
```
MIT License

Copyright (c) 2026 Seonggyu Park

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

````

📄 `pyproject.toml`
````
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "ihydrocal"
version = "0.0.0"
description = "Integrated Hydrological Model Calibration and Uncertainty Analysis"
readme = "README.md"
authors = [
    {name = "Seonggyu Park", email = "spark.hydro.ml@gmail.com"}
]
license = {text = "MIT"}
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Scientific/Engineering :: Hydrology",
]
keywords = ["hydrology", "calibration", "SWAT", "MODFLOW", "PEST", "uncertainty"]
dependencies = [
    "numpy>=1.20.0",
    "pandas>=1.3.0",
    "matplotlib>=3.4.0",
    "scipy>=1.7.0",
    "pyyaml>=5.4.0",
    "pyemu>=1.2.0",
    "flopy>=3.3.5",
]
requires-python = ">=3.12"

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=3.0.0",
    "black>=22.0.0",
    "flake8>=4.0.0",
    "mypy>=0.950",
    "sphinx>=4.5.0",
    "sphinx-rtd-theme>=1.0.0",
]

[project.urls]
Homepage = "https://github.com/yourusername/ihydrocal"
Documentation = "https://ihydrocal.readthedocs.io"
Repository = "https://github.com/yourusername/ihydrocal"
"Bug Tracker" = "https://github.com/yourusername/ihydrocal/issues"

[project.scripts]
ihydrocal = "ihydrocal.cli:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["ihydrocal*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--cov=ihydrocal --cov-report=xml --cov-report=html --cov-report=term"

[tool.black]
line-length = 88
target-version = ['py311','py312', 'py313']
include = '\.pyi?$'

[tool.mypy]
python_version = "3.13"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
````

#### 📄 `setup.py`
```python
"""Setup script for iHydroCal.""" 
from setuptools import setup # Configuration is in pyproject.toml 
setup()
```

📄 `MANIFEST.in`
```shell
### 8. `MANIFEST.in`

include LICENSE
include README.md
include requirements.txt
include requirements-dev.txt
recursive-include ihydrocal *.yaml *.yml
recursive-exclude * __pycache__
recursive-exclude * *.py[cod]
```

#### 📄 `environment.yml`
```yaml
name: ihydrocal
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.13
  - numpy>=1.26.0
  - pandas>=2.0.0
  - matplotlib>=3.8.0
  - scipy>=1.11.0
  - pyyaml>=6.0.0
  - pytest>=7.0.0
  - pytest-cov>=4.0.0
  - black>=24.0.0
  - flake8>=7.0.0
  - mypy>=1.0.0
  - sphinx>=7.0.0
  - sphinx-rtd-theme>=2.0.0
  - pip
  - pip:
      - pyemu>=1.2.0
      - flopy>=3.3.5
      - twine>=5.0.0
      - build>=1.0.0
```

#### 📄 `ihydrocal/__init__.py`

```python
"""
iHydroCal: Integrated Hydrological Model Calibration and Uncertainty Analysis.

A unified framework for calibration and uncertainty analysis of integrated 
hydrological models.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

__all__ = ["__version__"]
```

#### 📄 `ihydrocal/cli.py`
```python
"""Command-line interface for iHydroCal."""

import argparse
import sys
from . import __version__


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="iHydroCal - Integrated Hydrological Model Calibration"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"iHydroCal {__version__}",
    )
    
    args = parser.parse_args()
    
    if len(sys.argv) == 1:
        parser.print_help()
        return 0
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

```

#### 📄 `tests/__init__.py`
```python
"""Tests for iHydroCal."""
```

#### 📄 `tests/test_basic.py`
```python
"""Basic tests for iHydroCal."""

import ihydrocal


def test_version():
    """Test that version is defined."""
    assert hasattr(ihydrocal, "__version__")
    assert ihydrocal.__version__ == "0.0.0"


def test_import():
    """Test that package can be imported."""
    assert ihydrocal is not None
```

#### 📄 `conda.recipe/meta.yaml`
```yaml
{% set name = "ihydrocal" %}
{% set version = "0.0.0" %}

package:
  name: {{ name|lower }}
  version: {{ version }}

source:
  path: ..

build:
  number: 0
  noarch: python
  script: {{ PYTHON }} -m pip install . -vv
  entry_points:
    - ihydrocal = ihydrocal.cli:main

requirements:
  host:
    - python >=3.9
    - pip
    - setuptools >=61.0
    - wheel
  run:
    - python >=3.9
    - numpy >=1.26.0
    - pandas >=2.0.0
    - matplotlib-base >=3.8.0
    - scipy >=1.11.0
    - pyyaml >=6.0.0
    - pyemu >=1.2.0
    - flopy >=3.3.5

test:
  imports:
    - ihydrocal
  commands:
    - ihydrocal --help

about:
  home: https://github.com/yourusername/ihydrocal
  license: MIT
  license_family: MIT
  license_file: LICENSE
  summary: Integrated Hydrological Model Calibration and Uncertainty Analysis
  description: |
    iHydroCal provides a unified framework for calibration and uncertainty 
    analysis of integrated hydrological models including SWAT, SWAT+, 
    SWAT-MODFLOW, and APEX-MODFLOW-RT3D systems.
  dev_url: https://github.com/yourusername/ihydrocal

extra:
  recipe-maintainers:
    - spark-hydro
```

## Part 3: GitHub Actions Workflows (Using Conda)
#### 📄 `.github/workflows/tests.yml`
```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  workflow_dispatch:

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.11', '3.12', '3.13']

    steps:
    - uses: actions/checkout@v4

    - name: Setup Miniconda
      uses: conda-incubator/setup-miniconda@v3
      with:
        auto-update-conda: true
        python-version: ${{ matrix.python-version }}
        channels: conda-forge,defaults
        channel-priority: strict
        activate-environment: test-env

    - name: Install dependencies
      shell: bash -l {0}
      run: |
        conda install -y numpy pandas scipy matplotlib pyyaml pytest pytest-cov black flake8
        pip install pyemu flopy
        pip install -e .

    - name: Lint with flake8
      shell: bash -l {0}
      run: |
        flake8 ihydrocal --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 ihydrocal --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics

    - name: Check formatting with black
      shell: bash -l {0}
      run: |
        black --check ihydrocal tests

    - name: Run tests
      shell: bash -l {0}
      run: |
        pytest tests/ -v --cov=ihydrocal --cov-report=xml --cov-report=term

    - name: Upload coverage
      uses: codecov/codecov-action@v4
      with:
        file: ./coverage.xml
        fail_ci_if_error: false
```

#### 📄 `.github/workflows/publish-pypi.yml`
```yaml
name: Publish to PyPI

on:
  release:
    types: [published]
  workflow_dispatch:

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4

    - name: Setup Miniconda
      uses: conda-incubator/setup-miniconda@v3
      with:
        auto-update-conda: true
        python-version: '3.13'
        channels: conda-forge,defaults
        activate-environment: build-env

    - name: Install build tools
      shell: bash -l {0}
      run: |
        pip install build twine

    - name: Build package
      shell: bash -l {0}
      run: |
        python -m build

    - name: Check distribution
      shell: bash -l {0}
      run: |
        twine check dist/*

    - name: Publish to Test PyPI
      if: github.event_name == 'workflow_dispatch'
      shell: bash -l {0}
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.TEST_PYPI_API_TOKEN }}
      run: |
        twine upload --repository testpypi dist/*

    - name: Publish to PyPI
      if: github.event_name == 'release'
      shell: bash -l {0}
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: |
        twine upload dist/*
```

#### 📄 `.github/workflows/publish-conda.yml`
```yaml
name: Publish to Conda

on:
  release:
    types: [published]
  workflow_dispatch:

jobs:
  build-conda:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]

    steps:
    - uses: actions/checkout@v4

    - name: Setup Miniconda
      uses: conda-incubator/setup-miniconda@v3
      with:
        auto-update-conda: true
        python-version: '3.13'
        channels: conda-forge,defaults
        channel-priority: strict

    - name: Install conda-build
      shell: bash -l {0}
      run: |
        conda install -y conda-build anaconda-client

    - name: Build conda package
      shell: bash -l {0}
      run: |
        conda build conda.recipe --output-folder ./conda-bld

    - name: Upload to Anaconda (release)
      if: github.event_name == 'release'
      shell: bash -l {0}
      env:
        ANACONDA_API_TOKEN: ${{ secrets.ANACONDA_TOKEN }}
      run: |
        anaconda -t $ANACONDA_API_TOKEN upload --force ./conda-bld/noarch/ihydrocal-*.tar.bz2

    - name: Upload to Anaconda (test)
      if: github.event_name == 'workflow_dispatch'
      shell: bash -l {0}
      env:
        ANACONDA_API_TOKEN: ${{ secrets.ANACONDA_TOKEN }}
      run: |
        anaconda -t $ANACONDA_API_TOKEN upload --label test --force ./conda-bld/noarch/ihydrocal-*.tar.bz2
```

## Part 4: Local Development Setup
#### Now set up your local conda environment:

```bash
# Make sure you're in the ihydrocal directory
cd ihydrocal

# Create conda environment from environment.yml
conda env create -f environment.yml

# Activate the environment
conda activate ihydrocal

# Install your package in development mode
pip install -e .

# Verify installation
python --version
ihydrocal --version
pytest -v
```

## Part 5: Initialize Git and Push to GitHub
### Step 1: Initialize Git Locally

```bash
# Initialize git repository
git init

# Add all files
git add .

# Create first commit
git commit -m "Initial commit: Project structure with conda setup"
```

### Step 2: Create GitHub Repository
1. Go to [https://github.com/new](https://github.com/new)
2. Repository name: `ihydrocal`
3. Description: "Integrated Hydrological Model Calibration and Uncertainty Analysis"
4. Choose **Public** or **Private**
5. **Do NOT** initialize with README (you already have one)
6. Click "Create repository"

### Step 3: Push to GitHub
```bash
# Add remote (replace 'yourusername' with your GitHub username)
git remote add origin https://github.com/spark-hydro/ihydrocal.git

# Rename branch to main
git branch -M main

# Push to GitHub
git push -u origin main
```

## Part 6: Set Up GitHub Secrets
Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
Add these three secrets:
1. **PYPI_API_TOKEN**
    - Go to [https://pypi.org/manage/account/token/](https://pypi.org/manage/account/token/)
    - Create new token
    - Copy and paste into GitHub secret
2. **TEST_PYPI_API_TOKEN**
    - Go to [https://test.pypi.org/manage/account/token/](https://test.pypi.org/manage/account/token/)
    - Create new token
    - Copy and paste into GitHub secret
3. **ANACONDA_TOKEN**
    - Go to [https://anaconda.org/](https://anaconda.org/)
    - Sign up/login
    - Go to Settings → Access
    - Create new token
    - Copy and paste into GitHub secret

## Part 7: Test Everything
### Test Locally:

```bash
# Activate environment
conda activate ihydrocal

# Run tests
pytest -v

# Check formatting
black --check ihydrocal tests

# Format code
black ihydrocal tests

# Test CLI
ihydrocal --version

# Build locally
python -m build

# Check build
twine check dist/*
```

### Test on GitHub:
1. Push a commit to trigger tests:
```bash
git add .
git commit -m "Test CI/CD"
git push
```
2. Go to your repository → **Actions** tab
3. You should see the "Tests" workflow running

## Part 8: Publishing (When Ready)
### Test PyPI First (Manual):

```bash
# Build
python -m build

# Upload to Test PyPI
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ ihydrocal
```

### Publish via GitHub Release:
1. Go to your repository → **Releases** → **Create a new release**
2. Tag version: `v0.1.0`
3. Release title: `v0.1.0 - Initial Release`
4. Description: Write release notes
5. Click **Publish release**

This will automatically trigger:
- ✅ Build and publish to PyPI
- ✅ Build and publish to conda

## 🎯 Summary of What We Did

✅ Created complete project structure 
✅ Set up all configuration files for conda 
✅ Created GitHub Actions for testing, PyPI, and conda publishing 
✅ Used conda throughout (no venv confusion) 
✅ Ready for development and publishing

## 📝 Quick Reference Commands

```bash
# Daily development
conda activate ihydrocal
pytest
black ihydrocal tests

# Build locally
python -m build

# Publish manually
twine upload dist/*  # PyPI
conda build conda.recipe  # conda

# Or publish via GitHub release (automatic)
```

**You're all set!** 🎉 Let me know if you need help with any step or run into any issues!

