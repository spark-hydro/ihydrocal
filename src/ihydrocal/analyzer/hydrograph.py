"""
Hydrograph plotting utilities.

This module provides plotting functions for comparing observed and simulated
streamflow time series.

Typical use:
    from ihydrocal.analyzer import plot_hydrograph

    fig, ax, metrics = plot_hydrograph(
        matched_df,
        obs_col="08379500_obs",
        sim_col="ch001_sim",
    )
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .metrics import evaluate_metrics


def plot_hydrograph(
    matched_df,
    obs_col,
    sim_col,
    date_col="date",
    title=None,
    ylabel="Discharge (cms)",
    figsize=(10, 4),
    show_metrics=True,
    obs_scatter=True,
    obs_line=False,
    obs_marker_size=30,
    save_path=None,
):
    """
    Plot observed and simulated hydrographs.

    Parameters
    ----------
    matched_df : pandas.DataFrame
        DataFrame containing date, observed values, and simulated values.

    obs_col : str
        Column name for observed data.

    sim_col : str
        Column name for simulated data.

    date_col : str, default "date"
        Column name for dates.

    title : str, optional
        Plot title.

    ylabel : str, default "Discharge (cms)"
        Y-axis label.

    figsize : tuple, default (10, 4)
        Figure size.

    show_metrics : bool, default True
        If True, show model performance metrics inside the plot.

    obs_scatter : bool, default True
        If True, plot observed values as open-circle scatter points.
        This is useful when observations have missing values.

    obs_line : bool, default False
        If True, plot observed values as a line.

    obs_marker_size : int or float, default 30
        Marker size for observed scatter points.

    save_path : str or Path, optional
        If provided, save the figure to this path.

    Returns
    -------
    fig : matplotlib.figure.Figure
        Matplotlib figure object.

    ax : matplotlib.axes.Axes
        Matplotlib axes object.

    metrics : dict
        Dictionary of model performance metrics.
    """

    # Copy dataframe so the original matched_df is not modified.
    df = matched_df.copy()

    # Make sure date column is datetime.
    df[date_col] = pd.to_datetime(df[date_col])

    # Keep only needed columns.
    df = df[[date_col, obs_col, sim_col]]

    # For metrics, use only dates where both obs and sim are available.
    metric_df = df.dropna(subset=[obs_col, sim_col])
    metrics = evaluate_metrics(metric_df[obs_col], metric_df[sim_col])

    # Create figure.
    fig, ax = plt.subplots(figsize=figsize)

    # Plot simulated flow first.
    ax.plot(
        df[date_col],
        df[sim_col],
        label="Simulated",
        linewidth=1.2,
        zorder=1
    )

    # Plot observed flow as a line if requested.
    if obs_line:
        ax.plot(
            df[date_col],
            df[obs_col],
            label="Observed",
            linewidth=1.0,
            zorder=2
        )

    # Plot observed flow as open-circle scatter if requested.
    if obs_scatter:
        obs_df = df.dropna(subset=[obs_col])

        ax.scatter(
            obs_df[date_col],
            obs_df[obs_col],
            label="Observed",
            s=obs_marker_size,
            facecolors="none",
            edgecolors="red",
            linewidths=1.0,
            alpha=0.3,
            zorder=2

        )

    ax.set_xlabel("Date")
    ax.set_ylabel(ylabel)

    if title is None:
        title = f"{obs_col} vs {sim_col}"

    ax.set_title(title)

    if show_metrics:
        metrics_text = (
            f"NSE = {metrics['NSE']:.2f}\n"
            f"KGE = {metrics['KGE']:.2f}\n"
            f"R² = {metrics['R2']:.2f}\n"
            f"PBIAS = {metrics['PBIAS']:.1f}%\n"
            f"RMSE = {metrics['RMSE']:.2f}"
        )

        ax.text(
            0.02,
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

    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()

    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")

    return fig, ax, metrics


from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .metrics import evaluate_metrics


def plot_hydrograph_with_precip(
    matched_df,
    obs_col,
    sim_col,
    pcp_col,
    date_col="date",
    title=None,
    discharge_ylabel="Discharge (cms)",
    precip_ylabel="Precipitation (mm)",
    figsize=(10, 6),
    show_metrics=True,
    obs_scatter=True,
    obs_line=False,
    obs_marker_size=30,
    invert_precip_axis=True,
    save_path=None,
):
    """
    Plot precipitation on the top panel and observed/simulated discharge
    on the bottom panel.

    Parameters
    ----------
    matched_df : pandas.DataFrame
        DataFrame containing date, observed discharge, simulated discharge,
        and precipitation.

    obs_col : str
        Column name for observed discharge.

    sim_col : str
        Column name for simulated discharge.

    pcp_col : str
        Column name for precipitation.

    date_col : str, default "date"
        Date column name.

    title : str, optional
        Main plot title.

    discharge_ylabel : str, default "Discharge (cms)"
        Y-axis label for discharge.

    precip_ylabel : str, default "Precipitation (mm)"
        Y-axis label for precipitation.

    figsize : tuple, default (10, 6)
        Figure size.

    show_metrics : bool, default True
        If True, show model performance metrics on the discharge panel.

    obs_scatter : bool, default True
        If True, plot observed discharge as open-circle scatter points.

    obs_line : bool, default False
        If True, plot observed discharge as a line.

    obs_marker_size : int or float, default 30
        Marker size for observed discharge scatter points.

    invert_precip_axis : bool, default True
        If True, invert precipitation axis so rainfall bars go downward.

    save_path : str or Path, optional
        If provided, save the figure.

    Returns
    -------
    fig : matplotlib.figure.Figure
        Figure object.

    axes : tuple
        (precipitation axis, discharge axis)

    metrics : dict
        Performance metrics for observed and simulated discharge.
    """

    df = matched_df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df[[date_col, obs_col, sim_col, pcp_col]]

    metric_df = df.dropna(subset=[obs_col, sim_col])
    metrics = evaluate_metrics(metric_df[obs_col], metric_df[sim_col])

    fig, (ax_p, ax_q) = plt.subplots(
        2,
        1,
        figsize=figsize,
        sharex=True,
        gridspec_kw={"height_ratios": [1, 3]},
    )

    # ------------------------------------------------------------
    # Top panel: precipitation
    # ------------------------------------------------------------
    ax_p.bar(
        df[date_col],
        df[pcp_col],
        width=1.0,
        label="Precipitation",
    )

    ax_p.set_ylabel(precip_ylabel)
    ax_p.grid(True, alpha=0.3)

    if invert_precip_axis:
        ax_p.invert_yaxis()

    # ------------------------------------------------------------
    # Bottom panel: discharge
    # ------------------------------------------------------------
    # Simulated first
    ax_q.plot(
        df[date_col],
        df[sim_col],
        label="Simulated",
        linewidth=1.2,
    )

    if obs_line:
        ax_q.plot(
            df[date_col],
            df[obs_col],
            label="Observed",
            linewidth=1.0,
        )

    if obs_scatter:
        obs_df = df.dropna(subset=[obs_col])

        ax_q.scatter(
            obs_df[date_col],
            obs_df[obs_col],
            label="Observed",
            s=obs_marker_size,
            facecolors="none",
            edgecolors="red",
            linewidths=1.0,
            alpha=0.3,
        )

    ax_q.set_ylabel(discharge_ylabel)
    ax_q.set_xlabel("Date")
    ax_q.grid(True, alpha=0.3)
    ax_q.legend()

    if title is None:
        title = f"{obs_col} vs {sim_col} with precipitation"

    ax_p.set_title(title)

    if show_metrics:
        metrics_text = (
            f"NSE = {metrics['NSE']:.2f}\n"
            f"KGE = {metrics['KGE']:.2f}\n"
            f"R² = {metrics['R2']:.2f}\n"
            f"PBIAS = {metrics['PBIAS']:.1f}%\n"
            f"RMSE = {metrics['RMSE']:.2f}"
        )

        ax_q.text(
            0.02,
            0.95,
            metrics_text,
            transform=ax_q.transAxes,
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

    return fig, (ax_p, ax_q), metrics


def plot_simulated_discharge_comparison(
    base_df,
    scenario_df,
    base_sim_col,
    scenario_sim_col,
    date_col="date",
    base_label="Base model",
    scenario_label="Point-source scenario",
    title=None,
    ylabel="Discharge (cms)",
    figsize=(10, 4),
    plot_difference=False,
    difference_label="Scenario - Base",
    save_path=None,
):
    """
    Compare simulated outlet discharge between a base model and a scenario model.

    This function is useful for comparing SWAT+ baseline simulation with a
    point-source or recall-object application scenario.

    Parameters
    ----------
    base_df : pandas.DataFrame
        DataFrame containing base model simulated discharge.

    scenario_df : pandas.DataFrame
        DataFrame containing scenario simulated discharge.

    base_sim_col : str
        Column name for base model simulated discharge.

    scenario_sim_col : str
        Column name for scenario simulated discharge.

    date_col : str, default "date"
        Date column name used in both dataframes.

    base_label : str, default "Base model"
        Legend label for the base model.

    scenario_label : str, default "Point-source scenario"
        Legend label for the scenario model.

    title : str, optional
        Plot title.

    ylabel : str, default "Discharge (cms)"
        Y-axis label.

    figsize : tuple, default (10, 4)
        Figure size.

    plot_difference : bool, default False
        If True, add a second panel showing scenario minus base discharge.

    difference_label : str, default "Scenario - Base"
        Label for the difference plot.

    save_path : str or pathlib.Path, optional
        If provided, save the figure.

    Returns
    -------
    fig : matplotlib.figure.Figure
        Figure object.

    axes : matplotlib.axes.Axes or tuple
        Axis object if plot_difference=False.
        Tuple of axes if plot_difference=True.

    comparison_df : pandas.DataFrame
        Merged dataframe containing base, scenario, and difference columns.
    """

    # ------------------------------------------------------------
    # Prepare base dataframe.
    # ------------------------------------------------------------
    base = base_df[[date_col, base_sim_col]].copy()
    base[date_col] = pd.to_datetime(base[date_col])
    base = base.rename(columns={base_sim_col: "base_sim"})

    # ------------------------------------------------------------
    # Prepare scenario dataframe.
    # ------------------------------------------------------------
    scenario = scenario_df[[date_col, scenario_sim_col]].copy()
    scenario[date_col] = pd.to_datetime(scenario[date_col])
    scenario = scenario.rename(columns={scenario_sim_col: "scenario_sim"})

    # ------------------------------------------------------------
    # Merge by date.
    # inner join keeps only dates available in both simulations.
    # ------------------------------------------------------------
    comparison_df = pd.merge(
        base,
        scenario,
        on=date_col,
        how="inner",
    )

    comparison_df["difference"] = (
        comparison_df["scenario_sim"] - comparison_df["base_sim"]
    )

    # ------------------------------------------------------------
    # Create figure.
    # ------------------------------------------------------------
    if plot_difference:
        fig, (ax_q, ax_d) = plt.subplots(
            2,
            1,
            figsize=(figsize[0], figsize[1] + 2),
            sharex=True,
            gridspec_kw={"height_ratios": [3, 1]},
        )
    else:
        fig, ax_q = plt.subplots(figsize=figsize)

    # ------------------------------------------------------------
    # Main hydrograph panel.
    # ------------------------------------------------------------
    ax_q.plot(
        comparison_df[date_col],
        comparison_df["base_sim"],
        label=base_label,
        linewidth=1.2,
    )

    ax_q.plot(
        comparison_df[date_col],
        comparison_df["scenario_sim"],
        label=scenario_label,
        linewidth=1.2,
    )

    ax_q.set_ylabel(ylabel)

    if title is None:
        title = "Simulated outlet discharge comparison"

    ax_q.set_title(title)
    ax_q.grid(True, alpha=0.3)
    ax_q.legend()

    # ------------------------------------------------------------
    # Optional difference panel.
    # ------------------------------------------------------------
    if plot_difference:
        ax_d.axhline(
            0.0,
            linewidth=0.8,
            color="black",
        )

        ax_d.plot(
            comparison_df[date_col],
            comparison_df["difference"],
            label=difference_label,
            linewidth=1.0,
        )

        ax_d.set_ylabel("Difference")
        ax_d.set_xlabel("Date")
        ax_d.grid(True, alpha=0.3)
        ax_d.legend()

        axes = (ax_q, ax_d)

    else:
        ax_q.set_xlabel("Date")
        axes = ax_q

    fig.tight_layout()

    # ------------------------------------------------------------
    # Save figure.
    # ------------------------------------------------------------
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")

    return fig, axes, comparison_df


def plot_simulated_fdc_comparison(
    base_df,
    scenario_df,
    base_sim_col,
    scenario_sim_col,
    date_col="date",
    base_label="Base model",
    scenario_label="Point-source scenario",
    title=None,
    ylabel="Discharge (cms)",
    figsize=(6, 5),
    logy=True,
    save_path=None,
):
    """
    Compare simulated outlet flow-duration curves between a base model
    and a scenario model.

    Parameters
    ----------
    base_df : pandas.DataFrame
        DataFrame containing base model simulated discharge.

    scenario_df : pandas.DataFrame
        DataFrame containing scenario simulated discharge.

    base_sim_col : str
        Column name for base model simulated discharge.

    scenario_sim_col : str
        Column name for scenario simulated discharge.

    date_col : str, default "date"
        Date column name used in both dataframes.

    base_label : str, default "Base model"
        Legend label for the base model.

    scenario_label : str, default "Point-source scenario"
        Legend label for the scenario model.

    title : str, optional
        Plot title.

    ylabel : str, default "Discharge (cms)"
        Y-axis label.

    figsize : tuple, default (6, 5)
        Figure size.

    logy : bool, default True
        If True, use log scale for discharge.

    save_path : str or pathlib.Path, optional
        If provided, save the figure.

    Returns
    -------
    fig : matplotlib.figure.Figure
        Figure object.

    ax : matplotlib.axes.Axes
        Axis object.

    fdc_df : pandas.DataFrame
        DataFrame containing exceedance probability and sorted flows.
    """

    # ------------------------------------------------------------
    # Prepare and merge data.
    # ------------------------------------------------------------
    base = base_df[[date_col, base_sim_col]].copy()
    base[date_col] = pd.to_datetime(base[date_col])
    base = base.rename(columns={base_sim_col: "base_sim"})

    scenario = scenario_df[[date_col, scenario_sim_col]].copy()
    scenario[date_col] = pd.to_datetime(scenario[date_col])
    scenario = scenario.rename(columns={scenario_sim_col: "scenario_sim"})

    df = pd.merge(
        base,
        scenario,
        on=date_col,
        how="inner",
    )

    # ------------------------------------------------------------
    # Helper function to calculate FDC.
    # ------------------------------------------------------------
    def _calculate_fdc(values):
        values = pd.Series(values)
        values = pd.to_numeric(values, errors="coerce").dropna()
        values = values.loc[values > -999]

        if logy:
            values = values.loc[values > 0]

        sorted_values = values.sort_values(ascending=False).to_numpy(dtype=float)
        n = len(sorted_values)

        exceedance = (
            pd.Series(range(1, n + 1), dtype=float) / (n + 1) * 100.0
        ).to_numpy()

        return exceedance, sorted_values

    x_base, y_base = _calculate_fdc(df["base_sim"])
    x_scen, y_scen = _calculate_fdc(df["scenario_sim"])

    # ------------------------------------------------------------
    # Create FDC dataframe.
    # Lengths should be same because merged dates are same,
    # but this keeps it safe.
    # ------------------------------------------------------------
    n = min(len(x_base), len(x_scen))

    fdc_df = pd.DataFrame(
        {
            "exceedance_probability": x_base[:n],
            "base_sim": y_base[:n],
            "scenario_sim": y_scen[:n],
            "difference": y_scen[:n] - y_base[:n],
        }
    )

    # ------------------------------------------------------------
    # Plot.
    # ------------------------------------------------------------
    fig, ax = plt.subplots(figsize=figsize)

    ax.plot(
        fdc_df["exceedance_probability"],
        fdc_df["base_sim"],
        label=base_label,
        linewidth=1.5,
    )

    ax.plot(
        fdc_df["exceedance_probability"],
        fdc_df["scenario_sim"],
        label=scenario_label,
        linewidth=1.5,
    )

    ax.set_xlabel("Exceedance probability (%)")
    ax.set_ylabel(ylabel)

    if title is None:
        title = "Simulated outlet flow-duration curve comparison"

    ax.set_title(title)

    ax.set_xlim(0, 100)

    if logy:
        ax.set_yscale("log")

    ax.grid(True, which="both", alpha=0.3)
    ax.legend()

    fig.tight_layout()

    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")

    return fig, ax, fdc_df