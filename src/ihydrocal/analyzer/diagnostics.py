"""
Diagnostic plots for model evaluation.

This module provides model-independent plots for comparing observed,
simulated, and forcing variables such as precipitation.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .metrics import evaluate_metrics
from .hydrograph import plot_hydrograph_with_precip



def _prepare_xy(df, x_col, y_col):
    """Return clean x and y arrays after removing missing values."""
    clean = df[[x_col, y_col]].copy()
    clean = clean.replace([np.inf, -np.inf], np.nan)
    clean = clean.dropna()

    return clean[x_col].to_numpy(dtype=float), clean[y_col].to_numpy(dtype=float)


def plot_one_to_one(
    matched_df,
    x_col,
    y_col,
    xlabel=None,
    ylabel=None,
    title=None,
    figsize=(5, 5),
    show_metrics=True,
    save_path=None,
):
    """
    Plot a 1:1 scatter figure.

    Parameters
    ----------
    matched_df : pandas.DataFrame
        DataFrame containing the two variables to compare.

    x_col : str
        Column name for x-axis values.

    y_col : str
        Column name for y-axis values.

    xlabel, ylabel : str, optional
        Axis labels. If None, column names are used.

    title : str, optional
        Plot title.

    show_metrics : bool, default True
        If True, calculate metrics using x as observation and y as simulation.
        This is most meaningful for observed vs simulated discharge.

    save_path : str or Path, optional
        If provided, save figure to this path.

    Returns
    -------
    fig, ax, metrics
        Matplotlib figure, axis, and metrics dictionary.
    """

    x, y = _prepare_xy(matched_df, x_col, y_col)

    metrics = evaluate_metrics(x, y) if show_metrics else {}

    fig, ax = plt.subplots(figsize=figsize)

    ax.scatter(
        x,
        y,
        s=30,
        facecolors="none",
        edgecolors="red",
        linewidths=1.0,
    )

    # Draw 1:1 line.
    if len(x) > 0 and len(y) > 0:
        min_val = min(np.nanmin(x), np.nanmin(y))
        max_val = max(np.nanmax(x), np.nanmax(y))

        ax.plot(
            [min_val, max_val],
            [min_val, max_val],
            linestyle="--",
            linewidth=1.0,
            label="1:1 line",
        )

        ax.set_xlim(min_val, max_val)
        ax.set_ylim(min_val, max_val)

    ax.set_xlabel(xlabel or x_col)
    ax.set_ylabel(ylabel or y_col)

    if title is None:
        title = f"{y_col} vs {x_col}"

    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend()

    if show_metrics and metrics:
        metrics_text = (
            f"NSE = {metrics['NSE']:.2f}\n"
            f"KGE = {metrics['KGE']:.2f}\n"
            f"R² = {metrics['R2']:.2f}\n"
            f"PBIAS = {metrics['PBIAS']:.1f}%\n"
            f"RMSE = {metrics['RMSE']:.2f}"
        )

        ax.text(
            0.05,
            0.95,
            metrics_text,
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox={
                "boxstyle": "round",
                "facecolor": "white",
                "alpha": 0.8,
            },
        )

    fig.tight_layout()

    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")

    return fig, ax, metrics


def _minmax_normalize(values):
    """Normalize values to the 0–1 range."""

    values = np.asarray(values, dtype=float)

    vmin = np.nanmin(values)
    vmax = np.nanmax(values)

    if vmax == vmin:
        return np.full_like(values, np.nan, dtype=float)

    return (values - vmin) / (vmax - vmin)


def plot_normalized_response(
    matched_df,
    x_col,
    y_col,
    xlabel=None,
    ylabel=None,
    title=None,
    figsize=(5, 5),
    show_one_to_one=True,
    show_r2=True,
    save_path=None,
):
    """
    Plot normalized hydrologic response between two variables.

    Both variables are normalized to the 0–1 range before plotting.

    This is useful for comparing variables with different units,
    such as precipitation and discharge.

    Notes
    -----
    This is not a physical 1:1 comparison.
    The R² value only describes the linear association between the
    normalized variables.
    """

    df = matched_df[[x_col, y_col]].copy()
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()

    x_norm = _minmax_normalize(df[x_col])
    y_norm = _minmax_normalize(df[y_col])

    # Remove any NaNs that may come from constant-value normalization.
    valid = np.isfinite(x_norm) & np.isfinite(y_norm)
    x_norm = x_norm[valid]
    y_norm = y_norm[valid]

    if len(x_norm) >= 2:
        r = np.corrcoef(x_norm, y_norm)[0, 1]
        r2 = r**2
    else:
        r2 = np.nan

    fig, ax = plt.subplots(figsize=figsize)

    ax.scatter(
        x_norm,
        y_norm,
        s=30,
        facecolors="none",
        edgecolors="red",
        linewidths=1.0,
    )

    if show_one_to_one:
        ax.plot(
            [0, 1],
            [0, 1],
            linestyle="--",
            linewidth=1.0,
            label="1:1 reference",
        )

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax.set_xlabel(xlabel or f"Normalized {x_col}")
    ax.set_ylabel(ylabel or f"Normalized {y_col}")

    if title is None:
        title = f"Normalized response: {y_col} vs {x_col}"

    ax.set_title(title)
    ax.grid(True, alpha=0.3)

    if show_r2:
        ax.text(
            0.05,
            0.95,
            f"R² = {r2:.2f}",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=10,
            bbox={
                "boxstyle": "round",
                "facecolor": "white",
                "alpha": 0.8,
            },
        )

    if show_one_to_one:
        ax.legend()

    fig.tight_layout()

    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")

    return fig, ax, r2


def plot_flow_duration_curve(
    matched_df,
    obs_col,
    sim_col,
    title=None,
    xlabel="Exceedance Probability (%)",
    ylabel="Discharge (cms)",
    figsize=(6, 5),
    logy=True,
    save_path=None,
):
    """
    Plot flow duration curves for simulated and observed discharge.

    Parameters
    ----------
    matched_df : pandas.DataFrame
        DataFrame containing observed and simulated discharge columns.

    obs_col : str
        Observed discharge column.

    sim_col : str
        Simulated discharge column.

    title : str, optional
        Plot title.

    xlabel : str, default "Exceedance Probability (%)"
        X-axis label.

    ylabel : str, default "Discharge (cms)"
        Y-axis label.

    figsize : tuple, default (6, 5)
        Figure size.

    logy : bool, default False
        If True, use logarithmic y-axis.
        In this case, zero and negative values are removed automatically.

    save_path : str or Path, optional
        If provided, save figure to this path.

    Returns
    -------
    fig, ax
        Matplotlib figure and axis.
    """

    # Convert to clean numeric arrays
    obs = (
        matched_df[obs_col]
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
        .to_numpy(dtype=float)
    )

    sim = (
        matched_df[sim_col]
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
        .to_numpy(dtype=float)
    )

    # Log scale cannot handle zero or negative values.
    # So remove them only when log-scale FDC is requested.
    if logy:
        obs = obs[obs > 0]
        sim = sim[sim > 0]

    # Safety check
    if len(obs) == 0:
        raise ValueError(
            f"No valid observed values available for flow duration curve "
            f"after filtering column '{obs_col}'."
        )

    if len(sim) == 0:
        raise ValueError(
            f"No valid simulated values available for flow duration curve "
            f"after filtering column '{sim_col}'."
        )

    # Sort flows from high to low
    obs_sorted = np.sort(obs)[::-1]
    sim_sorted = np.sort(sim)[::-1]

    # Compute exceedance probability (%)
    obs_exc = np.arange(1, len(obs_sorted) + 1) / (len(obs_sorted) + 1) * 100
    sim_exc = np.arange(1, len(sim_sorted) + 1) / (len(sim_sorted) + 1) * 100

    fig, ax = plt.subplots(figsize=figsize)

    # Simulated = line
    ax.plot(
        sim_exc,
        sim_sorted,
        label="Simulated",
        linewidth=1.5,
    )

    # Observed = red open circles
    ax.scatter(
        obs_exc,
        obs_sorted,
        label="Observed",
        s=25,
        facecolors="none",
        edgecolors="red",
        linewidths=1.0,
    )

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    if title is None:
        title = f"Flow Duration Curve: {obs_col} vs {sim_col}"

    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend()

    if logy:
        ax.set_yscale("log")

    fig.tight_layout()

    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")

    return fig, ax


def plot_discharge_diagnostics(
    matched_df,
    obs_col=None,
    sim_col=None,
    pcp_col=None,
    site_channel_map=None,
    site_name=None,
    save_dir=None,
    log_fdc=False,
):
    """
    Create diagnostic plots for one site/channel pair or multiple pairs.

    This function can be used in two ways.

    Option 1: Single site/channel pair
        plot_discharge_diagnostics(
            matched_df,
            obs_col="08379500_obs",
            sim_col="ch001_sim",
            pcp_col="ch001_pcp_mm",
        )

    Option 2: Multiple site/channel pairs using site_channel_map
        site_channel_map = {
            "08379500": 1,
            "08380000": 25,
        }

        plot_discharge_diagnostics(
            matched_df,
            site_channel_map=site_channel_map,
        )

    Parameters
    ----------
    matched_df : pandas.DataFrame
        DataFrame containing observed discharge, simulated discharge,
        and precipitation.

    obs_col : str, optional
        Observed discharge column for a single site.

    sim_col : str, optional
        Simulated discharge column for a single channel.

    pcp_col : str, optional
        Precipitation column for a single channel.

    site_channel_map : dict, optional
        Dictionary mapping observed site numbers to SWAT+ channel IDs.

        Example:
            {
                "08379500": 1,
                "08380000": 25,
            }

    site_name : str, optional
        Site name for single-site mode.

    save_dir : str or Path, optional
        If provided, save figures to this folder.

    log_fdc : bool, default False
        If True, use log-scale y-axis for the flow duration curve.

    Returns
    -------
    dict
        Dictionary containing diagnostic plot results.
    """

    # ------------------------------------------------------------
    # Multi-site mode
    # ------------------------------------------------------------
    if site_channel_map is not None:
        all_results = {}

        for site_no, channel_id in site_channel_map.items():
            obs_col_i = f"{site_no}_obs"
            sim_col_i = f"ch{int(channel_id):03d}_sim"
            pcp_col_i = f"ch{int(channel_id):03d}_pcp_mm"
            site_name_i = f"USGS{site_no}_ch{int(channel_id):03d}"

            result_i = plot_discharge_diagnostics(
                matched_df=matched_df,
                obs_col=obs_col_i,
                sim_col=sim_col_i,
                pcp_col=pcp_col_i,
                site_name=site_name_i,
                save_dir=save_dir,
                log_fdc=log_fdc,
            )
            print(site_no)

            all_results[site_name_i] = result_i

        return all_results

    # ------------------------------------------------------------
    # Single-site mode
    # ------------------------------------------------------------
    if obs_col is None or sim_col is None or pcp_col is None:
        raise ValueError(
            "Provide either site_channel_map or all of obs_col, sim_col, and pcp_col."
        )

    if site_name is None:
        site_name = f"{obs_col}_{sim_col}"

    save_dir = Path(save_dir) if save_dir is not None else None

    def _save_path(name):
        if save_dir is None:
            return None
        return save_dir / f"{site_name}_{name}.png"

    results = {}

    # 0. Hydrograph with precipitation
    fig, axes, metrics_hydrograph = plot_hydrograph_with_precip(
        matched_df,
        obs_col=obs_col,
        sim_col=sim_col,
        pcp_col=pcp_col,
        title=f"{site_name}: Hydrograph with Precipitation",
        save_path=_save_path("hydrograph_pcp"),
    )

    results["hydrograph_pcp"] = {
        "fig": fig,
        "axes": axes,
        "metrics": metrics_hydrograph,
    }

    # 1. Simulated vs observed discharge
    fig, ax, metrics = plot_one_to_one(
        matched_df,
        x_col=obs_col,
        y_col=sim_col,
        xlabel="Observed discharge (cms)",
        ylabel="Simulated discharge (cms)",
        title=f"{site_name}: Simulated vs Observed Discharge",
        show_metrics=True,
        save_path=_save_path("sim_vs_obs"),
    )
    results["sim_vs_obs"] = {
        "fig": fig,
        "ax": ax,
        "metrics": metrics,
    }

   # 2. Normalized simulated discharge response to precipitation
    fig, ax, r2 = plot_normalized_response(
        matched_df,
        x_col=pcp_col,
        y_col=sim_col,
        xlabel="Normalized precipitation",
        ylabel="Normalized simulated discharge",
        title=f"{site_name}: Normalized Simulated Discharge Response to Precipitation",
        save_path=_save_path("sim_vs_pcp_normalized"),
    )

    results["sim_vs_pcp_normalized"] = {
        "fig": fig,
        "ax": ax,
        "r2": r2,
    }

    # 3. Normalized observed discharge response to precipitation
    fig, ax, r2 = plot_normalized_response(
        matched_df,
        x_col=pcp_col,
        y_col=obs_col,
        xlabel="Normalized precipitation",
        ylabel="Normalized observed discharge",
        title=f"{site_name}: Normalized Observed Discharge Response to Precipitation",
        save_path=_save_path("obs_vs_pcp_normalized"),
    )

    results["obs_vs_pcp_normalized"] = {
        "fig": fig,
        "ax": ax,
        "r2": r2,
    }

    # 4. Flow duration curve
    fig, ax = plot_flow_duration_curve(
        matched_df,
        obs_col=obs_col,
        sim_col=sim_col,
        title=f"{site_name}: Flow Duration Curve",
        logy=log_fdc,
        save_path=_save_path("fdc"),
    )
    results["fdc"] = {
        "fig": fig,
        "ax": ax,
    }

    return results