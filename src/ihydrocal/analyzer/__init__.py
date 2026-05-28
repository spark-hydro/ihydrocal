"""
Analyzer tools for iHydroCal.

This subpackage includes model-independent analysis and visualization tools.
"""

from .ua import plot_tseries_ensemble
from .ua import plot_parameter_ensemble
from .hydrograph import plot_hydrograph, plot_hydrograph_with_precip
from .metrics import evaluate_metrics, kge, nse, pbias, r_squared, rmse
from .precipitation import plot_precip_timeseries
from .diagnostics import (
    plot_one_to_one,
    plot_flow_duration_curve,
    plot_discharge_diagnostics,
    plot_normalized_response
)


__all__ = [
    "plot_tseries_ensemble",
    "plot_parameter_ensemble",
    "plot_hydrograph",
    "evaluate_metrics",
    "nse",
    "kge",
    "r_squared",
    "rmse",
    "pbias",
    "plot_precip_timeseries",
    "plot_hydrograph_with_precip",
    "plot_one_to_one",
    "plot_flow_duration_curve",
    "plot_discharge_diagnostics",
    "plot_normalized_response"
]
