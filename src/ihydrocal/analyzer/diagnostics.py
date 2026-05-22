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


def plot_flow_duration_curve(
    matched_df,
    obs_col,
    sim_col,
    title=None,
    xlabel="Exceedance Probability (%)",
    ylabel="Discharge (cms)",
    figsize=(6, 5),
    logy=False,
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

    logy : bool, default False
        If True, use logarithmic y-axis.

    Returns
    -------
    fig, ax
        Matplotlib figure and axis.
    """

    obs = matched_df[obs_col].replace([np.inf, -np.inf], np.nan).dropna().to_numpy(dtype=float)
    sim = matched_df[sim_col].replace([np.inf, -np.inf], np.nan).dropna().to_numpy(dtype=float)

    # Sort flows from high to low.
    obs_sorted = np.sort(obs)[::-1]
    sim_sorted = np.sort(sim)[::-1]

    # Exceedance probability.
    obs_exc = np.arange(1, len(obs_sorted) + 1) / (len(obs_sorted) + 1) * 100
    sim_exc = np.arange(1, len(sim_sorted) + 1) / (len(sim_sorted) + 1) * 100

    fig, ax = plt.subplots(figsize=figsize)

    # Simulated as line.
    ax.plot(
        sim_exc,
        sim_sorted,
        label="Simulated",
        linewidth=1.5,
    )

    # Observed as red open circles.
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
    obs_col,
    sim_col,
    pcp_col,
    site_name=None,
    save_dir=None,
):
    """
    Create four diagnostic plots:

    1. Simulated discharge vs observed discharge
    2. Simulated discharge vs precipitation
    3. Observed discharge vs precipitation
    4. Flow duration curve for simulated and observed discharge

    Parameters
    ----------
    matched_df : pandas.DataFrame
        DataFrame containing observed discharge, simulated discharge,
        and precipitation.

    obs_col : str
        Observed discharge column.

    sim_col : str
        Simulated discharge column.

    pcp_col : str
        Precipitation column.

    site_name : str, optional
        Name used in plot titles and file names.

    save_dir : str or Path, optional
        If provided, save all figures to this folder.

    Returns
    -------
    dict
        Dictionary containing figures, axes, and metrics.
    """

    if site_name is None:
        site_name = f"{obs_col}_{sim_col}"

    save_dir = Path(save_dir) if save_dir is not None else None

    def _save_path(name):
        if save_dir is None:
            return None
        return save_dir / f"{site_name}_{name}.png"

    results = {}

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
    results["sim_vs_obs"] = {"fig": fig, "ax": ax, "metrics": metrics}

    # 2. Simulated discharge vs precipitation
    fig, ax, _ = plot_one_to_one(
        matched_df,
        x_col=pcp_col,
        y_col=sim_col,
        xlabel="Precipitation (mm)",
        ylabel="Simulated discharge (cms)",
        title=f"{site_name}: Simulated Discharge vs Precipitation",
        show_metrics=False,
        save_path=_save_path("sim_vs_pcp"),
    )
    results["sim_vs_pcp"] = {"fig": fig, "ax": ax}

    # 3. Observed discharge vs precipitation
    fig, ax, _ = plot_one_to_one(
        matched_df,
        x_col=pcp_col,
        y_col=obs_col,
        xlabel="Precipitation (mm)",
        ylabel="Observed discharge (cms)",
        title=f"{site_name}: Observed Discharge vs Precipitation",
        show_metrics=False,
        save_path=_save_path("obs_vs_pcp"),
    )
    results["obs_vs_pcp"] = {"fig": fig, "ax": ax}

    # 4. Flow duration curve
    fig, ax = plot_flow_duration_curve(
        matched_df,
        obs_col=obs_col,
        sim_col=sim_col,
        title=f"{site_name}: Flow Duration Curve",
        save_path=_save_path("fdc"),
    )
    results["fdc"] = {"fig": fig, "ax": ax}

    return results