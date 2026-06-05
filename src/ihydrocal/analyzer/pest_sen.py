from pathlib import Path
from typing import Optional, Union

import pandas as pd
import matplotlib.pyplot as plt


def plot_pestpp_sen_morris(
    msn_file: Union[str, Path],
    mean_col: str = "sen_mean_abs",
    std_col: str = "sen_std_dev",
    min_mean_abs: float = 1.0e-6,
    top_n: Optional[int] = None,
    sort_by: str = "mean",
    figsize_bar: tuple = (10, 4),
    figsize_scatter: tuple = (8, 6),
    title_prefix: Optional[str] = None,
    annotate: bool = True,
    save_dir: Optional[Union[str, Path]] = None,
    show: bool = True,
):
    """
    Visualize PESTPP-SEN Morris sensitivity results from a .msn file.

    This function creates two common Morris sensitivity plots:

    1. Bar plot:
       - sen_mean_abs: overall parameter importance
       - sen_std_dev : interaction/nonlinearity/uncertainty in sensitivity

    2. Morris mean-vs-standard-deviation scatter plot:
       - x-axis: μ, here using sen_mean_abs
       - y-axis: σ, here using sen_std_dev

    Parameters
    ----------
    msn_file : str or Path
        Path to the PESTPP-SEN Morris output file, usually ending in .msn.

    mean_col : str
        Column name for the Morris absolute mean sensitivity.
        Default is "sen_mean_abs".

    std_col : str
        Column name for the Morris standard deviation.
        Default is "sen_std_dev".

    min_mean_abs : float
        Parameters with mean sensitivity less than or equal to this value
        are removed from the plots.

    top_n : int, optional
        If given, only the top N parameters are plotted.

    sort_by : {"mean", "std", "name"}
        Sorting option before plotting.

    figsize_bar : tuple
        Figure size for the bar plot.

    figsize_scatter : tuple
        Figure size for the scatter plot.

    title_prefix : str, optional
        Optional title prefix, for example model name or case name.

    annotate : bool
        If True, parameter names are added to the scatter plot.

    save_dir : str or Path, optional
        If provided, figures are saved to this directory.

    show : bool
        If True, display figures.

    Returns
    -------
    dict
        Dictionary containing:
        - "data": filtered sensitivity DataFrame
        - "bar_fig": bar plot figure
        - "bar_ax": bar plot axis
        - "scatter_fig": scatter plot figure
        - "scatter_ax": scatter plot axis
    """

    msn_file = Path(msn_file)

    if not msn_file.exists():
        raise FileNotFoundError(f"MSN file not found: {msn_file}")

    # ------------------------------------------------------------------
    # Read PESTPP-SEN Morris result file.
    # Usually, the first column is parameter_name.
    # ------------------------------------------------------------------
    df = pd.read_csv(msn_file, index_col="parameter_name")

    required_cols = [mean_col, std_col]
    missing = [col for col in required_cols if col not in df.columns]

    if missing:
        raise KeyError(
            f"Missing required column(s) in {msn_file.name}: {missing}. "
            f"Available columns: {list(df.columns)}"
        )

    # ------------------------------------------------------------------
    # Convert sensitivity columns to numeric in case they were read as text.
    # ------------------------------------------------------------------
    df[mean_col] = pd.to_numeric(df[mean_col], errors="coerce")
    df[std_col] = pd.to_numeric(df[std_col], errors="coerce")

    # Remove invalid rows.
    df = df.dropna(subset=[mean_col, std_col])

    # Remove parameters with near-zero sensitivity.
    df = df.loc[df[mean_col].abs() > min_mean_abs].copy()

    if df.empty:
        raise ValueError(
            "No sensitivity values remain after filtering. "
            f"Try lowering min_mean_abs. Current value: {min_mean_abs}"
        )

    # ------------------------------------------------------------------
    # Sort parameters.
    # ------------------------------------------------------------------
    if sort_by == "mean":
        df = df.sort_values(mean_col, ascending=False)
    elif sort_by == "std":
        df = df.sort_values(std_col, ascending=False)
    elif sort_by == "name":
        df = df.sort_index()
    else:
        raise ValueError("sort_by must be one of: 'mean', 'std', or 'name'.")

    if top_n is not None:
        df = df.head(top_n)

    # ------------------------------------------------------------------
    # Optional output folder.
    # ------------------------------------------------------------------
    if save_dir is not None:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

    prefix = title_prefix or msn_file.stem

    # ------------------------------------------------------------------
    # 1. Bar plot
    # ------------------------------------------------------------------
    bar_fig, bar_ax = plt.subplots(figsize=figsize_bar)

    df[[mean_col, std_col]].plot(
        kind="bar",
        ax=bar_ax,
        width=0.8,
    )

    bar_ax.set_title(f"{prefix}: Morris Sensitivity")
    bar_ax.set_xlabel("Parameter")
    bar_ax.set_ylabel("Sensitivity")
    bar_ax.grid(axis="y", alpha=0.3)
    bar_ax.tick_params(axis="x", rotation=45)
    bar_ax.legend(["Mean absolute sensitivity", "Standard deviation"])

    bar_fig.tight_layout()

    if save_dir is not None:
        bar_fig.savefig(save_dir / f"{msn_file.stem}_morris_bar.png", dpi=300)

    # ------------------------------------------------------------------
    # 2. Morris μ-σ scatter plot
    # ------------------------------------------------------------------
    scatter_fig, scatter_ax = plt.subplots(figsize=figsize_scatter)

    scatter_ax.scatter(
        df[mean_col],
        df[std_col],
        marker="^",
        s=90,
        alpha=0.7,
    )

    if annotate:
        for par_name, row in df.iterrows():
            scatter_ax.annotate(
                par_name,
                xy=(row[mean_col], row[std_col]),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=10,
            )

    # Add 1:1 line.
    x_min, x_max = scatter_ax.get_xlim()
    y_min, y_max = scatter_ax.get_ylim()

    mn = min(x_min, y_min)
    mx = max(x_max, y_max)

    scatter_ax.plot([mn, mx], [mn, mx], linestyle="--", linewidth=1.2)

    scatter_ax.set_xlim(mn, mx)
    scatter_ax.set_ylim(mn, mx)

    scatter_ax.set_title(f"{prefix}: Morris μ-σ Plot")
    scatter_ax.set_xlabel("μ: mean absolute sensitivity")
    scatter_ax.set_ylabel("σ: standard deviation")
    scatter_ax.grid(alpha=0.3)

    scatter_fig.tight_layout()

    if save_dir is not None:
        scatter_fig.savefig(save_dir / f"{msn_file.stem}_morris_scatter.png", dpi=300)

    if show:
        plt.show()
    else:
        plt.close(bar_fig)
        plt.close(scatter_fig)

    return {
        "data": df,
        "bar_fig": bar_fig,
        "bar_ax": bar_ax,
        "scatter_fig": scatter_fig,
        "scatter_ax": scatter_ax,
    }