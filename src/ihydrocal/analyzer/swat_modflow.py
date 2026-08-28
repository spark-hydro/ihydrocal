from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter

from .metrics import evaluate_metrics

def _safe_tight_layout(fig):
    """Call tight_layout only when the figure object supports it."""
    if hasattr(fig, "tight_layout"):
        fig.tight_layout()


def _save_figure(fig, save_path):
    if save_path is None:
        return
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=300, bbox_inches="tight")


def _metrics_text(metrics):
    return (
        f"NSE = {metrics['NSE']:.2f}\n"
        f"KGE = {metrics['KGE']:.2f}\n"
        f"R² = {metrics['R2']:.2f}\n"
        f"PBIAS = {metrics['PBIAS']:.1f}%\n"
        f"RMSE = {metrics['RMSE']:.2f}"
    )


def _clean_timeseries(df, date_col, columns):
    out = df[[date_col, *columns]].copy()
    out[date_col] = pd.to_datetime(out[date_col])
    return out.replace([np.inf, -np.inf], np.nan)


def _aggregate_timeseries(df, date_col, value_cols, aggregate=None, aggregate_func="mean"):
    """Optionally aggregate time series data to monthly or annual values."""

    if aggregate is None:
        return df

    freq_map = {
        "monthly": "ME",
        "month": "ME",
        "M": "ME",
        "annual": "A",
        "yearly": "A",
        "year": "A",
        "Y": "A",
        "A": "A",
    }

    if aggregate not in freq_map:
        raise ValueError(
            "aggregate must be one of None, 'monthly', 'month', 'M', "
            "'annual', 'yearly', 'year', 'Y', or 'A'."
        )

    out = df[[date_col, *value_cols]].copy()
    out[date_col] = pd.to_datetime(out[date_col])
    out = out.set_index(date_col)
    out = out.resample(freq_map[aggregate]).agg(aggregate_func)
    return out.reset_index()


def plot_swatmf_streamflow(
    streamflow_df,
    obs_col,
    sim_col="stf_sim",
    date_col="date",
    precip_df=None,
    precip_col="precip",
    aggregate=None,
    aggregate_func="mean",
    precip_aggregate_func="sum",
    title=None,
    ylabel="Stream discharge",
    figsize=(11, 4),
    show_metrics=True,
    obs_scatter=True,
    obs_line=True,
    save_path=None,
    ax=None,
):
    """Plot SWAT-MODFLOW simulated and observed streamflow.

    Parameters
    ----------
    streamflow_df : pandas.DataFrame
        DataFrame with date, simulated streamflow, and observed streamflow.
    obs_col : str
        Observed streamflow column.
    sim_col : str, default "stf_sim"
        Simulated streamflow column.
    precip_df : pandas.DataFrame, optional
        Optional precipitation dataframe with date and precipitation columns.
    aggregate : str, optional
        Optional time aggregation. Use "monthly" for monthly average analysis.
    aggregate_func : str or callable, default "mean"
        Aggregation function for simulated and observed streamflow.
    precip_aggregate_func : str or callable, default "sum"
        Aggregation function for precipitation if precip_df is supplied.
    ax : matplotlib.axes.Axes, optional
        Existing axis. If omitted, a new figure is created.
    """

    df = _clean_timeseries(streamflow_df, date_col, [sim_col, obs_col])
    df = _aggregate_timeseries(
        df,
        date_col=date_col,
        value_cols=[sim_col, obs_col],
        aggregate=aggregate,
        aggregate_func=aggregate_func,
    )
    metrics_df = df.dropna(subset=[sim_col, obs_col])
    metrics = evaluate_metrics(metrics_df[obs_col], metrics_df[sim_col])

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    ax.plot(df[date_col], df[sim_col], color="limegreen", lw=1.2, label="Simulated")

    if obs_line:
        ax.plot(
            df[date_col],
            df[obs_col],
            color="red",
            lw=1.0,
            alpha=0.45,
            label="Observed",
        )

    if obs_scatter:
        obs_df = df.dropna(subset=[obs_col])
        ax.scatter(
            obs_df[date_col],
            obs_df[obs_col],
            facecolors="none",
            edgecolors="red",
            linewidths=1.0,
            alpha=0.35,
            s=24,
            label="Observed points" if obs_line else "Observed",
            zorder=3,
        )

    if precip_df is not None:
        pcp = precip_df[[date_col, precip_col]].copy()
        pcp[date_col] = pd.to_datetime(pcp[date_col])
        pcp = _aggregate_timeseries(
            pcp,
            date_col=date_col,
            value_cols=[precip_col],
            aggregate=aggregate,
            aggregate_func=precip_aggregate_func,
        )
        ax_p = ax.twinx()
        ax_p.bar(
            pcp[date_col],
            pcp[precip_col],
            width=1.0,
            color="tab:blue",
            alpha=0.22,
            label="Precipitation",
        )
        ax_p.set_ylabel("Precipitation (mm)", color="tab:blue")
        ax_p.tick_params(axis="y", labelcolor="tab:blue")
        ax_p.invert_yaxis()
        if pcp[precip_col].notna().any():
            ax_p.set_ylim(float(pcp[precip_col].max()) * 3.0, 0)

    if title is None:
        title = f"{obs_col} streamflow"
        if aggregate in {"monthly", "month", "M"}:
            title = f"{obs_col} monthly streamflow"
        elif aggregate in {"annual", "yearly", "year", "Y", "A"}:
            title = f"{obs_col} annual streamflow"

    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")

    if show_metrics:
        ax.text(
            0.02,
            0.95,
            _metrics_text(metrics),
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8},
        )

    _safe_tight_layout(fig)
    _save_figure(fig, save_path)
    return fig, ax, metrics


def _fdc_values(values):
    values = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan)
    values = values.dropna().sort_values(ascending=False).to_numpy()

    if len(values) == 0:
        return np.array([]), np.array([])

    exceedance = np.arange(1, len(values) + 1) / (len(values) + 1) * 100.0
    return exceedance, values


def plot_swatmf_fdc(
    streamflow_df,
    obs_col,
    sim_col="stf_sim",
    title=None,
    xlabel="Exceedance probability (%)",
    ylabel="Stream discharge",
    figsize=(6, 5),
    logy=True,
    save_path=None,
    ax=None,
):
    """Plot observed and simulated flow duration curves."""

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    sim_x, sim_y = _fdc_values(streamflow_df[sim_col])
    obs_x, obs_y = _fdc_values(streamflow_df[obs_col])

    ax.plot(sim_x, sim_y, color="limegreen", lw=1.5, label="Simulated")
    ax.plot(obs_x, obs_y, color="red", lw=1.2, alpha=0.65, label="Observed")

    if logy:
        positive = pd.concat(
            [
                pd.Series(streamflow_df[sim_col], dtype="float64"),
                pd.Series(streamflow_df[obs_col], dtype="float64"),
            ]
        )
        if (positive > 0).any():
            ax.set_yscale("log")

    if title is None:
        title = f"{obs_col} flow duration curve"

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()

    _safe_tight_layout(fig)
    _save_figure(fig, save_path)

    fdc_data = {
        "sim_exceedance": sim_x,
        "sim_flow": sim_y,
        "obs_exceedance": obs_x,
        "obs_flow": obs_y,
    }
    return fig, ax, fdc_data


def plot_swatmf_dtw(
    gw_sim_df,
    sim_col,
    gw_obs_df,
    obs_col,
    date_col="date",
    precip_df=None,
    precip_col="precip",
    aggregate=None,
    aggregate_func="mean",
    precip_aggregate_func="sum",
    title=None,
    ylabel="Depth to water table",
    figsize=(10, 3),
    show_metrics=True,
    save_path=None,
    ax=None,
):
    """Plot simulated and observed depth to water table for one observation."""

    sim = gw_sim_df[[date_col, sim_col]].copy()
    obs = gw_obs_df[[date_col, obs_col]].copy()
    sim[date_col] = pd.to_datetime(sim[date_col])
    obs[date_col] = pd.to_datetime(obs[date_col])

    df = pd.merge(sim, obs, on=date_col, how="outer")
    df = df.replace([np.inf, -np.inf], np.nan)
    df = _aggregate_timeseries(
        df,
        date_col=date_col,
        value_cols=[sim_col, obs_col],
        aggregate=aggregate,
        aggregate_func=aggregate_func,
    )
    metric_df = df.dropna(subset=[sim_col, obs_col])
    metrics = evaluate_metrics(metric_df[obs_col], metric_df[sim_col])

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    ax.plot(df[date_col], df[sim_col], c="skyblue", lw=1.2, label="Simulated")
    ax.plot(
        df[date_col],
        df[obs_col],
        c="m",
        lw=1.2,
        alpha=0.6,
        label="Observed",
        zorder=3,
    )

    if precip_df is not None:
        pcp = precip_df[[date_col, precip_col]].copy()
        pcp[date_col] = pd.to_datetime(pcp[date_col])
        pcp = _aggregate_timeseries(
            pcp,
            date_col=date_col,
            value_cols=[precip_col],
            aggregate=aggregate,
            aggregate_func=precip_aggregate_func,
        )
        ax_p = ax.twinx()
        ax_p.bar(
            pcp[date_col],
            pcp[precip_col],
            width=1.0,
            color="tab:blue",
            alpha=0.18,
        )
        ax_p.set_ylabel("Precipitation (mm)", color="tab:blue")
        ax_p.tick_params(axis="y", labelcolor="tab:blue")
        ax_p.invert_yaxis()
        if pcp[precip_col].notna().any():
            ax_p.set_ylim(float(pcp[precip_col].max()) * 3.0, 0)

    if title is None:
        title = f"{sim_col} vs {obs_col}"
        if aggregate in {"monthly", "month", "M"}:
            title = f"Monthly DTW: {sim_col} vs {obs_col}"
        elif aggregate in {"annual", "yearly", "year", "Y", "A"}:
            title = f"Annual DTW: {sim_col} vs {obs_col}"

    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right")

    if show_metrics and len(metric_df) > 1:
        ax.text(
            0.02,
            0.95,
            _metrics_text(metrics),
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=8,
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8},
        )

    _safe_tight_layout(fig)
    _save_figure(fig, save_path)
    return fig, ax, metrics


def plot_swatmf_water_balance(
    water_balance_df,
    date_col="date",
    timestep="month",
    title="SWAT-MODFLOW water balance",
    figsize=(11, 7),
    width_exg=1,
    cutcolor="k",
    save_path=None,
    axes=None,
):
    """Plot selected water balance terms from SWAT-MODFLOW output.std.

    This follows the legacy SWAT-MODFLOW stacked bar style:
    precipitation on top, soil water and streamflow components in the middle,
    aquifer exchange terms below zero, and groundwater storage on the bottom.
    """

    df = water_balance_df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col)

    if "precip" in df.columns and "prec" not in df.columns:
        df = df.rename(columns={"precip": "prec"})

    if timestep in {"month", "M", "ME"}:
        df = df.resample("ME").mean()
    elif timestep in {"year", "Y", "YE"}:
        df = df.resample("A").mean()

    required = ["prec", "sw", "gwq", "latq", "surq", "swgw", "perco", "gw"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise KeyError(
            "water_balance_df is missing required columns: "
            + ", ".join(missing)
        )

    if axes is None:
        fig, axes = plt.subplots(
            4,
            1,
            figsize=figsize,
            sharex=True,
            gridspec_kw={
                "height_ratios": [0.2, 0.2, 0.4, 0.2],
                "hspace": 0.1,
            },
        )
    else:
        axes = list(axes)
        fig = axes[0].figure

    width = -20 * width_exg
    stream_total = df["gwq"] + df["latq"] + df["surq"]
    soil_total = stream_total + df["sw"]
    aquifer_exchange = df["swgw"] + df["perco"]
    aquifer_total = df["gw"] + df["perco"] + df["swgw"]

    axes[0].bar(
        df.index,
        df["prec"],
        width,
        align="edge",
        color="slateblue",
    )
    if df["prec"].notna().any():
        axes[0].set_ylim(float(df["prec"].max()) * 1.1, 0)
    axes[0].xaxis.tick_top()
    axes[0].spines["bottom"].set_visible(False)
    axes[0].tick_params(axis="both", labelsize=8)

    axes[1].spines["top"].set_visible(False)
    axes[1].spines["bottom"].set_visible(False)
    axes[1].get_xaxis().set_visible(False)
    axes[1].bar(
        df.index,
        df["sw"],
        width,
        bottom=stream_total,
        align="edge",
        color="lightgreen",
    )
    axes[1].set_ylim(stream_total.max(), soil_total.max())
    axes[1].tick_params(axis="both", labelsize=8)

    axes[2].spines["top"].set_visible(False)
    axes[2].spines["bottom"].set_visible(False)
    axes[2].get_xaxis().set_visible(False)
    axes[2].bar(df.index, df["gwq"], width, align="edge", color="darkgreen")
    axes[2].bar(
        df.index,
        df["latq"],
        width,
        bottom=df["gwq"],
        align="edge",
        color="forestgreen",
    )
    axes[2].bar(
        df.index,
        df["surq"],
        width,
        bottom=df["latq"] + df["gwq"],
        align="edge",
        color="limegreen",
    )
    axes[2].bar(
        df.index,
        df["sw"],
        width,
        bottom=stream_total,
        align="edge",
        color="lightgreen",
    )
    axes[2].axhline(y=0, xmin=0, xmax=1, lw=0.3, ls="--", c="grey")
    axes[2].bar(
        df.index,
        df["swgw"] * -1,
        width,
        align="edge",
        color="b",
    )
    axes[2].bar(
        df.index,
        df["perco"] * -1,
        width,
        bottom=df["swgw"] * -1,
        align="edge",
        color="dodgerblue",
    )
    axes[2].bar(
        df.index,
        df["gw"] * -1,
        width,
        bottom=(df["perco"] * -1) + (df["swgw"] * -1),
        color="skyblue",
        align="edge",
    )
    axes[2].set_ylim(-1 * aquifer_exchange.max(), stream_total.max())
    axes[2].tick_params(axis="both", labelsize=8)
    axes[2].yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{abs(x):g}"))

    axes[3].bar(
        df.index,
        df["gw"],
        width,
        bottom=df["perco"] + df["swgw"],
        color="skyblue",
        align="edge",
    )
    axes[3].set_ylim(aquifer_total.max(), aquifer_total.min())
    axes[3].spines["top"].set_visible(False)
    axes[3].tick_params(axis="both", labelsize=8)
    axes[3].set_xlabel("Date")

    d = 0.003
    kwargs = dict(transform=axes[1].transAxes, color=cutcolor, clip_on=False)
    axes[1].plot((-d, +d), (-d, +d), **kwargs)
    axes[1].plot((1 - d, 1 + d), (-d, +d), **kwargs)
    kwargs.update(transform=axes[2].transAxes)
    axes[2].plot((-d, +d), (-d, +d), **kwargs)
    axes[2].plot((1 - d, 1 + d), (-d, +d), **kwargs)
    axes[2].plot((-d, +d), (1 - d, 1 + d), **kwargs)
    axes[2].plot((1 - d, 1 + d), (1 - d, 1 + d), **kwargs)
    kwargs.update(transform=axes[3].transAxes)
    axes[3].plot((-d, +d), (1 - d, 1 + d), **kwargs)
    axes[3].plot((1 - d, 1 + d), (1 - d, 1 + d), **kwargs)

    names = (
        "Precipitation",
        "Soil Water",
        "Surface Runoff",
        "Lateral Flow",
        "Groundwater Flow to Stream",
        "Seepage from Stream to Aquifer",
        "Deep Percolation to Aquifer",
        "Groundwater Volume",
    )
    colors = (
        "slateblue",
        "lightgreen",
        "limegreen",
        "forestgreen",
        "darkgreen",
        "b",
        "dodgerblue",
        "skyblue",
    )
    handles = [Rectangle((0, 0), 0.1, 0.1, fc=color, alpha=1) for color in colors]
    legend = axes[0].legend(
        handles,
        names,
        loc="upper left",
        edgecolor="none",
        fontsize=8,
        bbox_to_anchor=(-0.02, 1.8),
        ncol=4,
    )
    legend._legend_box.align = "left"
    for text in legend.texts:
        text.set_multialignment("left")

    for ax in axes:
        ax.grid(True, alpha=0.3)

    # fig.suptitle(title)
    _safe_tight_layout(fig)
    _save_figure(fig, save_path)
    return fig, axes, df.reset_index()


def plot_swatmf_performance_dashboard(
    streamflow_df,
    streamflow_obs_col,
    water_balance_df,
    gw_sim_df=None,
    gw_obs_df=None,
    gw_pairs=None,
    streamflow_sim_col="stf_sim",
    precip_df=None,
    date_col="date",
    figsize=(12, 10),
    title="SWAT-MODFLOW model performance",
    save_path=None,
):
    """Create a compact dashboard for streamflow, DTW, FDC, and water balance."""

    gw_pairs = gw_pairs or []
    n_gw = min(len(gw_pairs), 4)
    nrows = 2 + n_gw + 4

    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(
        nrows,
        1,
        height_ratios=[1.5, 1.3, *([1.2] * n_gw), 0.9, 0.9, 1.2, 0.9],
    )

    ax_stf = fig.add_subplot(gs[0])
    _, _, stream_metrics = plot_swatmf_streamflow(
        streamflow_df,
        obs_col=streamflow_obs_col,
        sim_col=streamflow_sim_col,
        date_col=date_col,
        precip_df=precip_df,
        title="Streamflow",
        ax=ax_stf,
    )

    ax_fdc = fig.add_subplot(gs[1])
    _, _, fdc_data = plot_swatmf_fdc(
        streamflow_df,
        obs_col=streamflow_obs_col,
        sim_col=streamflow_sim_col,
        title="Flow duration curve",
        ax=ax_fdc,
    )

    gw_metrics = {}
    for i, (sim_col, obs_col) in enumerate(gw_pairs[:n_gw]):
        ax = fig.add_subplot(gs[2 + i])
        _, _, metrics = plot_swatmf_dtw(
            gw_sim_df,
            sim_col=sim_col,
            gw_obs_df=gw_obs_df,
            obs_col=obs_col,
            date_col=date_col,
            title=f"DTW: {sim_col} vs {obs_col}",
            ax=ax,
        )
        gw_metrics[(sim_col, obs_col)] = metrics

    wb_start = 2 + n_gw
    wb_axes = [fig.add_subplot(gs[wb_start + i]) for i in range(4)]
    _, _, wb_data = plot_swatmf_water_balance(
        water_balance_df,
        date_col=date_col,
        title="Water balance",
        axes=wb_axes,
    )

    fig.suptitle(title, y=0.995)
    _safe_tight_layout(fig)
    _save_figure(fig, save_path)

    results = {
        "streamflow_metrics": stream_metrics,
        "gw_metrics": gw_metrics,
        "fdc_data": fdc_data,
        "water_balance": wb_data,
    }
    return fig, results


def plot_swatmf_performance_dashboard_subfigures(
    streamflow_df,
    streamflow_obs_col,
    water_balance_df,
    gw_sim_df=None,
    gw_obs_df=None,
    gw_pairs=None,
    streamflow_sim_col="stf_sim",
    precip_df=None,
    date_col="date",
    aggregate=None,
    water_balance_timestep="month",
    figsize=(10, 10),
    height_ratios=(0.18, 0.16, 0.18, 0.18, 0.3),
    gw_wspace=0.05,
    title="SWAT-MODFLOW model performance",
    save_path=None,
):
    """Create a SWAT-MODFLOW dashboard using nested subfigures.

    This layout follows the legacy workflow:
    one streamflow panel, one FDC panel, four optional DTW panels in a 2x2
    arrangement, and the stacked-bar water balance plot as the bottom subfigure.
    """

    gw_pairs = gw_pairs or []
    gw_pairs = gw_pairs[:4]

    fig = plt.figure(figsize=figsize)
    subfigs = fig.subfigures(
        5,
        1,
        height_ratios=height_ratios,
    )

    ax_stream = subfigs[0].subplots(1, 1)
    _, _, stream_metrics = plot_swatmf_streamflow(
        streamflow_df,
        obs_col=streamflow_obs_col,
        sim_col=streamflow_sim_col,
        date_col=date_col,
        precip_df=precip_df,
        aggregate=aggregate,
        ylabel=r"Stream Discharge",
        title="Streamflow",
        ax=ax_stream,
    )

    fdc_df = _clean_timeseries(
        streamflow_df,
        date_col,
        [streamflow_sim_col, streamflow_obs_col],
    )
    fdc_df = _aggregate_timeseries(
        fdc_df,
        date_col=date_col,
        value_cols=[streamflow_sim_col, streamflow_obs_col],
        aggregate=aggregate,
        aggregate_func="mean",
    )

    ax_fdc = subfigs[1].subplots(1, 1)
    _, _, fdc_data = plot_swatmf_fdc(
        fdc_df,
        obs_col=streamflow_obs_col,
        sim_col=streamflow_sim_col,
        title="Flow Duration Curve",
        ax=ax_fdc,
    )

    ax_gw_top = subfigs[2].subplots(
        1,
        2,
        sharey=False,
        gridspec_kw={"wspace": gw_wspace},
    )
    ax_gw_bottom = subfigs[3].subplots(
        1,
        2,
        sharey=False,
        gridspec_kw={"wspace": gw_wspace},
    )
    gw_axes = [ax_gw_top[0], ax_gw_top[1], ax_gw_bottom[0], ax_gw_bottom[1]]

    gw_metrics = {}
    for ax, (sim_col, obs_col) in zip(gw_axes, gw_pairs):
        _, _, metrics = plot_swatmf_dtw(
            gw_sim_df,
            sim_col=sim_col,
            gw_obs_df=gw_obs_df,
            obs_col=obs_col,
            date_col=date_col,
            aggregate=aggregate,
            title=f"{sim_col} vs {obs_col}",
            ax=ax,
        )
        gw_metrics[(sim_col, obs_col)] = metrics

    for ax in gw_axes[len(gw_pairs):]:
        ax.axis("off")

    ax_wb = subfigs[4].subplots(
        4,
        1,
        sharex=True,
        height_ratios=[0.2, 0.2, 0.4, 0.2],
    )
    _, wb_axes, wb_data = plot_swatmf_water_balance(
        water_balance_df,
        date_col=date_col,
        timestep=water_balance_timestep,
        title="Water Balance - Monthly Average [mm]"
        if water_balance_timestep in {"month", "M", "ME"}
        else "Water Balance [mm]",
        axes=ax_wb,
    )

    fig.suptitle(title, y=0.995)
    _save_figure(fig, save_path)

    axes = {
        "streamflow": ax_stream,
        "fdc": ax_fdc,
        "gw": gw_axes,
        "water_balance": wb_axes,
    }
    results = {
        "streamflow_metrics": stream_metrics,
        "fdc_data": fdc_data,
        "gw_metrics": gw_metrics,
        "water_balance": wb_data,
    }
    return fig, axes, results


def plot_swatmf_case_study_dashboard(
    streamflow_df,
    streamflow_obs_col,
    water_balance_df,
    gw_sim_df,
    gw_obs_df,
    gw_sim_col,
    gw_obs_col,
    streamflow_sim_col="stf_sim",
    precip_df=None,
    date_col="date",
    aggregate=None,
    water_balance_timestep="month",
    figsize=(10, 10),
    height_ratios=(0.25, 0.25, 0.50),
    width_ratios=(0.50, 0.50),
    title="SWAT-MODFLOW Model Performance",
    save_path=None,
):
    """Create a case-study dashboard.

    Layout:
        Row 1: streamflow
        Row 2 col 1: FDC
        Row 2 col 2: DTW
        Row 3: water balance
    """

    fig = plt.figure(figsize=figsize)

    subfigs = fig.subfigures(
        3,
        1,
        height_ratios=height_ratios,
    )

    # ------------------------------------------------------------------
    # Row 1: streamflow
    # ------------------------------------------------------------------
    ax_stream = subfigs[0].subplots(1, 1)

    _, _, stream_metrics = plot_swatmf_streamflow(
        streamflow_df,
        obs_col=streamflow_obs_col,
        sim_col=streamflow_sim_col,
        date_col=date_col,
        precip_df=precip_df,
        aggregate=aggregate,
        ylabel=r"Stream Discharge",
        # title="Streamflow",
        ax=ax_stream,
    )

    # ------------------------------------------------------------------
    # Row 2: FDC and DTW
    # ------------------------------------------------------------------
    ax_mid = subfigs[1].subplots(
        1,
        2,
        sharey=False,
        gridspec_kw={"width_ratios": width_ratios, "wspace": 0.25},
    )

    fdc_df = _clean_timeseries(
        streamflow_df,
        date_col,
        [streamflow_sim_col, streamflow_obs_col],
    )

    fdc_df = _aggregate_timeseries(
        fdc_df,
        date_col=date_col,
        value_cols=[streamflow_sim_col, streamflow_obs_col],
        aggregate=aggregate,
        aggregate_func="mean",
    )

    _, _, fdc_data = plot_swatmf_fdc(
        fdc_df,
        obs_col=streamflow_obs_col,
        sim_col=streamflow_sim_col,
        # title="Flow Duration Curve",
        ax=ax_mid[0],
    )

    _, _, gw_metrics = plot_swatmf_dtw(
        gw_sim_df,
        sim_col=gw_sim_col,
        gw_obs_df=gw_obs_df,
        obs_col=gw_obs_col,
        date_col=date_col,
        aggregate=aggregate,
        # title=f"DTW: {gw_sim_col} vs {gw_obs_col}",
        ax=ax_mid[1],
    )

    # ------------------------------------------------------------------
    # Row 3: water balance
    # ------------------------------------------------------------------
    ax_wb = subfigs[2].subplots(
        4,
        1,
        sharex=True,
        height_ratios=[0.2, 0.2, 0.4, 0.2],
    )

    wb_title = (
        "Water Balance - Monthly Average [mm]"
        if water_balance_timestep in {"month", "M", "ME"}
        else "Water Balance [mm]"
    )

    _, wb_axes, wb_data = plot_swatmf_water_balance(
        water_balance_df,
        date_col=date_col,
        timestep=water_balance_timestep,
        # title=wb_title,
        axes=ax_wb,
    )

    # fig.suptitle(title, y=0.995)

    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")

    axes = {
        "streamflow": ax_stream,
        "fdc": ax_mid[0],
        "dtw": ax_mid[1],
        "water_balance": wb_axes,
    }

    results = {
        "streamflow_metrics": stream_metrics,
        "fdc_data": fdc_data,
        "gw_metrics": gw_metrics,
        "water_balance": wb_data,
    }

    return fig, axes, results

