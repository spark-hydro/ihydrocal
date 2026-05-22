"""
Hydrologic model performance metrics.

This module provides commonly used objective functions for comparing
observed and simulated hydrologic variables, such as streamflow.

The functions are intentionally written to be:
1. Model-independent
   - They can be used for SWAT, SWAT+, SWAT+gwflow, SWAT-MODFLOW,
     APEX, DayCent, or any other model.

2. NaN-safe
   - Missing values are removed before metric calculation.

3. Simple to use in notebooks and scripts
   - Example:
       from ihydrocal.analyzer import evaluate_metrics

       metrics = evaluate_metrics(obs, sim)
"""

import numpy as np


def _clean_obs_sim(obs, sim):
    """
    Convert observed and simulated data to NumPy arrays and remove invalid values.

    Parameters
    ----------
    obs : array-like
        Observed values.
    sim : array-like
        Simulated values.

    Returns
    -------
    obs_clean : numpy.ndarray
        Observed values after removing NaN/inf values.
    sim_clean : numpy.ndarray
        Simulated values after removing NaN/inf values.

    Notes
    -----
    This helper function removes any pair where either observed or simulated
    value is NaN or infinite. This is important because hydrologic datasets
    often contain missing observations.
    """

    obs = np.asarray(obs, dtype=float)
    sim = np.asarray(sim, dtype=float)

    if len(obs) != len(sim):
        raise ValueError("Observed and simulated data must have the same length.")

    mask = np.isfinite(obs) & np.isfinite(sim)

    return obs[mask], sim[mask]


def nse(obs, sim):
    """
    Calculate Nash-Sutcliffe Efficiency (NSE).

    NSE measures how well the simulated time series matches the observed
    time series. NSE = 1 is perfect. NSE = 0 means the model is as good as
    using the observed mean. NSE < 0 means the model is worse than using
    the observed mean.

    Parameters
    ----------
    obs : array-like
        Observed values.
    sim : array-like
        Simulated values.

    Returns
    -------
    float
        Nash-Sutcliffe Efficiency.
    """

    obs, sim = _clean_obs_sim(obs, sim)

    if len(obs) == 0:
        return np.nan

    denominator = np.sum((obs - np.mean(obs)) ** 2)

    if denominator == 0:
        return np.nan

    numerator = np.sum((obs - sim) ** 2)

    return 1 - numerator / denominator


def rmse(obs, sim):
    """
    Calculate Root Mean Squared Error (RMSE).

    RMSE has the same unit as the variable being evaluated.
    For streamflow in cms, RMSE is also in cms.

    Parameters
    ----------
    obs : array-like
        Observed values.
    sim : array-like
        Simulated values.

    Returns
    -------
    float
        Root Mean Squared Error.
    """

    obs, sim = _clean_obs_sim(obs, sim)

    if len(obs) == 0:
        return np.nan

    return np.sqrt(np.mean((obs - sim) ** 2))


def pbias(obs, sim):
    """
    Calculate Percent Bias (PBIAS).

    PBIAS indicates whether the model tends to overestimate or underestimate.

    In this convention:
        PBIAS > 0 means simulated values are higher than observed values.
        PBIAS < 0 means simulated values are lower than observed values.

    Parameters
    ----------
    obs : array-like
        Observed values.
    sim : array-like
        Simulated values.

    Returns
    -------
    float
        Percent bias.
    """

    obs, sim = _clean_obs_sim(obs, sim)

    if len(obs) == 0:
        return np.nan

    obs_sum = np.sum(obs)

    if obs_sum == 0:
        return np.nan

    return 100 * np.sum(sim - obs) / obs_sum


def kge(obs, sim):
    """
    Calculate Kling-Gupta Efficiency (KGE).

    KGE evaluates model performance using three components:
        1. Correlation
        2. Variability ratio
        3. Bias ratio

    KGE = 1 is perfect.

    Parameters
    ----------
    obs : array-like
        Observed values.
    sim : array-like
        Simulated values.

    Returns
    -------
    float
        Kling-Gupta Efficiency.
    """

    obs, sim = _clean_obs_sim(obs, sim)

    if len(obs) < 2:
        return np.nan

    obs_std = np.std(obs)
    sim_std = np.std(sim)
    obs_mean = np.mean(obs)

    if obs_std == 0 or obs_mean == 0:
        return np.nan

    r = np.corrcoef(obs, sim)[0, 1]
    alpha = sim_std / obs_std
    beta = np.mean(sim) / obs_mean

    return 1 - np.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2)


def r_squared(obs, sim):
    """
    Calculate coefficient of determination, R².

    Parameters
    ----------
    obs : array-like
        Observed values.
    sim : array-like
        Simulated values.

    Returns
    -------
    float
        R-squared value.
    """

    obs, sim = _clean_obs_sim(obs, sim)

    if len(obs) < 2:
        return np.nan

    r = np.corrcoef(obs, sim)[0, 1]

    return r**2


def evaluate_metrics(obs, sim):
    """
    Calculate multiple hydrologic performance metrics.

    Parameters
    ----------
    obs : array-like
        Observed values.
    sim : array-like
        Simulated values.

    Returns
    -------
    dict
        Dictionary containing NSE, KGE, R2, RMSE, and PBIAS.

    Example
    -------
    >>> metrics = evaluate_metrics(observed_flow, simulated_flow)
    >>> metrics["NSE"]
    0.76
    """

    return {
        "NSE": nse(obs, sim),
        "KGE": kge(obs, sim),
        "R2": r_squared(obs, sim),
        "RMSE": rmse(obs, sim),
        "PBIAS": pbias(obs, sim),
    }