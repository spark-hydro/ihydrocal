# iHydroCal

**Integrated Hydrological Model Calibration and Uncertainty Analysis**

[![Tests](https://github.com/spark-hydro/ihydrocal/workflows/Tests/badge.svg)](https://github.com/spark-hydro/ihydrocal/actions)
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
git clone https://github.com/spark-hydro/ihydrocal.git
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
@software{ihydrocal,
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
- **Email**: spark.hydro.ml@gmail.com
- **GitHub**: [spark-hydro](https://github.com/spark-hydro)
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