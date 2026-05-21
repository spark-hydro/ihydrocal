"""
iHydroCal: Integrated Hydrological Model Calibration and Uncertainty Analysis.

A unified framework for calibration and uncertainty analysis of integrated
hydrological models.
"""

from ihydrocal.core import create_model, available_models

__version__ = "0.0.0b3"

# Import model modules so they register themselves
from ihydrocal import models  # noqa: F401

__all__ = [
    "create_model",
    "available_models",
    "__version__",
]
