from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_precip_timeseries(
    pcp_df,
    date_col="date",
    stations=None,
    figsize=(11, 4),
    title="Precipitation Time Series",
    ylabel="Precipitation",
    alpha=0.7,
    save_path=None,
):
    """Plot precipitation time series from a wide precipitation dataframe.

    Parameters
    ----------
    pcp_df : pandas.DataFrame
        Wide precipitation dataframe.

        Expected format:
            date        station1    station2    station3
            2010-01-01  0.0         1.2         0.0

    stations : list, optional
        List of station columns to plot.
        If None, plot all stations.

    Returns
    -------
    fig, ax
        Matplotlib figure and axis.
    """

    df = pcp_df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    if stations is None:
        stations = [c for c in df.columns if c != date_col]

    fig, ax = plt.subplots(figsize=figsize)

    for station in stations:
        ax.plot(
            df[date_col],
            df[station],
            label=station,
            linewidth=0.8,
            alpha=alpha,
        )

    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)

    if len(stations) <= 12:
        ax.legend(fontsize=8)

    fig.tight_layout()

    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")

    return fig, ax