"""
Cleaned IES analyzer script.

Key cleanup:
- Centralized imports.
- Set Matplotlib backend to Agg for script-based figure/GIF saving.
- Defined _ensemble_to_dataframe() before all functions that use it.
- Removed older duplicate/confusing animation functions:
    animate_tseries_ensemble()
    animate_tseries_ensemble_by_realization_org()
- Kept the latest realization-based time-series, FDC, and parameter animations.
"""

import os
os.environ.setdefault("MPLBACKEND", "Agg")

from pathlib import Path
from typing import Optional, Union
import math

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.animation import FuncAnimation, PillowWriter, FFMpegWriter
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Rectangle, Patch
from matplotlib.lines import Line2D
import matplotlib.gridspec as gridspec

import pyemu


def _ensemble_to_dataframe(ensemble, name="ensemble", copy=True):
    """
    Convert a pandas DataFrame or pyEMU ensemble-like object to a DataFrame.

    This helper allows plotting/analyzer functions to accept either:

        - pandas.DataFrame
        - pyemu.ObservationEnsemble
        - pyemu.ParameterEnsemble

    Parameters
    ----------
    ensemble : object
        Ensemble object to convert.

    name : str
        Name used in error messages.

    copy : bool
        If True, return a copy of the DataFrame.

    Returns
    -------
    pandas.DataFrame or None
        Converted ensemble dataframe.

        If ensemble is None, returns None.
    """

    if ensemble is None:
        return None

    if isinstance(ensemble, pd.DataFrame):
        return ensemble.copy() if copy else ensemble

    # pyEMU ensembles often expose the underlying DataFrame as _df.
    if hasattr(ensemble, "_df"):
        df = ensemble._df
        return df.copy() if copy else df

    # Some ensemble-like objects may support to_dataframe().
    if hasattr(ensemble, "to_dataframe"):
        df = ensemble.to_dataframe()
        return df.copy() if copy else df

    # Last-resort conversion for dataframe-like objects.
    try:
        df = pd.DataFrame(
            ensemble,
            index=ensemble.index,
            columns=ensemble.columns,
        )
        return df.copy() if copy else df

    except Exception as err:
        raise TypeError(
            f"{name} must be a pandas DataFrame, pyEMU ensemble-like object, or None. "
            f"Could not convert object of type {type(ensemble)} to pandas DataFrame."
        ) from err


def load_ies_observation_ensembles(
    pst=None,
    pst_file: Optional[Union[str, Path]] = None,
    model_dir: Optional[Union[str, Path]] = None,
    case: Optional[str] = None,
    last_iter: Optional[int] = None,
    build_pt_fill: bool = True,
):
    """
    Load PESTPP-IES prior and posterior observation ensembles.

    This helper is designed to reduce repeated IPython code.

    Example
    -------
    If:

        pst_file = model_dir / "pecos_rw_ies.pst"

    then this function assumes:

        prior observation ensemble:
            pecos_rw_ies.0.obs.csv

        posterior observation ensemble:
            pecos_rw_ies.<last_iter>.obs.csv

    If last_iter is None, the function automatically finds the largest
    available iteration number from files matching:

        case.*.obs.csv

    Parameters
    ----------
    pst : pyemu.Pst, optional
        Existing PEST control file object.

    pst_file : str or pathlib.Path, optional
        Path to the PEST control file.

        Required if pst is not provided.

    model_dir : str or pathlib.Path, optional
        Folder containing PESTPP-IES output files.

        If None and pst_file is provided, model_dir is inferred from
        pst_file.parent.

    case : str, optional
        Case name used as the prefix for IES output files.

        If None and pst_file is provided, case is inferred from pst_file.stem.

        Example:
            pecos_rw_ies.pst -> case = "pecos_rw_ies"

    last_iter : int, optional
        Posterior iteration number.

        If None, the function automatically finds the largest available
        iteration from observation ensemble files.

    build_pt_fill : bool, default True
        If True, create a posterior min/max dataframe for uncertainty-band
        plotting in plot_tseries_ensemble().

    Returns
    -------
    dict
        Dictionary containing:
            - pst
            - model_dir
            - case
            - last_iter
            - pr_oe
            - pt_oe
            - pt_fill
            - prior_obs_file
            - posterior_obs_file
    """

    # ------------------------------------------------------------------
    # Load pst if only pst_file is provided.
    # pyEMU often needs str(path), not Path object.
    # ------------------------------------------------------------------
    if pst is None:
        if pst_file is None:
            raise ValueError("Either pst or pst_file must be provided.")

        pst_file = Path(pst_file)
        pst = pyemu.Pst(str(pst_file))

    else:
        if pst_file is not None:
            pst_file = Path(pst_file)

    # ------------------------------------------------------------------
    # Infer model_dir.
    # ------------------------------------------------------------------
    if model_dir is None:
        if pst_file is None:
            raise ValueError(
                "model_dir could not be inferred because pst_file was not provided."
            )

        model_dir = pst_file.parent

    model_dir = Path(model_dir)

    # ------------------------------------------------------------------
    # Infer case name.
    # Example:
    #     pecos_rw_ies.pst -> pecos_rw_ies
    # ------------------------------------------------------------------
    if case is None:
        if pst_file is None:
            raise ValueError(
                "case could not be inferred because pst_file was not provided."
            )

        case = pst_file.stem

    # ------------------------------------------------------------------
    # Automatically find the last available IES observation iteration.
    #
    # Files should look like:
    #     pecos_rw_ies.0.obs.csv
    #     pecos_rw_ies.1.obs.csv
    #     pecos_rw_ies.2.obs.csv
    # ------------------------------------------------------------------
    if last_iter is None:
        obs_files = sorted(model_dir.glob(f"{case}.*.obs.csv"))

        iteration_numbers = []

        for f in obs_files:
            # Remove case prefix and suffix.
            # Example:
            #   pecos_rw_ies.4.obs.csv -> 4
            middle = f.name.replace(f"{case}.", "").replace(".obs.csv", "")

            if middle.isdigit():
                iteration_numbers.append(int(middle))

        if not iteration_numbers:
            raise FileNotFoundError(
                f"No IES observation ensemble files found using pattern: "
                f"{model_dir / f'{case}.*.obs.csv'}"
            )

        last_iter = max(iteration_numbers)

    # ------------------------------------------------------------------
    # Define prior and posterior observation ensemble files.
    # ------------------------------------------------------------------
    prior_obs_file = model_dir / f"{case}.0.obs.csv"
    posterior_obs_file = model_dir / f"{case}.{last_iter}.obs.csv"

    if not prior_obs_file.exists():
        raise FileNotFoundError(f"Prior observation ensemble not found: {prior_obs_file}")

    if not posterior_obs_file.exists():
        raise FileNotFoundError(
            f"Posterior observation ensemble not found: {posterior_obs_file}"
        )

    # ------------------------------------------------------------------
    # Load ensembles as DataFrames.
    #
    # We use DataFrames here because plot_tseries_ensemble() and
    # plot_fdc_ensemble() only need realization rows and observation columns.
    # ------------------------------------------------------------------
    pr_oe = pd.read_csv(prior_obs_file, index_col=0)
    pt_oe = pd.read_csv(posterior_obs_file, index_col=0)

    # ------------------------------------------------------------------
    # Build posterior uncertainty range for time-series band plotting.
    #
    # pt_fill structure:
    #     index  = datetime parsed from observation names
    #     columns = pt_min, pt_max, obgnme
    #
    # This can be passed directly to plot_tseries_ensemble(..., pt_fill=pt_fill)
    # ------------------------------------------------------------------
    pt_fill = None

    if build_pt_fill:
        pt_fill = pd.DataFrame(
            {
                "pt_min": pt_oe.min(axis=0),
                "pt_max": pt_oe.max(axis=0),
            }
        )

        obs_data = pst.observation_data.copy()

        missing_obs = [obs for obs in pt_fill.index if obs not in obs_data.index]

        if missing_obs:
            raise KeyError(
                f"{len(missing_obs)} posterior observation names were not found "
                f"in pst.observation_data. Example: {missing_obs[0]}"
            )

        pt_fill["obgnme"] = obs_data.loc[pt_fill.index, "obgnme"]

        # Assumes date is stored in the last 8 characters of observation name.
        pt_fill["time"] = pd.to_datetime(
            pt_fill.index.astype(str).str[-8:],
            errors="coerce",
        )

        pt_fill = (
            pt_fill
            .dropna(subset=["time"])
            .set_index("time")
            .sort_index()
        )

    return {
        "pst": pst,
        "model_dir": model_dir,
        "case": case,
        "last_iter": last_iter,
        "pr_oe": pr_oe,
        "pt_oe": pt_oe,
        "pt_fill": pt_fill,
        "prior_obs_file": prior_obs_file,
        "posterior_obs_file": posterior_obs_file,
    }


def load_ies_parameter_ensembles(
    pst=None,
    pst_file=None,
    model_dir=None,
    case=None,
    last_iter=None,
):
    """
    Load PESTPP-IES prior and posterior parameter ensembles.

    Example
    -------
    If:

        pst_file = model_dir / "pecos_rw_ies.pst"

    then this function assumes:

        prior parameter ensemble:
            pecos_rw_ies.0.par.csv

        posterior parameter ensemble:
            pecos_rw_ies.<last_iter>.par.csv

    If last_iter is None, the function automatically finds the largest
    available iteration number from files matching:

        case.*.par.csv

    Returns
    -------
    dict
        Dictionary containing:
            - pst
            - model_dir
            - case
            - last_iter
            - pr_pe
            - pt_pe
            - prior_par_file
            - posterior_par_file
    """

    from pathlib import Path
    import pandas as pd
    import pyemu

    # ------------------------------------------------------------------
    # Load pst if only pst_file is provided.
    # ------------------------------------------------------------------
    if pst is None:
        if pst_file is None:
            raise ValueError("Either pst or pst_file must be provided.")

        pst_file = Path(pst_file)
        pst = pyemu.Pst(str(pst_file))

    else:
        if pst_file is not None:
            pst_file = Path(pst_file)

    # ------------------------------------------------------------------
    # Infer model_dir.
    # ------------------------------------------------------------------
    if model_dir is None:
        if pst_file is None:
            raise ValueError(
                "model_dir could not be inferred because pst_file was not provided."
            )

        model_dir = pst_file.parent

    model_dir = Path(model_dir)

    # ------------------------------------------------------------------
    # Infer case name.
    # ------------------------------------------------------------------
    if case is None:
        if pst_file is None:
            raise ValueError(
                "case could not be inferred because pst_file was not provided."
            )

        case = pst_file.stem

    # ------------------------------------------------------------------
    # Automatically find last available parameter iteration.
    #
    # Files should look like:
    #     pecos_rw_ies.0.par.csv
    #     pecos_rw_ies.1.par.csv
    #     pecos_rw_ies.2.par.csv
    # ------------------------------------------------------------------
    if last_iter is None:
        par_files = sorted(model_dir.glob(f"{case}.*.par.csv"))

        iteration_numbers = []

        for f in par_files:
            middle = f.name.replace(f"{case}.", "").replace(".par.csv", "")

            if middle.isdigit():
                iteration_numbers.append(int(middle))

        if not iteration_numbers:
            raise FileNotFoundError(
                f"No IES parameter ensemble files found using pattern: "
                f"{model_dir / f'{case}.*.par.csv'}"
            )

        last_iter = max(iteration_numbers)

    # ------------------------------------------------------------------
    # Define prior and posterior parameter ensemble files.
    # ------------------------------------------------------------------
    prior_par_file = model_dir / f"{case}.0.par.csv"
    posterior_par_file = model_dir / f"{case}.{last_iter}.par.csv"

    if not prior_par_file.exists():
        raise FileNotFoundError(
            f"Prior parameter ensemble not found: {prior_par_file}"
        )

    if not posterior_par_file.exists():
        raise FileNotFoundError(
            f"Posterior parameter ensemble not found: {posterior_par_file}"
        )

    # ------------------------------------------------------------------
    # Load parameter ensembles.
    # ------------------------------------------------------------------
    pr_pe = pd.read_csv(prior_par_file, index_col=0)
    pt_pe = pd.read_csv(posterior_par_file, index_col=0)

    return {
        "pst": pst,
        "model_dir": model_dir,
        "case": case,
        "last_iter": last_iter,
        "pr_pe": pr_pe,
        "pt_pe": pt_pe,
        "prior_par_file": prior_par_file,
        "posterior_par_file": posterior_par_file,
    }


def parse_observation_times(obs_names, date_format=None):
    """
    Parse datetime values from observation names.

    By default, this assumes the last 8 characters of each observation name
    are dates in YYYYMMDD format.

    Examples
    --------
    stf_08447300_20010515 -> 2001-05-15
    """
    obs_names = pd.Index(obs_names).astype(str)

    if date_format is None:
        return pd.to_datetime(obs_names.str[-8:], errors="coerce")

    return pd.to_datetime(obs_names, format=date_format, errors="coerce")


def aggregate_series(values, times, freq="MS", func="mean", missing_threshold=-999):
    """
    Aggregate a time series to monthly, annual, or other temporal frequency.

    Common frequencies
    ------------------
    MS : month start
    M  : month end
    YS : year start

    Common functions
    ----------------
    mean, sum, median, max, min
    """
    s = pd.Series(
        pd.to_numeric(values, errors="coerce"),
        index=pd.to_datetime(times, errors="coerce"),
    )

    s = s.dropna()
    s = s.loc[s > missing_threshold]

    if s.empty:
        return s

    if func == "mean":
        return s.resample(freq).mean().dropna()
    if func == "sum":
        return s.resample(freq).sum().dropna()
    if func == "median":
        return s.resample(freq).median().dropna()
    if func == "max":
        return s.resample(freq).max().dropna()
    if func == "min":
        return s.resample(freq).min().dropna()

    raise ValueError(
        "func must be one of: 'mean', 'sum', 'median', 'max', or 'min'."
    )


def aggregate_observation_ensemble(
    ensemble_df,
    obs_names,
    times,
    freq="MS",
    func="mean",
    reference_index=None,
):
    """
    Aggregate each realization in an observation ensemble.

    Parameters
    ----------
    ensemble_df : pandas.DataFrame
        Rows are realizations and columns are observation names.

    obs_names : list-like
        Observation names to use.

    times : list-like
        Datetime values corresponding to obs_names.

    reference_index : pandas.DatetimeIndex, optional
        If provided, each aggregated realization is reindexed to this index.

    Returns
    -------
    pandas.DataFrame
        Aggregated ensemble with:
            rows = realizations
            columns = aggregated timestamps
    """
    ensemble_df = _ensemble_to_dataframe(ensemble_df)

    aggregated = {}

    for realization in ensemble_df.index:
        s = aggregate_series(
            ensemble_df.loc[realization, obs_names].to_numpy(),
            times,
            freq=freq,
            func=func,
        )

        if reference_index is not None:
            s = s.reindex(reference_index)

        aggregated[realization] = s.to_numpy()

    if reference_index is None:
        reference_index = s.index

    return pd.DataFrame(
        aggregated,
        index=reference_index,
    ).T


def build_posterior_fill(pt_oe, pst=None, obgnam=None, obs_names=None, times=None):
    """
    Build posterior min/max uncertainty band for time-series plotting.

    If obs_names and times are provided, this works for one selected
    observation group and can also support monthly aggregated ensembles.

    If pst is provided and obs_names is None, this builds pt_fill for all
    observations using pst.observation_data.
    """
    pt_oe = _ensemble_to_dataframe(pt_oe, name="pt_oe")

    if obs_names is not None:
        df_fill = pd.DataFrame(
            {
                "pt_min": pt_oe[obs_names].min(axis=0).to_numpy(),
                "pt_max": pt_oe[obs_names].max(axis=0).to_numpy(),
                "obgnme": obgnam,
            },
            index=pd.to_datetime(times),
        )

        return df_fill.sort_index()

    if pst is None:
        raise ValueError("pst is required when obs_names is not provided.")

    df_fill = pd.DataFrame(
        {
            "pt_min": pt_oe.min(axis=0),
            "pt_max": pt_oe.max(axis=0),
        }
    )

    obs_data = pst.observation_data.copy()
    df_fill["obgnme"] = obs_data.loc[df_fill.index, "obgnme"]
    df_fill["time"] = parse_observation_times(df_fill.index)

    return (
        df_fill
        .dropna(subset=["time"])
        .set_index("time")
        .sort_index()
    )


def calculate_fdc(values, logy=False, missing_threshold=-999):
    """
    Calculate a flow duration curve.

    Exceedance probability:
        P = rank / (n + 1) * 100
    """
    values = pd.Series(values)
    values = pd.to_numeric(values, errors="coerce").dropna()
    values = values.loc[values > missing_threshold]

    if logy:
        values = values.loc[values > 0]

    if values.empty:
        return None, None

    sorted_values = np.sort(values.to_numpy(dtype=float))[::-1]
    n = len(sorted_values)

    exceedance = np.arange(1, n + 1) / (n + 1) * 100.0

    return exceedance, sorted_values


def calculate_fdc_band(
    ensemble_df,
    obs_names,
    quantiles=(0.05, 0.95),
    logy=False,
):
    """
    Calculate an FDC-space uncertainty band from an ensemble.

    This should be used instead of date-based pt_fill for FDC plots.
    """
    ensemble_df = _ensemble_to_dataframe(ensemble_df)

    fdc_arrays = []
    exceedance_ref = None
    expected_length = None

    for realization in ensemble_df.index:
        x, y = calculate_fdc(
            ensemble_df.loc[realization, obs_names],
            logy=logy,
        )

        if x is None:
            continue

        if expected_length is None:
            expected_length = len(y)
            exceedance_ref = x

        if len(y) != expected_length:
            continue

        fdc_arrays.append(y)

    if not fdc_arrays:
        return None

    fdc_matrix = np.vstack(fdc_arrays)

    q_low, q_high = quantiles

    return {
        "exceedance": exceedance_ref,
        "low": np.nanquantile(fdc_matrix, q_low, axis=0),
        "high": np.nanquantile(fdc_matrix, q_high, axis=0),
        "median": np.nanmedian(fdc_matrix, axis=0),
        "matrix": fdc_matrix,
    }


def plot_ies_phi_evolution(
    phi_file: Union[str, Path],
    phi_col: str = "mean",
    iteration_col: Optional[str] = None,
    logy: bool = True,
    title: Optional[str] = None,
    figsize: tuple = (7, 4),
    save_path: Optional[Union[str, Path]] = None,
    dpi: int = 300,
    show: bool = False,
):
    """
    Plot PESTPP-IES phi evolution through iterations.

    Parameters
    ----------
    phi_file : str or Path
        Path to a PESTPP-IES phi file, usually:
            case.phi.actual.csv
            case.phi.composite.csv
            case.phi.meas.csv

    phi_col : str
        Column to plot. Common columns are often:
            mean, median, std, min, max

    iteration_col : str, optional
        Iteration column name. If None, the function tries to infer it.
        If no suitable column is found, the DataFrame index is used.

    logy : bool
        If True, use log scale for the y-axis.

    title : str, optional
        Plot title.

    figsize : tuple
        Figure size.

    save_path : str or Path, optional
        If provided, save the figure.

    dpi : int
        Save resolution.

    show : bool
        If True, call plt.show().

    Returns
    -------
    fig, ax, phi_df
        Matplotlib figure, axis, and processed phi DataFrame.
    """

    phi_file = Path(phi_file)

    if not phi_file.exists():
        raise FileNotFoundError(f"Phi file not found: {phi_file}")

    phi_df = pd.read_csv(phi_file)

    # Normalize column names just enough for easier matching.
    lower_cols = {c.lower(): c for c in phi_df.columns}

    if phi_col not in phi_df.columns:
        if phi_col.lower() in lower_cols:
            phi_col = lower_cols[phi_col.lower()]
        else:
            raise KeyError(
                f"Column '{phi_col}' not found in {phi_file.name}. "
                f"Available columns: {list(phi_df.columns)}"
            )

    # Try to infer iteration column.
    if iteration_col is None:
        for candidate in ["iteration", "iter", "it"]:
            if candidate in lower_cols:
                iteration_col = lower_cols[candidate]
                break

    if iteration_col is not None and iteration_col in phi_df.columns:
        x = phi_df[iteration_col]
        x_label = "Iteration"
    else:
        x = phi_df.index
        x_label = "Iteration"

    fig, ax = plt.subplots(figsize=figsize)

    ax.plot(
        x,
        phi_df[phi_col],
        marker="o",
        linewidth=1.8,
        label=phi_col,
    )

    if logy:
        ax.set_yscale("log")

    ax.set_xlabel(x_label)
    ax.set_ylabel("Phi")
    ax.set_title(title or f"PESTPP-IES Phi Evolution: {phi_col}")
    ax.grid(True, alpha=0.3)
    ax.legend()

    fig.tight_layout()

    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=dpi, bbox_inches="tight")

    if show:
        plt.show()

    return fig, ax, phi_df


def plot_ies_phi_distribution(
    pst,
    *,
    pr_oe=None,
    pt_oe=None,
    pr_oe_file: Optional[Union[str, Path]] = None,
    pt_oe_file: Optional[Union[str, Path]] = None,
    bins: int = 20,
    log10: bool = True,
    use_shared_bins: bool = False,
    separate_axes: bool = False,
    separate_layout: str = "vertical",
    figsize: tuple = (7, 4),
    title: Optional[str] = None,
    save_path: Optional[Union[str, Path]] = None,
    dpi: int = 300,
    show: bool = False,
):
    """
    Plot prior and posterior PESTPP-IES phi distributions.

    This function compares objective-function values from PESTPP-IES
    observation ensembles.

    It can be used to check whether IES moved the ensemble from a wide,
    high-phi prior distribution toward a lower and tighter posterior
    distribution.

    Parameters
    ----------
    pst : pyemu.Pst
        PEST control file object.

        This is required because pyEMU calculates each realization's phi
        using the observation values, weights, and groups stored in the
        PEST control file.

    pr_oe : pyemu.ObservationEnsemble, optional
        Prior observation ensemble object.

        If this is already loaded using:

            pyemu.ObservationEnsemble.from_csv(...)

        you can pass it directly.

    pt_oe : pyemu.ObservationEnsemble, optional
        Posterior observation ensemble object.

    pr_oe_file : str or pathlib.Path, optional
        Path to the prior observation ensemble CSV file.

        Example:
            pecos_rw_ies.0.obs.csv

    pt_oe_file : str or pathlib.Path, optional
        Path to the posterior observation ensemble CSV file.

        Example:
            pecos_rw_ies.4.obs.csv

    bins : int, default 20
        Number of histogram bins.

    log10 : bool, default True
        If True, plot log10(phi).

        This is usually recommended because phi values can span several
        orders of magnitude.

    use_shared_bins : bool, default False
        If True, prior and posterior histograms use the same bin edges.

        This gives a strict comparison, but if the prior range is very wide
        and the posterior range is very narrow, the posterior may appear as
        a thin vertical line.

        If False, each histogram uses its own bin range. This mimics the
        common pyEMU-style plotting approach:

            pr_oe.phi_vector.apply(np.log10).hist(...)
            pt_oe.phi_vector.apply(np.log10).hist(...)

    separate_axes : bool, default False
        If True, plot prior and posterior histograms in two stacked panels.

        This is useful when the posterior distribution is much narrower
        than the prior distribution. In that case, plotting both on one
        x-axis can make the posterior look like a vertical line.

        If separate_axes=True and both prior and posterior are available,
        this option overrides use_shared_bins.

    figsize : tuple, default (7, 4)
        Figure size in inches.

        For separate_axes=True, you may want something like:
            figsize=(7, 5)

    title : str, optional
        Optional figure title.

    save_path : str or pathlib.Path, optional
        If provided, save the figure to this path.

    dpi : int, default 300
        Figure resolution for saving.

    show : bool, default False
        If True, call plt.show() before returning.

        In IPython/Jupyter, it is often cleaner to use:

            display(fig)
            plt.close(fig)

        after the function returns.

    Returns
    -------
    fig : matplotlib.figure.Figure
        Figure object.

    ax : matplotlib.axes.Axes or numpy.ndarray
        If separate_axes=False, this is one axis.

        If separate_axes=True, this is an array of axes:
            axes[0] = prior axis
            axes[1] = posterior axis

    phi_data : dict
        Dictionary containing processed phi values.

        Keys may include:
            "prior"
            "posterior"

        Values are pandas Series containing either phi or log10(phi).
    """

    # ------------------------------------------------------------------
    # Load observation ensembles from CSV if ensemble objects were not
    # provided directly.
    #
    # We intentionally load these as pyEMU ObservationEnsemble objects
    # instead of plain pandas DataFrames because we need:
    #
    #     ensemble.phi_vector
    #
    # This property is calculated using the PEST control file observation
    # data and weights.
    # ------------------------------------------------------------------
    if pr_oe is None and pr_oe_file is not None:
        pr_oe = pyemu.ObservationEnsemble.from_csv(
            pst=pst,
            filename=str(pr_oe_file),
        )

    if pt_oe is None and pt_oe_file is not None:
        pt_oe = pyemu.ObservationEnsemble.from_csv(
            pst=pst,
            filename=str(pt_oe_file),
        )

    # At least one ensemble must be available.
    if pr_oe is None and pt_oe is None:
        raise ValueError(
            "At least one prior or posterior observation ensemble must be provided. "
            "Use pr_oe/pt_oe or pr_oe_file/pt_oe_file."
        )

    # ------------------------------------------------------------------
    # Extract phi values.
    #
    # phi_vector can contain NaN values if some realizations are invalid.
    # We drop NaNs.
    #
    # If log10=True, phi must be positive. Any zero or negative phi values
    # are removed before applying log10.
    # ------------------------------------------------------------------
    phi_data = {}

    if pr_oe is not None:
        pr_phi = pr_oe.phi_vector.dropna().astype(float)
        pr_phi = pr_phi.loc[pr_phi > 0]

        if log10:
            pr_phi = np.log10(pr_phi)

        phi_data["prior"] = pd.Series(pr_phi, name="Prior")

    if pt_oe is not None:
        pt_phi = pt_oe.phi_vector.dropna().astype(float)
        pt_phi = pt_phi.loc[pt_phi > 0]

        if log10:
            pt_phi = np.log10(pt_phi)

        phi_data["posterior"] = pd.Series(pt_phi, name="Posterior")

    # ------------------------------------------------------------------
    # Safety checks.
    # These warnings are helpful when a histogram does not appear.
    # ------------------------------------------------------------------
    if "prior" in phi_data and phi_data["prior"].empty:
        print("Warning: prior phi data is empty after filtering.")

    if "posterior" in phi_data and phi_data["posterior"].empty:
        print("Warning: posterior phi data is empty after filtering.")

    if all(series.empty for series in phi_data.values()):
        raise ValueError(
            "All phi data are empty after filtering. "
            "Check the observation ensembles and phi_vector values."
        )

    # ------------------------------------------------------------------
    # Print a small summary.
    # This is useful in IPython because it confirms whether posterior phi
    # exists even if the plot looks compressed.
    # ------------------------------------------------------------------
    print("Phi distribution summary:")
    for key, values in phi_data.items():
        if values.empty:
            print(f"  {key}: empty")
        else:
            print(
                f"  {key}: count={len(values)}, "
                f"min={values.min():.4f}, "
                f"max={values.max():.4f}, "
                f"mean={values.mean():.4f}"
            )

    # ------------------------------------------------------------------
    # Case 1: separate axes.
    #
    # This is the best option when posterior phi is tightly clustered.
    # Each histogram gets its own x-axis range, so posterior does not
    # collapse into a vertical line.
    # ------------------------------------------------------------------
    if separate_axes and ("prior" in phi_data) and ("posterior" in phi_data):
        if separate_layout == "horizontal":
            fig, axes = plt.subplots(
                1,
                2,
                figsize=figsize,
                sharex=False,
                sharey=False,
            )
        else:
            fig, axes = plt.subplots(
                2,
                1,
                figsize=figsize,
                sharex=False,
                sharey=False,
            )

        ax_prior, ax_post = axes

        # Prior histogram.
        ax_prior.hist(
            phi_data["prior"],
            bins=bins,
            color="0.5",
            edgecolor="none",
            alpha=0.5,
            density=False,
            label="Prior",
        )

        ax_prior.set_ylabel("Frequency")
        ax_prior.set_title("Prior")
        ax_prior.grid(True, alpha=0.6)
        ax_prior.legend()

        # Add a small x-axis padding to the prior panel.
        pr_min = phi_data["prior"].min()
        pr_max = phi_data["prior"].max()
        pr_pad = (pr_max - pr_min) * 0.03 if pr_max > pr_min else 0.1
        ax_prior.set_xlim(pr_min - pr_pad, pr_max + pr_pad)

        # Posterior histogram.
        ax_post.hist(
            phi_data["posterior"],
            bins=bins,
            color="b",
            edgecolor="none",
            alpha=0.5,
            density=False,
            label="Posterior",
        )

        ax_post.set_ylabel("Frequency")
        ax_post.set_title("Posterior")
        ax_post.grid(True, alpha=0.6)
        ax_post.legend()

        # Add a small x-axis padding to the posterior panel.
        pt_min = phi_data["posterior"].min()
        pt_max = phi_data["posterior"].max()
        pt_pad = (pt_max - pt_min) * 0.03 if pt_max > pt_min else 0.1
        ax_post.set_xlim(pt_min - pt_pad, pt_max + pt_pad)

        # Shared x-axis label for the bottom panel.
        if log10:
            ax_post.set_xlabel(r"$log_{10}\phi$")
        else:
            ax_post.set_xlabel(r"$\phi$")

        if title is not None:
            fig.suptitle(title)

        fig.tight_layout()

        # If suptitle is used, leave a little room at the top.
        if title is not None:
            fig.subplots_adjust(top=0.88)

        ax_return = axes

    # ------------------------------------------------------------------
    # Case 2: one axis.
    #
    # This supports:
    #   - pyEMU-style independent bins
    #   - shared bins
    # ------------------------------------------------------------------
    else:
        fig, ax = plt.subplots(figsize=figsize)

        if use_shared_bins:
            # ----------------------------------------------------------
            # Shared bins.
            #
            # This is useful for direct comparison, but it may compress
            # the posterior if the prior range is much wider.
            # ----------------------------------------------------------
            all_phi = pd.concat(list(phi_data.values()), axis=0)

            bin_edges = np.linspace(
                all_phi.min(),
                all_phi.max(),
                bins + 1,
            )

            if "prior" in phi_data and not phi_data["prior"].empty:
                ax.hist(
                    phi_data["prior"],
                    bins=bin_edges,
                    color="0.5",
                    edgecolor="none",
                    alpha=0.5,
                    density=False,
                    label="Prior",
                )

            if "posterior" in phi_data and not phi_data["posterior"].empty:
                ax.hist(
                    phi_data["posterior"],
                    bins=bin_edges,
                    color="b",
                    edgecolor="none",
                    alpha=0.5,
                    density=False,
                    label="Posterior",
                )

        else:
            # ----------------------------------------------------------
            # PyEMU-style independent bins on one axis.
            #
            # This mimics:
            #
            #     pr_oe.phi_vector.apply(np.log10).hist(...)
            #     pt_oe.phi_vector.apply(np.log10).hist(...)
            #
            # Note:
            # If posterior range is extremely narrow compared with prior,
            # it can still look like a vertical line on one shared x-axis.
            # In that case, use separate_axes=True.
            # ----------------------------------------------------------
            if "prior" in phi_data and not phi_data["prior"].empty:
                phi_data["prior"].hist(
                    ax=ax,
                    bins=bins,
                    fc="0.5",
                    ec="none",
                    alpha=0.5,
                    density=False,
                    label="Prior",
                )

            if "posterior" in phi_data and not phi_data["posterior"].empty:
                phi_data["posterior"].hist(
                    ax=ax,
                    bins=bins,
                    fc="b",
                    ec="none",
                    alpha=0.5,
                    density=False,
                    label="Posterior",
                )

        # --------------------------------------------------------------
        # Set x-axis limits using all available data.
        # This prevents extreme clipping and keeps both distributions in
        # view. It does not solve the narrow-posterior issue; for that,
        # use separate_axes=True.
        # --------------------------------------------------------------
        all_phi = pd.concat(list(phi_data.values()), axis=0)

        xmin = all_phi.min()
        xmax = all_phi.max()
        pad = (xmax - xmin) * 0.03 if xmax > xmin else 0.1

        ax.set_xlim(xmin - pad, xmax + pad)

        if log10:
            ax.set_xlabel(r"$log_{10}\phi$")
        else:
            ax.set_xlabel(r"$\phi$")

        ax.set_ylabel("Frequency")

        if title is not None:
            ax.set_title(title)

        ax.grid(True)
        ax.legend()

        fig.tight_layout()

        ax_return = ax

    # ------------------------------------------------------------------
    # Save the figure if requested.
    # ------------------------------------------------------------------
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=dpi, bbox_inches="tight")

    # ------------------------------------------------------------------
    # Show the figure if requested.
    # In notebooks, show=True usually works, but using display(fig) after
    # return is often more reliable.
    # ------------------------------------------------------------------
    if show:
        plt.show()

    return fig, ax_return, phi_data


def plot_tseries_ensemble(
    pst,
    obgnam,
    *,
    pr_oe=None,
    pt_oe=None,
    width=10,
    height=3,
    dot=False,
    bstcd=None,
    pt_fill=None,
    ymin=None,
    ymax=None,
    auto_ylim_from_pt_fill=False,
    ylim_pad_fraction=0.10,
    include_obs_in_ylim=True,
    aggregate_freq=None,
    aggregate_func="mean",
    savefig=False,
    filename=None,
    dpi=300,
    show=False,
    pst_file=None,
    model_dir=None,
    case=None,
    last_iter=None,
    auto_load_ies=False,
    auto_build_pt_fill=True,
):
    """
    Plot observed time-series data with optional prior and posterior output ensembles.

    This function is designed for PESTPP-IES output ensembles.

    It supports:

        1. Observed data only
        2. Observed data + prior ensemble
        3. Observed data + posterior ensemble
        4. Observed data + prior and posterior ensembles
        5. Daily or temporally aggregated values, such as monthly means

    Recommended visual order
    ------------------------
    The plotting order is intentionally controlled as:

        1. Prior ensemble
        2. Posterior ensemble or posterior uncertainty band
        3. Best-estimate posterior realization, if requested
        4. Observed values

    This order keeps the observed data visible on top of the uncertainty
    information.

    Temporal aggregation
    --------------------
    If aggregate_freq is provided, the function aggregates observed,
    prior ensemble, and posterior ensemble values before plotting.

    Example monthly-average plot:

        aggregate_freq = "MS"
        aggregate_func = "mean"

    Common pandas frequencies:
        "MS" = month start
        "M"  = month end
        "YS" = year start

    Common aggregation functions:
        "mean", "sum", "median", "max", "min"

    Parameters
    ----------
    pst : pyemu.Pst
        PEST control file object.

        The function uses:
            - pst.observation_data
            - pst.nnz_obs_groups

    obgnam : str
        Observation group name to plot.

    pr_oe : pandas.DataFrame or pyemu.ObservationEnsemble, optional
        Prior output ensemble.

        Rows should be realization names and columns should be observation names.

    pt_oe : pandas.DataFrame or pyemu.ObservationEnsemble, optional
        Posterior output ensemble.

        Rows should be realization names and columns should be observation names.

    width, height : float, optional
        Figure size in inches.

    dot : bool, default False
        If True, plot ensemble realizations as scatter points.

        If False, plot ensemble realizations as lines or posterior band.

    bstcd : str, optional
        Best-estimate realization name to plot from posterior ensemble.

        This requires pt_oe.

    pt_fill : pandas.DataFrame, optional
        Posterior uncertainty range.

        Expected columns:
            - obgnme
            - pt_min
            - pt_max

        Expected index:
            datetime-like values compatible with the x-axis.

        If provided, the function plots a posterior uncertainty band instead
        of plotting every posterior realization as blue lines.

        Important:
            If aggregate_freq is not None, the function ignores daily pt_fill
            and rebuilds df_fill from the aggregated posterior ensemble.

    ymin, ymax : float, optional
        Optional manual y-axis limits.

        If provided, these override auto y-axis behavior.

    auto_ylim_from_pt_fill : bool, default False
        If True, automatically set y-axis limits from the posterior
        uncertainty band.

    ylim_pad_fraction : float, default 0.10
        Fractional padding added to automatically calculated y-axis limits.

    include_obs_in_ylim : bool, default True
        If True and auto_ylim_from_pt_fill=True, observed values are also
        included when calculating automatic y-axis limits.

    aggregate_freq : str, optional
        Temporal aggregation frequency.

        Example:
            "MS" for monthly average.

        If None, the original daily values are used.

    aggregate_func : str, default "mean"
        Aggregation function.

        Supported values depend on your aggregate_series() helper, but should
        include:
            "mean", "sum", "median", "max", "min"

    savefig : bool, default False
        If True, save the figure as a PNG file.

    filename : str or pathlib.Path, optional
        Output filename.

        If None and savefig=True, a default filename is generated.

    dpi : int, default 300
        Resolution for saved figure.

    show : bool, default False
        If True, call plt.show().

    pst_file : str or pathlib.Path, optional
        PEST control file path used when auto_load_ies=True.

    model_dir : str or pathlib.Path, optional
        Folder containing PESTPP-IES output files.

    case : str, optional
        PEST++ case name.

    last_iter : int, optional
        Posterior IES iteration. If None, latest iteration can be inferred by
        load_ies_observation_ensembles().

    auto_load_ies : bool, default False
        If True, automatically load prior/posterior observation ensembles.

    auto_build_pt_fill : bool, default True
        If True and auto_load_ies=True, also build posterior fill dataframe.

    Returns
    -------
    fig, ax
        Matplotlib figure and axis objects.
    """

    # ------------------------------------------------------------------
    # Optional automatic loading for PESTPP-IES outputs.
    #
    # This allows simple calls such as:
    #
    #     plot_tseries_ensemble(
    #         pst_file=model_dir / "pecos_rw_ies.pst",
    #         obgnam="stf_08447300",
    #         auto_load_ies=True,
    #     )
    #
    # The function will load:
    #     case.0.obs.csv
    #     case.<last_iter>.obs.csv
    #     pt_fill
    # ------------------------------------------------------------------
    if auto_load_ies:
        ies = load_ies_observation_ensembles(
            pst=pst,
            pst_file=pst_file,
            model_dir=model_dir,
            case=case,
            last_iter=last_iter,
            build_pt_fill=auto_build_pt_fill,
        )

        pst = ies["pst"]

        if pr_oe is None:
            pr_oe = ies["pr_oe"]

        if pt_oe is None:
            pt_oe = ies["pt_oe"]

        if pt_fill is None and auto_build_pt_fill:
            pt_fill = ies["pt_fill"]

    # ------------------------------------------------------------------
    # Convert pyEMU ensemble-like objects to pandas DataFrames.
    # ------------------------------------------------------------------
    pr_oe = _ensemble_to_dataframe(pr_oe, name="pr_oe")
    pt_oe = _ensemble_to_dataframe(pt_oe, name="pt_oe")

    has_prior = pr_oe is not None
    has_posterior = pt_oe is not None

    # ------------------------------------------------------------------
    # Get observation data from the PEST control file.
    #
    # We keep only observations from non-zero-weight observation groups.
    # ------------------------------------------------------------------
    obs = pst.observation_data.copy()
    obs = obs.loc[obs.obgnme.isin(pst.nnz_obs_groups)].copy()

    # ------------------------------------------------------------------
    # Extract time information from observation names.
    #
    # This assumes the last 8 characters of obsnme are dates.
    # ------------------------------------------------------------------
    obs["time"] = pd.to_datetime(obs.obsnme.str[-8:], errors="coerce")

    # ------------------------------------------------------------------
    # Select the requested observation group.
    # ------------------------------------------------------------------
    oobs = obs.loc[obs.obgnme == obgnam].copy()

    if oobs.empty:
        raise ValueError(f"No observations found for observation group: {obgnam}")

    # ------------------------------------------------------------------
    # Remove observations where date parsing failed.
    # ------------------------------------------------------------------
    oobs = oobs.dropna(subset=["time"]).copy()

    if oobs.empty:
        raise ValueError(
            f"Observations were found for {obgnam}, but no valid dates could be parsed "
            "from the last 8 characters of obsnme."
        )

    # ------------------------------------------------------------------
    # Sort observations by time so lines follow chronological order.
    # ------------------------------------------------------------------
    oobs.sort_values("time", inplace=True)

    tvals = oobs.time.to_numpy()
    onames = oobs.obsnme.to_numpy()

    # ------------------------------------------------------------------
    # Prepare prior ensemble.
    #
    # Values <= -999 are treated as missing values.
    # ------------------------------------------------------------------
    if has_prior:
        pr_oe = pr_oe.where(pr_oe > -999)

        missing_prior_cols = [name for name in onames if name not in pr_oe.columns]

        if missing_prior_cols:
            raise KeyError(
                f"{len(missing_prior_cols)} observation names are missing from pr_oe. "
                f"Example missing name: {missing_prior_cols[0]}"
            )

    # ------------------------------------------------------------------
    # Prepare posterior ensemble.
    # ------------------------------------------------------------------
    if has_posterior:
        pt_oe = pt_oe.where(pt_oe > -999)

        missing_post_cols = [name for name in onames if name not in pt_oe.columns]

        if missing_post_cols:
            raise KeyError(
                f"{len(missing_post_cols)} observation names are missing from pt_oe. "
                f"Example missing name: {missing_post_cols[0]}"
            )

    # ------------------------------------------------------------------
    # Prepare observed values with non-zero weight.
    #
    # These will be plotted last so they remain visible.
    #
    # Important:
    #     We prepare this before aggregation because monthly aggregation
    #     should use only non-zero-weight observations.
    # ------------------------------------------------------------------
    oobs_nonzero = oobs.loc[oobs.weight > 0].copy()

    # ------------------------------------------------------------------
    # Optional temporal aggregation.
    #
    # If aggregate_freq is provided, daily values are aggregated before
    # plotting. This is useful for monthly average plots.
    #
    # Example:
    #     aggregate_freq = "MS"
    #     aggregate_func = "mean"
    #
    # After aggregation:
    #     tvals         -> aggregated timestamps
    #     oobs_nonzero  -> aggregated observed values
    #     pr_oe         -> aggregated prior ensemble
    #     pt_oe         -> aggregated posterior ensemble
    #     onames        -> aggregated timestamps used as ensemble columns
    #
    # Because the ensemble columns change from original observation names
    # to aggregated timestamps, df_fill must be rebuilt later from the
    # aggregated posterior ensemble.
    # ------------------------------------------------------------------
    if aggregate_freq is not None:

        obs_agg = aggregate_series(
            oobs_nonzero["obsval"].to_numpy(),
            oobs_nonzero["time"].to_numpy(),
            freq=aggregate_freq,
            func=aggregate_func,
        )

        if obs_agg.empty:
            raise ValueError(
                f"No valid aggregated observed values for observation group: {obgnam}"
            )

        # Aggregated x-axis time values.
        tvals = obs_agg.index.to_numpy()

        # Replace observed dataframe with aggregated observations.
        # Keep the same column names used later by the plotting code.
        oobs_nonzero = pd.DataFrame(
            {
                "time": obs_agg.index,
                "obsval": obs_agg.values,
                "weight": 1.0,
            }
        )

        # Save original daily observation names and times for ensemble aggregation.
        daily_onames = onames.copy()
        daily_times = oobs["time"].to_numpy()

        # Aggregate prior ensemble realization by realization.
        if has_prior:
            pr_oe = aggregate_observation_ensemble(
                pr_oe,
                obs_names=daily_onames,
                times=daily_times,
                freq=aggregate_freq,
                func=aggregate_func,
                reference_index=obs_agg.index,
            )

        # Aggregate posterior ensemble realization by realization.
        if has_posterior:
            pt_oe = aggregate_observation_ensemble(
                pt_oe,
                obs_names=daily_onames,
                times=daily_times,
                freq=aggregate_freq,
                func=aggregate_func,
                reference_index=obs_agg.index,
            )

        # After aggregation, ensemble columns are timestamps, not original
        # daily observation names.
        onames = obs_agg.index

    # ------------------------------------------------------------------
    # Prepare posterior uncertainty band.
    #
    # Daily mode:
    #     Use pt_fill if provided.
    #
    # Aggregated mode:
    #     Rebuild df_fill from the aggregated posterior ensemble.
    #
    # This avoids plotting a daily posterior band on a monthly plot.
    # ------------------------------------------------------------------
    if aggregate_freq is not None and has_posterior:
        df_fill = build_posterior_fill(
            pt_oe,
            obgnam=obgnam,
            obs_names=onames,
            times=onames,
        )

    elif pt_fill is not None:
        required_cols = {"obgnme", "pt_min", "pt_max"}
        missing_cols = required_cols.difference(pt_fill.columns)

        if missing_cols:
            raise KeyError(
                f"pt_fill is missing required columns: {sorted(missing_cols)}"
            )

        df_fill = pt_fill.loc[pt_fill["obgnme"] == obgnam].copy()

        if df_fill.empty:
            raise ValueError(f"No pt_fill records found for observation group: {obgnam}")

        # Sort the fill dataframe by its datetime index to avoid strange
        # polygons when fill_between is called.
        df_fill = df_fill.sort_index()

    else:
        df_fill = None

    # ------------------------------------------------------------------
    # Create figure.
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(width, height))

    # ==================================================================
    # Case 1: scatter style
    # ==================================================================
    if dot:

        # --------------------------------------------------------------
        # 1. Prior ensemble first.
        # --------------------------------------------------------------
        if has_prior:
            for idx, realization in enumerate(pr_oe.index):
                ax.scatter(
                    tvals,
                    pr_oe.loc[realization, onames].to_numpy(),
                    color="gray",
                    s=30,
                    alpha=0.35,
                    label="Prior ensemble" if idx == 0 else None,
                    zorder=1,
                )

        # --------------------------------------------------------------
        # 2. Posterior ensemble second.
        # --------------------------------------------------------------
        if has_posterior:
            for idx, realization in enumerate(pt_oe.index):
                ax.scatter(
                    tvals,
                    pt_oe.loc[realization, onames].to_numpy(),
                    color="b",
                    s=30,
                    alpha=0.20,
                    label="Posterior ensemble" if idx == 0 else None,
                    zorder=2,
                )

        # --------------------------------------------------------------
        # 3. Best-estimate realization, if requested.
        #
        # For scatter mode, plot it as a blue line so it is easy to
        # distinguish from the ensemble cloud.
        # --------------------------------------------------------------
        if bstcd is not None:
            if not has_posterior:
                raise ValueError("bstcd was provided, but pt_oe is None.")

            if bstcd not in pt_oe.index:
                raise KeyError(
                    f"Best-estimate realization '{bstcd}' was not found in pt_oe.index."
                )

            ax.plot(
                tvals,
                pt_oe.loc[bstcd, onames].to_numpy(),
                color="b",
                lw=1.5,
                zorder=4,
                label="Best estimate",
            )

        # --------------------------------------------------------------
        # 4. Observed values last.
        # --------------------------------------------------------------
        ax.scatter(
            oobs_nonzero.time,
            oobs_nonzero.obsval,
            edgecolor="red",
            facecolor="none",
            s=30,
            alpha=0.8,
            label="Observed",
            zorder=5,
        )

    # ==================================================================
    # Case 2: line/band style
    # ==================================================================
    else:

        # --------------------------------------------------------------
        # 1. Prior ensemble first.
        # --------------------------------------------------------------
        if has_prior:
            for idx, realization in enumerate(pr_oe.index):
                ax.plot(
                    tvals,
                    pr_oe.loc[realization, onames].to_numpy(),
                    color="0.5",
                    lw=0.5,
                    alpha=0.45,
                    label="Prior ensemble" if idx == 0 else None,
                    zorder=1,
                )

        # --------------------------------------------------------------
        # 2. Posterior ensemble second.
        #
        # If df_fill is available, plot posterior uncertainty as a band.
        # If not, plot all posterior realizations.
        # --------------------------------------------------------------
        if has_posterior:
            if df_fill is not None:

                # Posterior uncertainty band.
                ax.fill_between(
                    df_fill.index,
                    df_fill["pt_min"].to_numpy(dtype=float),
                    df_fill["pt_max"].to_numpy(dtype=float),
                    interpolate=False,
                    color="b",
                    alpha=0.35,
                    label="Posterior range",
                    zorder=3,
                )

                # Lower edge of posterior band.
                ax.plot(
                    df_fill.index,
                    df_fill["pt_min"].to_numpy(dtype=float),
                    color="b",
                    lw=0.8,
                    alpha=0.8,
                    zorder=3,
                )

                # Upper edge of posterior band.
                ax.plot(
                    df_fill.index,
                    df_fill["pt_max"].to_numpy(dtype=float),
                    color="b",
                    lw=0.8,
                    alpha=0.8,
                    zorder=3,
                )

            else:
                for idx, realization in enumerate(pt_oe.index):
                    ax.plot(
                        tvals,
                        pt_oe.loc[realization, onames].to_numpy(),
                        color="b",
                        lw=0.5,
                        alpha=0.40,
                        label="Posterior ensemble" if idx == 0 else None,
                        zorder=2,
                    )

        # --------------------------------------------------------------
        # 3. Best-estimate posterior realization, if requested.
        # --------------------------------------------------------------
        if bstcd is not None:
            if not has_posterior:
                raise ValueError("bstcd was provided, but pt_oe is None.")

            if bstcd not in pt_oe.index:
                raise KeyError(
                    f"Best-estimate realization '{bstcd}' was not found in pt_oe.index."
                )

            ax.plot(
                tvals,
                pt_oe.loc[bstcd, onames].to_numpy(),
                color="b",
                lw=1.5,
                zorder=4,
                label="Best estimate",
            )

        # --------------------------------------------------------------
        # 4. Observed values last.
        # --------------------------------------------------------------
        ax.scatter(
            oobs_nonzero.time,
            oobs_nonzero.obsval,
            edgecolor="red",
            facecolor="none",
            s=14,
            zorder=5,
            alpha=0.8,
            label="Observed",
        )

    # ------------------------------------------------------------------
    # Automatically set y-axis limits from posterior uncertainty band.
    #
    # Manual ymin/ymax still take priority if provided by the user.
    # ------------------------------------------------------------------
    if auto_ylim_from_pt_fill and df_fill is not None and ymin is None and ymax is None:
        y_values = []

        y_values.extend(df_fill["pt_min"].dropna().to_numpy(dtype=float))
        y_values.extend(df_fill["pt_max"].dropna().to_numpy(dtype=float))

        if include_obs_in_ylim and not oobs_nonzero.empty:
            y_values.extend(oobs_nonzero["obsval"].dropna().to_numpy(dtype=float))

        y_values = np.asarray(y_values, dtype=float)
        y_values = y_values[np.isfinite(y_values)]

        if y_values.size > 0:
            y_min_auto = y_values.min()
            y_max_auto = y_values.max()

            y_range = y_max_auto - y_min_auto

            if y_range == 0:
                pad = abs(y_max_auto) * ylim_pad_fraction

                if pad == 0:
                    pad = 1.0
            else:
                pad = y_range * ylim_pad_fraction

            ymin = y_min_auto - pad
            ymax = y_max_auto + pad

    # ------------------------------------------------------------------
    # Optional y-axis limits.
    # ------------------------------------------------------------------
    if ymin is not None or ymax is not None:
        ax.set_ylim(ymin, ymax)

    # ------------------------------------------------------------------
    # Format x-axis.
    #
    # Major ticks are years.
    # Minor ticks are months.
    # ------------------------------------------------------------------
    years = mdates.YearLocator()
    years_fmt = mdates.DateFormatter("%Y")

    months = mdates.MonthLocator()
    months_fmt = mdates.DateFormatter("%b")

    ax.xaxis.set_major_locator(years)
    ax.xaxis.set_major_formatter(years_fmt)

    ax.xaxis.set_minor_locator(months)
    ax.xaxis.set_minor_formatter(months_fmt)

    plt.setp(ax.xaxis.get_minorticklabels(), fontsize=6, rotation=90)

    ax.tick_params(axis="both", labelsize=8, rotation=0)
    ax.tick_params(axis="x", pad=15)

    # Add small x-axis margin so edge points are not clipped.
    ax.margins(x=0.01)

    # ------------------------------------------------------------------
    # Add legend only if there are labeled plot elements.
    #
    # Remove duplicate labels while preserving order.
    # ------------------------------------------------------------------
    handles, labels = ax.get_legend_handles_labels()

    if labels:
        unique = {}

        for handle, label in zip(handles, labels):
            if label not in unique:
                unique[label] = handle

        ax.legend(
            unique.values(),
            unique.keys(),
            fontsize=8,
            ncol=3,
        )

    plt.tight_layout()

    # ------------------------------------------------------------------
    # Save figure.
    # ------------------------------------------------------------------
    if savefig:
        if filename is None:
            if aggregate_freq is None:
                filename = f"tensemble_{obgnam}.png"
            else:
                filename = f"tensemble_{aggregate_freq}_{aggregate_func}_{obgnam}.png"

        fig.savefig(filename, bbox_inches="tight", dpi=dpi)

    if show:
        plt.show()

    return fig, ax


def plot_fdc_ensemble(
    pst=None,
    obgnam=None,
    *,
    pst_file=None,
    model_dir=None,
    case=None,
    last_iter=None,
    auto_load_ies=False,
    pr_oe=None,
    pt_oe=None,
    width=6,
    height=5,
    logy=True,
    posterior_band=True,
    posterior_band_quantiles=(0.05, 0.95),
    plot_prior_lines=True,
    plot_posterior_lines=False,
    obs_dot=False,
    obs_marker_size=18,
    obs_line=True,
    aggregate_freq=None,
    aggregate_func="mean",
    ymin=None,
    ymax=None,
    title=None,
    savefig=False,
    filename=None,
    dpi=300,
    show=False,
):
    """
    Plot flow duration curves for observed data and optional prior/posterior
    PESTPP-IES output ensembles.

    This function supports daily FDCs and temporally aggregated FDCs.

    Example daily FDC
    -----------------
    aggregate_freq=None

    Example monthly-average FDC
    ---------------------------
    aggregate_freq="MS"
    aggregate_func="mean"

    Main plot elements
    ------------------
    1. Prior ensemble FDCs
    2. Posterior FDC uncertainty band
    3. Posterior median FDC
    4. Observed FDC line and/or dots

    Why FDC aggregation is handled here
    -----------------------------------
    If aggregate_freq is provided, each time series is aggregated first.
    Then the FDC is calculated from the aggregated values.

    For example:

        daily flow -> monthly mean flow -> monthly FDC
    """

    # ------------------------------------------------------------------
    # Optional automatic loading for PESTPP-IES output files.
    # ------------------------------------------------------------------
    if auto_load_ies:
        ies = load_ies_observation_ensembles(
            pst=pst,
            pst_file=pst_file,
            model_dir=model_dir,
            case=case,
            last_iter=last_iter,
            build_pt_fill=False,
        )

        pst = ies["pst"]

        if pr_oe is None:
            pr_oe = ies["pr_oe"]

        if pt_oe is None:
            pt_oe = ies["pt_oe"]

    # ------------------------------------------------------------------
    # Safety checks.
    # ------------------------------------------------------------------
    if pst is None:
        raise ValueError("pst must be provided, or use pst_file with auto_load_ies=True.")

    if obgnam is None:
        raise ValueError("obgnam must be provided.")

    # ------------------------------------------------------------------
    # Convert pyEMU ensemble-like objects to pandas DataFrames.
    # ------------------------------------------------------------------
    pr_oe = _ensemble_to_dataframe(pr_oe, name="pr_oe")
    pt_oe = _ensemble_to_dataframe(pt_oe, name="pt_oe")

    has_prior = pr_oe is not None
    has_posterior = pt_oe is not None

    # ------------------------------------------------------------------
    # Get observation data from the PEST control file.
    # Keep only non-zero-weight observation groups.
    # ------------------------------------------------------------------
    obs = pst.observation_data.copy()
    obs = obs.loc[obs.obgnme.isin(pst.nnz_obs_groups)].copy()

    # ------------------------------------------------------------------
    # Parse dates from observation names.
    # Assumes the last 8 characters are YYYYMMDD.
    # ------------------------------------------------------------------
    obs["time"] = pd.to_datetime(obs.obsnme.str[-8:], errors="coerce")

    # ------------------------------------------------------------------
    # Select requested observation group.
    # ------------------------------------------------------------------
    oobs = obs.loc[obs.obgnme == obgnam].copy()

    if oobs.empty:
        raise ValueError(f"No observations found for observation group: {obgnam}")

    oobs = oobs.dropna(subset=["time"]).copy()

    if oobs.empty:
        raise ValueError(
            f"Observations were found for {obgnam}, but no valid dates could be parsed."
        )

    oobs.sort_values("time", inplace=True)

    onames = oobs.obsnme.to_numpy()
    times = oobs["time"].to_numpy()

    # ------------------------------------------------------------------
    # Prepare observed values.
    # Use only non-zero-weight observations.
    # ------------------------------------------------------------------
    oobs_nonzero = oobs.loc[oobs.weight > 0].copy()

    obs_values = pd.to_numeric(oobs_nonzero.obsval, errors="coerce")
    obs_times = oobs_nonzero["time"].to_numpy()

    # ------------------------------------------------------------------
    # If aggregation is requested, aggregate observations before FDC.
    #
    # Example:
    #   aggregate_freq="MS"
    #   aggregate_func="mean"
    #
    # means:
    #   daily observed flow -> monthly average observed flow -> FDC
    # ------------------------------------------------------------------
    if aggregate_freq is not None:
        obs_values = aggregate_series(
            obs_values.to_numpy(),
            obs_times,
            freq=aggregate_freq,
            func=aggregate_func,
        )
    else:
        obs_values = obs_values.dropna()
        obs_values = obs_values.loc[obs_values > -999]

    if obs_values.empty:
        raise ValueError(f"No valid observed values found for group: {obgnam}")

    # ------------------------------------------------------------------
    # Prepare prior ensemble.
    # ------------------------------------------------------------------
    if has_prior:
        pr_oe = pr_oe.where(pr_oe > -999)

        missing_prior_cols = [name for name in onames if name not in pr_oe.columns]

        if missing_prior_cols:
            raise KeyError(
                f"{len(missing_prior_cols)} observation names are missing from pr_oe. "
                f"Example missing name: {missing_prior_cols[0]}"
            )

    # ------------------------------------------------------------------
    # Prepare posterior ensemble.
    # ------------------------------------------------------------------
    if has_posterior:
        pt_oe = pt_oe.where(pt_oe > -999)

        missing_post_cols = [name for name in onames if name not in pt_oe.columns]

        if missing_post_cols:
            raise KeyError(
                f"{len(missing_post_cols)} observation names are missing from pt_oe. "
                f"Example missing name: {missing_post_cols[0]}"
            )

    # ------------------------------------------------------------------
    # Helper to get one realization's values.
    #
    # If aggregate_freq is None:
    #     return daily realization values
    #
    # If aggregate_freq is not None:
    #     return aggregated realization values, e.g. monthly mean flow
    # ------------------------------------------------------------------
    def _get_realization_values(ensemble_df, realization):
        values = ensemble_df.loc[realization, onames]

        if aggregate_freq is not None:
            return aggregate_series(
                values.to_numpy(),
                times,
                freq=aggregate_freq,
                func=aggregate_func,
            )

        return values

    # ------------------------------------------------------------------
    # Helper to calculate one FDC.
    #
    # Exceedance probability:
    #     P = rank / (n + 1) * 100
    #
    # Larger flows have smaller exceedance probabilities.
    # ------------------------------------------------------------------
    def _calculate_fdc(values):
        values = pd.Series(values)
        values = pd.to_numeric(values, errors="coerce").dropna()
        values = values.loc[values > -999]

        if logy:
            values = values.loc[values > 0]

        if values.empty:
            return None, None

        sorted_values = np.sort(values.to_numpy(dtype=float))[::-1]
        n = len(sorted_values)

        exceedance = np.arange(1, n + 1) / (n + 1) * 100.0

        return exceedance, sorted_values

    # ------------------------------------------------------------------
    # Helper to calculate posterior FDC uncertainty band.
    #
    # The band is calculated in FDC space:
    #   1. Aggregate each realization if requested.
    #   2. Sort each realization into FDC values.
    #   3. Calculate quantiles across realizations at each exceedance rank.
    # ------------------------------------------------------------------
    def _calculate_fdc_band(ensemble_df, quantiles=(0.05, 0.95)):
        fdc_arrays = []
        exceedance_ref = None
        expected_length = None

        for realization in ensemble_df.index:
            values = _get_realization_values(ensemble_df, realization)
            x, y = _calculate_fdc(values)

            if x is None:
                continue

            if expected_length is None:
                expected_length = len(y)
                exceedance_ref = x

            # Skip inconsistent lengths caused by missing values.
            if len(y) != expected_length:
                continue

            fdc_arrays.append(y)

        if not fdc_arrays:
            return None

        fdc_matrix = np.vstack(fdc_arrays)

        q_low, q_high = quantiles

        return {
            "exceedance": exceedance_ref,
            "low": np.nanquantile(fdc_matrix, q_low, axis=0),
            "high": np.nanquantile(fdc_matrix, q_high, axis=0),
            "median": np.nanmedian(fdc_matrix, axis=0),
            "matrix": fdc_matrix,
        }

    # ------------------------------------------------------------------
    # Create figure.
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(width, height))

    fdc_data = {}

    # ------------------------------------------------------------------
    # 1. Prior ensemble FDCs.
    # ------------------------------------------------------------------
    if has_prior and plot_prior_lines:
        for idx, realization in enumerate(pr_oe.index):
            values = _get_realization_values(pr_oe, realization)
            x, y = _calculate_fdc(values)

            if x is None:
                continue

            ax.plot(
                x,
                y,
                color="0.5",
                lw=0.5,
                alpha=0.30,
                label="Prior ensemble" if idx == 0 else None,
                zorder=1,
            )

    # ------------------------------------------------------------------
    # 2. Posterior FDC uncertainty band.
    # ------------------------------------------------------------------
    if has_posterior and posterior_band:
        pt_band = _calculate_fdc_band(
            pt_oe,
            quantiles=posterior_band_quantiles,
        )

        if pt_band is not None:
            fdc_data["posterior_band"] = pt_band

            x_band = pt_band["exceedance"]

            ax.fill_between(
                x_band,
                pt_band["low"],
                pt_band["high"],
                color="b",
                alpha=0.25,
                label=(
                    f"Posterior "
                    f"{posterior_band_quantiles[0]:.0%}-"
                    f"{posterior_band_quantiles[1]:.0%} range"
                ),
                zorder=2,
            )

            ax.plot(
                x_band,
                pt_band["median"],
                color="b",
                lw=1.4,
                alpha=0.9,
                label="Posterior median",
                zorder=3,
            )

    # ------------------------------------------------------------------
    # 3. Optional posterior individual FDC lines.
    # ------------------------------------------------------------------
    if has_posterior and plot_posterior_lines:
        for idx, realization in enumerate(pt_oe.index):
            values = _get_realization_values(pt_oe, realization)
            x, y = _calculate_fdc(values)

            if x is None:
                continue

            ax.plot(
                x,
                y,
                color="b",
                lw=0.5,
                alpha=0.25,
                label="Posterior ensemble" if idx == 0 else None,
                zorder=2,
            )

    # ------------------------------------------------------------------
    # 4. Observed FDC.
    # Plot last so it stays visible.
    # ------------------------------------------------------------------
    x_obs, y_obs = _calculate_fdc(obs_values)

    if x_obs is None:
        raise ValueError(f"Could not calculate observed FDC for group: {obgnam}")

    fdc_data["observed"] = {
        "exceedance": x_obs,
        "flow": y_obs,
    }

    if obs_line:
        ax.plot(
            x_obs,
            y_obs,
            color="red",
            lw=1.8,
            label="Observed" if not obs_dot else "Observed line",
            zorder=5,
        )

    if obs_dot:
        ax.scatter(
            x_obs,
            y_obs,
            edgecolor="red",
            facecolor="none",
            s=obs_marker_size,
            alpha=0.8,
            label="Observed" if not obs_line else "Observed points",
            zorder=6,
        )

    # ------------------------------------------------------------------
    # Axis formatting.
    # ------------------------------------------------------------------
    ax.set_xlabel("Exceedance probability (%)")

    if aggregate_freq is None:
        ax.set_ylabel("Flow")
    else:
        ax.set_ylabel(f"{aggregate_func.capitalize()} flow")

    ax.set_xlim(0, 100)

    if logy:
        ax.set_yscale("log")

    if ymin is not None or ymax is not None:
        ax.set_ylim(ymin, ymax)

    ax.grid(True, which="both", alpha=0.3)

    # ------------------------------------------------------------------
    # Remove duplicate legend labels.
    # ------------------------------------------------------------------
    handles, labels = ax.get_legend_handles_labels()

    if labels:
        unique = {}

        for handle, label in zip(handles, labels):
            if label not in unique:
                unique[label] = handle

        ax.legend(
            unique.values(),
            unique.keys(),
            fontsize=8,
        )

    # ------------------------------------------------------------------
    # Title.
    # ------------------------------------------------------------------
    if title is not None:
        ax.set_title(title)
    else:
        if aggregate_freq is None:
            ax.set_title(f"Flow Duration Curve: {obgnam}")
        else:
            ax.set_title(
                f"Flow Duration Curve ({aggregate_freq}, {aggregate_func}): {obgnam}"
            )

    fig.tight_layout()

    # ------------------------------------------------------------------
    # Save figure.
    # ------------------------------------------------------------------
    if savefig:
        if filename is None:
            if aggregate_freq is None:
                filename = f"fdc_ensemble_{obgnam}.png"
            else:
                filename = f"fdc_ensemble_{aggregate_freq}_{aggregate_func}_{obgnam}.png"

        fig.savefig(filename, bbox_inches="tight", dpi=dpi)

    if show:
        plt.show()

    return fig, ax, fdc_data


def plot_parameter_ensemble(
    pst,
    *,
    pr_pe=None,
    pt_pe=None,
    sel_pars=None,
    width=7,
    height=5,
    ncols=3,
    nbins=20,
    bestcand=None,
    parobj_file=None,
    wd=None,
    savefig=False,
    filename=None,
    dpi=300,
    show=False,
):
    """
    Plot histograms of prior and/or posterior parameter ensembles.

    This function is designed for PESTPP-IES parameter ensembles.

    It supports:

        1. Prior only
        2. Posterior only
        3. Prior + posterior

    It also supports parameter selection using either:

        1. sel_pars=None
           Plot all available parameters.

        2. sel_pars=list
           Example:
               sel_pars = ["cn2", "esco", "alpha"]

        3. sel_pars=pandas.DataFrame
           Must contain a "parnme" column.

    Notes
    -----
    This function safely handles pyEMU pst.parameter_data where "parnme"
    may appear both as an index and a column. That situation can cause:

        ValueError: 'parnme' is both an index level and a column label

    To avoid this, the function resets parameter metadata to a clean
    dataframe where "parnme" is only a normal column.

    Parameters
    ----------
    pst : pyemu.Pst
        PEST control file object.

    pr_pe : pandas.DataFrame or pyemu.ParameterEnsemble, optional
        Prior parameter ensemble.

        Rows are realizations and columns are parameter names.

    pt_pe : pandas.DataFrame or pyemu.ParameterEnsemble, optional
        Posterior parameter ensemble.

    sel_pars : list-like or pandas.DataFrame, optional
        Selected parameters to plot.

        If list-like:
            ["cn2", "esco", "alpha"]

        If DataFrame:
            Must contain "parnme". It can optionally contain:
                parlbnd, parubnd, offset

    width, height : float, optional
        Figure size in inches.

    ncols : int, default 3
        Number of subplot columns.

    nbins : int, default 20
        Number of histogram bins.

    bestcand : str, optional
        Best candidate realization name. Used only with parobj_file.

    parobj_file : str or pathlib.Path, optional
        CSV file containing parameter values for candidate realizations.

        It should contain:
            real_name
            parameter columns

    wd : str or pathlib.Path, optional
        Working directory for parobj_file if parobj_file is relative.

    savefig : bool, default False
        If True, save the figure.

    filename : str or pathlib.Path, optional
        Output filename.

    dpi : int, default 300
        Figure resolution for saving.

    show : bool, default False
        If True, call plt.show().

    Returns
    -------
    fig : matplotlib.figure.Figure
        Matplotlib figure object.

    axes : numpy.ndarray
        Array of matplotlib axes.
    """

    from pathlib import Path
    import math
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt

    # ------------------------------------------------------------------
    # Convert pyEMU ensemble-like objects to pandas DataFrames.
    #
    # This allows direct use of:
    #     pyemu.ParameterEnsemble.from_csv(...)
    #
    # or plain pandas DataFrames:
    #     pd.read_csv(..., index_col=0)
    # ------------------------------------------------------------------
    pr_pe = _ensemble_to_dataframe(pr_pe, name="pr_pe")
    pt_pe = _ensemble_to_dataframe(pt_pe, name="pt_pe")

    has_prior = pr_pe is not None
    has_posterior = pt_pe is not None

    if not has_prior and not has_posterior:
        raise ValueError("At least one of pr_pe or pt_pe must be provided.")

    # ------------------------------------------------------------------
    # Normalize ensemble column names to lowercase.
    #
    # PEST parameter names are commonly lowercase, but this makes the
    # function more robust if a CSV has mixed-case columns.
    # ------------------------------------------------------------------
    if has_prior:
        pr_pe = pr_pe.copy()
        pr_pe.columns = [str(c).lower() for c in pr_pe.columns]

    if has_posterior:
        pt_pe = pt_pe.copy()
        pt_pe.columns = [str(c).lower() for c in pt_pe.columns]

    # ------------------------------------------------------------------
    # Prepare pst.parameter_data safely.
    #
    # In pyEMU, parameter names are often stored as the dataframe index.
    # Sometimes "parnme" also exists as a column. If "parnme" is both an
    # index level and a column, pandas merge/filter operations can raise:
    #
    #     ValueError: 'parnme' is both an index level and a column label
    #
    # To avoid this, we force parameter names to be a normal column only,
    # and we remove index ambiguity.
    # ------------------------------------------------------------------
    par_data_raw = pst.parameter_data.copy()

    # Save original parameter names from the index before resetting it.
    index_parnmes = par_data_raw.index.astype(str)

    # Remove index name and reset to a simple integer index.
    par_data_raw.index.name = None
    par_data = par_data_raw.reset_index(drop=True)

    # If parnme column exists, keep it. If not, create it from the original index.
    if "parnme" not in par_data.columns:
        par_data["parnme"] = index_parnmes
    else:
        par_data["parnme"] = par_data["parnme"].astype(str)

    # Normalize parameter names.
    par_data["parnme"] = par_data["parnme"].str.lower()

    # ------------------------------------------------------------------
    # Required columns for histogram binning.
    # ------------------------------------------------------------------
    required_cols = ["parnme", "parlbnd", "parubnd"]
    missing_cols = [col for col in required_cols if col not in par_data.columns]

    if missing_cols:
        raise KeyError(
            f"pst.parameter_data is missing required columns: {missing_cols}"
        )

    # ------------------------------------------------------------------
    # Keep useful metadata columns if they exist.
    # ------------------------------------------------------------------
    meta_cols = ["parnme", "parlbnd", "parubnd"]

    for optional_col in ["partrans", "parchglim", "pargp", "scale", "offset"]:
        if optional_col in par_data.columns:
            meta_cols.append(optional_col)

    par_meta = par_data[meta_cols].copy()
    par_meta["parnme"] = par_meta["parnme"].astype(str).str.lower()

    # Make sure offset exists.
    # For normal parameters this is 0. For your pctchg offset approach,
    # this is needed to show actual relative change values.
    if "offset" not in par_meta.columns:
        par_meta["offset"] = 0.0

    par_meta["offset"] = pd.to_numeric(par_meta["offset"], errors="coerce").fillna(0.0)

    # ------------------------------------------------------------------
    # Identify parameter columns available in the provided ensembles.
    # ------------------------------------------------------------------
    available_pars = set()

    if has_prior:
        available_pars.update(pr_pe.columns)

    if has_posterior:
        available_pars.update(pt_pe.columns)

    # ------------------------------------------------------------------
    # Build selected parameter dataframe.
    #
    # sel_pars can be:
    #   1. None
    #   2. list/tuple/Index of parameter names
    #   3. DataFrame containing a "parnme" column
    # ------------------------------------------------------------------
    if sel_pars is None:
        sel_pars_df = par_meta.loc[
            par_meta["parnme"].isin(available_pars)
        ].copy()

    elif isinstance(sel_pars, pd.DataFrame):
        sel_pars_df = sel_pars.copy()

        # Remove index ambiguity if parnme is both index and column.
        sel_pars_df.index.name = None
        sel_pars_df = sel_pars_df.reset_index(drop=True)

        if "parnme" not in sel_pars_df.columns:
            raise KeyError("sel_pars DataFrame must contain a 'parnme' column.")

        sel_pars_df["parnme"] = sel_pars_df["parnme"].astype(str).str.lower()

        # Add missing metadata from pst.parameter_data.
        missing_from_sel = [
            col for col in ["parlbnd", "parubnd", "offset"]
            if col not in sel_pars_df.columns
        ]

        if missing_from_sel:
            sel_pars_df = sel_pars_df.merge(
                par_meta,
                on="parnme",
                how="left",
                suffixes=("", "_pst"),
            )

            for col in missing_from_sel:
                pst_col = f"{col}_pst"
                if pst_col in sel_pars_df.columns:
                    sel_pars_df[col] = sel_pars_df[pst_col]

            drop_cols = [
                col for col in sel_pars_df.columns
                if col.endswith("_pst")
            ]
            sel_pars_df.drop(columns=drop_cols, inplace=True)

    else:
        # Assume sel_pars is list-like.
        sel_pars = [str(p).lower() for p in list(sel_pars)]

        sel_pars_df = pd.DataFrame({"parnme": sel_pars})

        sel_pars_df = sel_pars_df.merge(
            par_meta,
            on="parnme",
            how="left",
        )

    # ------------------------------------------------------------------
    # Keep only parameters that exist in at least one provided ensemble.
    # ------------------------------------------------------------------
    sel_pars_df["parnme"] = sel_pars_df["parnme"].astype(str).str.lower()

    missing_from_ensemble = [
        p for p in sel_pars_df["parnme"].tolist()
        if p not in available_pars
    ]

    if missing_from_ensemble:
        print(
            "Skipped parameter(s) not found in parameter ensembles: "
            + ", ".join(missing_from_ensemble)
        )

    sel_pars_df = sel_pars_df.loc[
        sel_pars_df["parnme"].isin(available_pars)
    ].copy()

    if sel_pars_df.empty:
        raise ValueError(
            "No selected parameters were found in the provided ensemble(s)."
        )

    # ------------------------------------------------------------------
    # Make sure parameter bounds exist.
    # ------------------------------------------------------------------
    if sel_pars_df["parlbnd"].isna().any() or sel_pars_df["parubnd"].isna().any():
        missing_bound_pars = sel_pars_df.loc[
            sel_pars_df["parlbnd"].isna() | sel_pars_df["parubnd"].isna(),
            "parnme",
        ].tolist()

        raise ValueError(
            "Some selected parameters are missing bounds. "
            f"Example(s): {missing_bound_pars[:5]}"
        )

    sel_pars_df["parlbnd"] = pd.to_numeric(sel_pars_df["parlbnd"], errors="coerce")
    sel_pars_df["parubnd"] = pd.to_numeric(sel_pars_df["parubnd"], errors="coerce")
    sel_pars_df["offset"] = pd.to_numeric(
        sel_pars_df.get("offset", 0.0),
        errors="coerce",
    ).fillna(0.0)

    # ------------------------------------------------------------------
    # Read best-candidate parameter object file once, if requested.
    # Do not read this inside the loop.
    # ------------------------------------------------------------------
    bestcand_df = None

    if parobj_file is not None:
        parobj_path = Path(parobj_file)

        if not parobj_path.is_absolute() and wd is not None:
            parobj_path = Path(wd) / parobj_path

        bestcand_df = pd.read_csv(parobj_path)

        if "real_name" not in bestcand_df.columns:
            raise KeyError("parobj_file must contain a 'real_name' column.")

        if bestcand is None:
            raise ValueError("parobj_file was provided, but bestcand is None.")

        # Normalize parameter columns but preserve real_name.
        bestcand_df.columns = [
            "real_name" if str(c).lower() == "real_name" else str(c).lower()
            for c in bestcand_df.columns
        ]

    # ------------------------------------------------------------------
    # Create subplot layout.
    # squeeze=False makes axes always a 2D array, even with one row.
    # ------------------------------------------------------------------
    npars = len(sel_pars_df)
    nrows = math.ceil(npars / ncols)

    fig, axes = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        figsize=(width, height),
        squeeze=False,
    )

    # ------------------------------------------------------------------
    # Plot histograms.
    # ------------------------------------------------------------------
    first_legend_axis = True

    for i, ax in enumerate(axes.flat):
        if i >= npars:
            ax.axis("off")
            continue

        parnme = sel_pars_df.iloc[i]["parnme"]
        parlbnd = float(sel_pars_df.iloc[i]["parlbnd"])
        parubnd = float(sel_pars_df.iloc[i]["parubnd"])
        offset = float(sel_pars_df.iloc[i]["offset"])

        # Histogram bins are based on actual displayed values:
        #     PEST internal value + offset
        #
        # For your pctchg offset approach:
        #     internal 1 to 201, offset -101
        #     displayed -100 to +100
        bin_edges = np.linspace(
            parlbnd + offset,
            parubnd + offset,
            nbins + 1,
        )

        # --------------------------------------------------------------
        # Prior histogram
        # --------------------------------------------------------------
        if has_prior and parnme in pr_pe.columns:
            prior_vals = pr_pe[parnme].dropna().to_numpy(dtype=float) + offset

            ax.hist(
                prior_vals,
                bins=bin_edges,
                color="gray",
                alpha=0.5,
                density=False,
                label="Prior" if first_legend_axis else None,
            )

        # --------------------------------------------------------------
        # Posterior histogram
        # --------------------------------------------------------------
        if has_posterior and parnme in pt_pe.columns:
            post_vals = pt_pe[parnme].dropna().to_numpy(dtype=float) + offset

            ax.hist(
                post_vals,
                bins=bin_edges,
                alpha=0.5,
                density=False,
                label="Posterior" if first_legend_axis else None,
            )

        # --------------------------------------------------------------
        # Best-candidate vertical line
        # --------------------------------------------------------------
        if bestcand_df is not None:
            if parnme in bestcand_df.columns:
                match = bestcand_df.loc[
                    bestcand_df["real_name"] == bestcand,
                    parnme,
                ]

                if not match.empty:
                    x_best = float(match.iloc[0]) + offset

                    ax.axvline(
                        x=x_best,
                        color="red",
                        linestyle="--",
                        alpha=0.7,
                        label="Best candidate" if first_legend_axis else None,
                    )

        # --------------------------------------------------------------
        # Subplot formatting
        # --------------------------------------------------------------
        ax.set_title(
            parnme,
            fontsize=9,
            loc="left",
            x=0.05,
            y=0.92,
        )

        ax.tick_params(axis="x", labelsize=8)
        ax.tick_params(axis="y", labelsize=8)

        if first_legend_axis:
            handles, labels = ax.get_legend_handles_labels()
            if labels:
                ax.legend(fontsize=8)
            first_legend_axis = False

    # ------------------------------------------------------------------
    # Shared figure labels.
    # ------------------------------------------------------------------
    fig.supxlabel("Parameter relative change (%)", fontsize=10)
    fig.supylabel("Frequency", fontsize=10)

    plt.tight_layout()

    # ------------------------------------------------------------------
    # Save figure only when requested.
    # ------------------------------------------------------------------
    if savefig:
        if filename is None:
            filename = "parameter_ensemble.png"

        fig.savefig(filename, bbox_inches="tight", dpi=dpi)

    # ------------------------------------------------------------------
    # Show figure only when requested.
    # ------------------------------------------------------------------
    if show:
        plt.show()

    return fig, axes


def plot_ies_tseries_ensemble_by_group(
    pst=None,
    *,
    pr_oe=None,
    pt_oe=None,
    pt_fill=None,
    obs_groups=None,
    out_dir="ies_tseries",
    prefix="ies_tseries",
    width=10,
    height=3,
    dot=False,
    bstcd=None,
    ymin=None,
    ymax=None,
    auto_ylim_from_pt_fill=False,
    ylim_pad_fraction=0.10,
    include_obs_in_ylim=True,
    aggregate_freq=None,
    aggregate_func="mean",
    dpi=300,
    show=False,
    close=True,
    verbose=True,
    # auto-load IES options
    pst_file=None,
    model_dir=None,
    case=None,
    last_iter=None,
    auto_load_ies=False,
    auto_build_pt_fill=True,
):
    """
    Plot IES time-series ensemble figures for multiple observation groups.

    This is a batch wrapper around plot_tseries_ensemble().

    It supports the same IES auto-loading workflow as plot_tseries_ensemble(),
    but loads the IES output ensembles only once before looping through
    observation groups.

    Parameters
    ----------
    pst : pyemu.Pst, optional
        PEST control object.

    pr_oe : pandas.DataFrame or pyemu.ObservationEnsemble, optional
        Prior observation ensemble.

    pt_oe : pandas.DataFrame or pyemu.ObservationEnsemble, optional
        Posterior observation ensemble.

    pt_fill : pandas.DataFrame, optional
        Posterior uncertainty band dataframe.

    obs_groups : list-like, optional
        Observation groups to plot. If None, uses pst.nnz_obs_groups.

    out_dir : str or pathlib.Path
        Output directory for saved figures.

    prefix : str
        Prefix for output figure names.

    width, height : float
        Figure size in inches.

    dot : bool
        If True, plot ensemble realizations as scatter points.

    bstcd : str, optional
        Best-estimate realization name to plot from posterior ensemble.

    ymin, ymax : float, optional
        Manual y-axis limits.

    auto_ylim_from_pt_fill : bool
        If True, automatically set y-axis limits from posterior fill range.

    ylim_pad_fraction : float
        Padding fraction for automatic y-axis limits.

    include_obs_in_ylim : bool
        If True, observed values are included in automatic y-axis limits.

    aggregate_freq : str, optional
        Temporal aggregation frequency, e.g., "MS" for monthly mean.

    aggregate_func : str
        Aggregation function, e.g., "mean", "sum", "median".

    dpi : int
        Saved figure resolution.

    show : bool
        If True, display figures.

    close : bool
        If True, close figures after saving. Recommended for batch plotting.

    verbose : bool
        If True, print progress messages.

    pst_file, model_dir, case, last_iter : optional
        Inputs for automatic IES loading.

    auto_load_ies : bool
        If True, load prior/posterior observation ensembles automatically.

    auto_build_pt_fill : bool
        If True and auto_load_ies=True, also build posterior fill dataframe.

    Returns
    -------
    saved_files : dict
        Dictionary with observation group names as keys and saved file paths
        as values.
    """

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------
    # Load IES outputs once, not once per observation group.
    # --------------------------------------------------------------
    if auto_load_ies:
        ies = load_ies_observation_ensembles(
            pst=pst,
            pst_file=pst_file,
            model_dir=model_dir,
            case=case,
            last_iter=last_iter,
            build_pt_fill=auto_build_pt_fill,
        )

        pst = ies["pst"]

        if pr_oe is None:
            pr_oe = ies["pr_oe"]

        if pt_oe is None:
            pt_oe = ies["pt_oe"]

        if pt_fill is None and auto_build_pt_fill:
            pt_fill = ies["pt_fill"]

    if pst is None:
        raise ValueError(
            "pst is required. Provide pst directly or use auto_load_ies=True "
            "with pst_file."
        )

    if obs_groups is None:
        obs_groups = pst.nnz_obs_groups

    saved_files = {}

    for obgnam in obs_groups:
        try:
            if aggregate_freq is None:
                filename = out_dir / f"{prefix}_{obgnam}.png"
            else:
                filename = out_dir / f"{prefix}_{aggregate_freq}_{aggregate_func}_{obgnam}.png"

            fig, ax = plot_tseries_ensemble(
                pst=pst,
                obgnam=obgnam,
                pr_oe=pr_oe,
                pt_oe=pt_oe,
                width=width,
                height=height,
                dot=dot,
                bstcd=bstcd,
                pt_fill=pt_fill,
                ymin=ymin,
                ymax=ymax,
                auto_ylim_from_pt_fill=auto_ylim_from_pt_fill,
                ylim_pad_fraction=ylim_pad_fraction,
                include_obs_in_ylim=include_obs_in_ylim,
                aggregate_freq=aggregate_freq,
                aggregate_func=aggregate_func,
                savefig=True,
                filename=filename,
                dpi=dpi,
                show=show,
                auto_load_ies=False,  # already loaded above
            )

            if close:
                plt.close(fig)

            saved_files[obgnam] = filename

            if verbose:
                print(f"Saved time series: {obgnam}")

        except Exception as err:
            if verbose:
                print(f"Skipped time series {obgnam}: {err}")

    return saved_files


def plot_ies_fdc_ensemble_by_group(
    pst=None,
    *,
    pr_oe=None,
    pt_oe=None,
    obs_groups=None,
    out_dir="ies_fdc",
    prefix="ies_fdc",
    width=6,
    height=5,
    logy=True,
    posterior_band=True,
    posterior_band_quantiles=(0.05, 0.95),
    plot_prior_lines=True,
    plot_posterior_lines=False,
    obs_dot=False,
    obs_marker_size=18,
    obs_line=True,
    aggregate_freq=None,
    aggregate_func="mean",
    ymin=None,
    ymax=None,
    title=None,
    dpi=300,
    show=False,
    close=True,
    verbose=True,
    # auto-load IES options
    pst_file=None,
    model_dir=None,
    case=None,
    last_iter=None,
    auto_load_ies=False,
):
    """
    Plot IES flow-duration-curve ensemble figures for multiple observation groups.

    This is a batch wrapper around plot_fdc_ensemble().

    It supports the same auto_load_ies workflow as plot_fdc_ensemble(),
    but loads the PESTPP-IES output ensembles only once before looping through
    observation groups.

    Parameters
    ----------
    pst : pyemu.Pst, optional
        PEST control object.

    pr_oe : pandas.DataFrame or pyemu.ObservationEnsemble, optional
        Prior observation ensemble.

    pt_oe : pandas.DataFrame or pyemu.ObservationEnsemble, optional
        Posterior observation ensemble.

    obs_groups : list-like, optional
        Observation groups to plot. If None, uses pst.nnz_obs_groups.

    out_dir : str or pathlib.Path
        Output directory for saved figures.

    prefix : str
        Prefix for output figure names.

    width, height : float
        Figure size in inches.

    logy : bool
        If True, use log scale for the y-axis.

    posterior_band : bool
        If True, plot posterior FDC uncertainty band.

    posterior_band_quantiles : tuple
        Lower and upper quantiles for posterior FDC band.

    plot_prior_lines : bool
        If True, plot individual prior ensemble FDCs.

    plot_posterior_lines : bool
        If True, plot individual posterior ensemble FDCs.

    obs_dot : bool
        If True, plot observed FDC as points.

    obs_marker_size : float
        Marker size for observed FDC points.

    obs_line : bool
        If True, plot observed FDC as a line.

    aggregate_freq : str, optional
        Temporal aggregation frequency before FDC calculation.
        Example: "MS" for monthly mean FDC.

    aggregate_func : str
        Aggregation function before FDC calculation.

    ymin, ymax : float, optional
        Manual y-axis limits.

    title : str, optional
        Optional title. If None, plot_fdc_ensemble() generates one.

    dpi : int
        Saved figure resolution.

    show : bool
        If True, display figures.

    close : bool
        If True, close figures after saving.

    verbose : bool
        If True, print progress messages.

    pst_file, model_dir, case, last_iter : optional
        Inputs for automatic IES loading.

    auto_load_ies : bool
        If True, load prior/posterior observation ensembles automatically.

    Returns
    -------
    results : dict
        Dictionary with saved file paths and FDC data by observation group.
    """

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------
    # Load IES outputs once, not once per observation group.
    # --------------------------------------------------------------
    if auto_load_ies:
        ies = load_ies_observation_ensembles(
            pst=pst,
            pst_file=pst_file,
            model_dir=model_dir,
            case=case,
            last_iter=last_iter,
            build_pt_fill=False,
        )

        pst = ies["pst"]

        if pr_oe is None:
            pr_oe = ies["pr_oe"]

        if pt_oe is None:
            pt_oe = ies["pt_oe"]

    if pst is None:
        raise ValueError(
            "pst is required. Provide pst directly or use auto_load_ies=True "
            "with pst_file."
        )

    if obs_groups is None:
        obs_groups = pst.nnz_obs_groups

    saved_files = {}
    fdc_data_by_group = {}

    for obgnam in obs_groups:
        try:
            if aggregate_freq is None:
                filename = out_dir / f"{prefix}_{obgnam}.png"
            else:
                filename = out_dir / f"{prefix}_{aggregate_freq}_{aggregate_func}_{obgnam}.png"

            fig, ax, fdc_data = plot_fdc_ensemble(
                pst=pst,
                obgnam=obgnam,
                pr_oe=pr_oe,
                pt_oe=pt_oe,
                width=width,
                height=height,
                logy=logy,
                posterior_band=posterior_band,
                posterior_band_quantiles=posterior_band_quantiles,
                plot_prior_lines=plot_prior_lines,
                plot_posterior_lines=plot_posterior_lines,
                obs_dot=obs_dot,
                obs_marker_size=obs_marker_size,
                obs_line=obs_line,
                aggregate_freq=aggregate_freq,
                aggregate_func=aggregate_func,
                ymin=ymin,
                ymax=ymax,
                title=title,
                savefig=True,
                filename=filename,
                dpi=dpi,
                show=show,
                auto_load_ies=False,  # already loaded above
            )

            if close:
                plt.close(fig)

            saved_files[obgnam] = filename
            fdc_data_by_group[obgnam] = fdc_data

            if verbose:
                print(f"Saved FDC: {obgnam}")

        except Exception as err:
            if verbose:
                print(f"Skipped FDC {obgnam}: {err}")

    return {
        "files": saved_files,
        "fdc_data": fdc_data_by_group,
    }


def animate_tseries_ensemble_by_realization(
    pst=None,
    obgnam=None,
    *,
    pr_oe=None,
    pt_oe=None,
    width=10,
    height=3,
    bstcd=None,
    pt_fill=None,
    ymin=None,
    ymax=None,
    auto_ylim_from_pt_fill=False,
    ylim_pad_fraction=0.10,
    include_obs_in_ylim=True,
    aggregate_freq=None,
    aggregate_func="mean",
    pst_file=None,
    model_dir=None,
    case=None,
    last_iter=None,
    auto_load_ies=False,
    auto_build_pt_fill=True,
    max_prior_realizations=None,
    max_posterior_realizations=None,
    show_prior=True,
    show_posterior=True,
    show_observed=True,
    show_posterior_band=False,
    animate_only_posterior=False,
    prior_label="Prior ensemble",
    posterior_label="Posterior ensemble",
    observed_label="Observed",
    title=None,
    ylabel="Discharge",
    save_path=None,
    writer="pillow",
    fps=8,
    interval=250,
    pause_seconds=2.0,
    repeat=True,
    dpi=150,
    show=False,
    close=False,
    save_first_last_figures=False,
    first_last_dir=None,
    first_fig_name=None,
    last_fig_name=None,
):
    """
    Animate a time-series ensemble plot by adding ensemble realizations one by one.

    This is not a time-progress animation. The full time axis is shown from
    the beginning, and each frame adds another prior and/or posterior
    realization.

    If animate_only_posterior=True, all prior realizations are drawn
    statically first, and only posterior realizations are animated.
    """

    from pathlib import Path

    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.animation import FuncAnimation, PillowWriter, FFMpegWriter

    if obgnam is None:
        raise ValueError("obgnam must be provided.")

    # ------------------------------------------------------------------
    # Helper for making saved GIF non-looping.
    # ------------------------------------------------------------------
    def _make_gif_nonlooping(gif_path):
        try:
            from PIL import Image, ImageSequence
        except ImportError as err:
            raise ImportError(
                "Pillow is required to post-process GIF repeat behavior. "
                "Install it with: pip install pillow"
            ) from err

        gif_path = Path(gif_path)

        im = Image.open(gif_path)
        frames = [frame.copy() for frame in ImageSequence.Iterator(im)]

        if not frames:
            return

        # Use fps directly. Do not read duration from im.info, because
        # pause frames can make all frames slow after post-processing.
        frame_duration = int(1000 / fps)

        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=frame_duration,
            loop=1,
        )

    # ------------------------------------------------------------------
    # Optional automatic loading for PESTPP-IES outputs.
    # ------------------------------------------------------------------
    if auto_load_ies:
        ies = load_ies_observation_ensembles(
            pst=pst,
            pst_file=pst_file,
            model_dir=model_dir,
            case=case,
            last_iter=last_iter,
            build_pt_fill=auto_build_pt_fill,
        )

        pst = ies["pst"]

        if pr_oe is None:
            pr_oe = ies["pr_oe"]

        if pt_oe is None:
            pt_oe = ies["pt_oe"]

        if pt_fill is None and auto_build_pt_fill:
            pt_fill = ies["pt_fill"]

    if pst is None:
        raise ValueError(
            "pst is required. Provide pst directly or use auto_load_ies=True "
            "with pst_file."
        )

    # ------------------------------------------------------------------
    # Convert pyEMU ensemble-like objects to pandas DataFrames.
    # ------------------------------------------------------------------
    pr_oe = _ensemble_to_dataframe(pr_oe, name="pr_oe")
    pt_oe = _ensemble_to_dataframe(pt_oe, name="pt_oe")

    has_prior = pr_oe is not None and show_prior
    has_posterior = pt_oe is not None and show_posterior

    if not has_prior and not has_posterior:
        raise ValueError("At least one of pr_oe or pt_oe must be provided.")

    animate_prior = has_prior and not animate_only_posterior
    animate_posterior = has_posterior

    if animate_only_posterior and not has_posterior:
        raise ValueError(
            "animate_only_posterior=True requires posterior ensemble data (pt_oe)."
        )

    # ------------------------------------------------------------------
    # Get observation data from PEST control file.
    # ------------------------------------------------------------------
    obs = pst.observation_data.copy()
    obs = obs.loc[obs.obgnme.isin(pst.nnz_obs_groups)].copy()

    obs["time"] = pd.to_datetime(obs.obsnme.str[-8:], errors="coerce")

    oobs = obs.loc[obs.obgnme == obgnam].copy()

    if oobs.empty:
        raise ValueError(f"No observations found for observation group: {obgnam}")

    oobs = oobs.dropna(subset=["time"]).copy()

    if oobs.empty:
        raise ValueError(
            f"Observations were found for {obgnam}, but no valid dates could be parsed "
            "from the last 8 characters of obsnme."
        )

    oobs.sort_values("time", inplace=True)

    tvals = oobs.time.to_numpy()
    onames = oobs.obsnme.to_numpy()

    # ------------------------------------------------------------------
    # Prepare prior ensemble.
    # ------------------------------------------------------------------
    if has_prior:
        pr_oe = pr_oe.where(pr_oe > -999)

        missing_prior_cols = [name for name in onames if name not in pr_oe.columns]

        if missing_prior_cols:
            raise KeyError(
                f"{len(missing_prior_cols)} observation names are missing from pr_oe. "
                f"Example missing name: {missing_prior_cols[0]}"
            )

    # ------------------------------------------------------------------
    # Prepare posterior ensemble.
    # ------------------------------------------------------------------
    if has_posterior:
        pt_oe = pt_oe.where(pt_oe > -999)

        missing_post_cols = [name for name in onames if name not in pt_oe.columns]

        if missing_post_cols:
            raise KeyError(
                f"{len(missing_post_cols)} observation names are missing from pt_oe. "
                f"Example missing name: {missing_post_cols[0]}"
            )

    # ------------------------------------------------------------------
    # Prepare observed values with non-zero weight.
    # ------------------------------------------------------------------
    oobs_nonzero = oobs.loc[oobs.weight > 0].copy()

    # ------------------------------------------------------------------
    # Optional temporal aggregation.
    # ------------------------------------------------------------------
    if aggregate_freq is not None:

        obs_agg = aggregate_series(
            oobs_nonzero["obsval"].to_numpy(),
            oobs_nonzero["time"].to_numpy(),
            freq=aggregate_freq,
            func=aggregate_func,
        )

        if obs_agg.empty:
            raise ValueError(
                f"No valid aggregated observed values for observation group: {obgnam}"
            )

        tvals = obs_agg.index.to_numpy()

        oobs_nonzero = pd.DataFrame(
            {
                "time": obs_agg.index,
                "obsval": obs_agg.values,
                "weight": 1.0,
            }
        )

        daily_onames = onames.copy()
        daily_times = oobs["time"].to_numpy()

        if has_prior:
            pr_oe = aggregate_observation_ensemble(
                pr_oe,
                obs_names=daily_onames,
                times=daily_times,
                freq=aggregate_freq,
                func=aggregate_func,
                reference_index=obs_agg.index,
            )

        if has_posterior:
            pt_oe = aggregate_observation_ensemble(
                pt_oe,
                obs_names=daily_onames,
                times=daily_times,
                freq=aggregate_freq,
                func=aggregate_func,
                reference_index=obs_agg.index,
            )

        onames = obs_agg.index

    onames = pd.Index(onames)
    tvals = pd.to_datetime(tvals)

    # ------------------------------------------------------------------
    # Prepare posterior uncertainty band.
    # ------------------------------------------------------------------
    if aggregate_freq is not None and has_posterior:
        df_fill = build_posterior_fill(
            pt_oe,
            obgnam=obgnam,
            obs_names=onames,
            times=onames,
        )

    elif pt_fill is not None:
        required_cols = {"obgnme", "pt_min", "pt_max"}
        missing_cols = required_cols.difference(pt_fill.columns)

        if missing_cols:
            raise KeyError(
                f"pt_fill is missing required columns: {sorted(missing_cols)}"
            )

        df_fill = pt_fill.loc[pt_fill["obgnme"] == obgnam].copy()

        if df_fill.empty:
            raise ValueError(f"No pt_fill records found for observation group: {obgnam}")

        df_fill = df_fill.sort_index()

    else:
        df_fill = None

    # ------------------------------------------------------------------
    # Select realizations.
    # ------------------------------------------------------------------
    if has_prior:
        prior_reals = list(pr_oe.index)
        if max_prior_realizations is not None:
            prior_reals = prior_reals[:max_prior_realizations]
    else:
        prior_reals = []

    if has_posterior:
        posterior_reals = list(pt_oe.index)
        if max_posterior_realizations is not None:
            posterior_reals = posterior_reals[:max_posterior_realizations]
    else:
        posterior_reals = []

    if animate_only_posterior:
        n_frames = len(posterior_reals)
    else:
        n_frames = max(len(prior_reals), len(posterior_reals))

    if n_frames == 0:
        raise ValueError("No realizations available to animate.")

    pause_frames = int(fps * pause_seconds)
    total_frames = n_frames + pause_frames

    # ------------------------------------------------------------------
    # Automatically set y-axis limits from posterior uncertainty band.
    # ------------------------------------------------------------------
    if auto_ylim_from_pt_fill and df_fill is not None and ymin is None and ymax is None:
        y_values = []

        y_values.extend(df_fill["pt_min"].dropna().to_numpy(dtype=float))
        y_values.extend(df_fill["pt_max"].dropna().to_numpy(dtype=float))

        if include_obs_in_ylim and not oobs_nonzero.empty:
            y_values.extend(oobs_nonzero["obsval"].dropna().to_numpy(dtype=float))

        y_values = np.asarray(y_values, dtype=float)
        y_values = y_values[np.isfinite(y_values)]

        if y_values.size > 0:
            y_min_auto = y_values.min()
            y_max_auto = y_values.max()
            y_range = y_max_auto - y_min_auto

            if y_range == 0:
                pad = abs(y_max_auto) * ylim_pad_fraction
                if pad == 0:
                    pad = 1.0
            else:
                pad = y_range * ylim_pad_fraction

            ymin = y_min_auto - pad
            ymax = y_max_auto + pad

    # ------------------------------------------------------------------
    # Fallback y-axis limits.
    # ------------------------------------------------------------------
    if ymin is None or ymax is None:
        y_values = []

        if has_prior and prior_reals:
            y_values.extend(
                pr_oe.loc[prior_reals, onames].to_numpy(dtype=float).ravel()
            )

        if has_posterior and posterior_reals:
            y_values.extend(
                pt_oe.loc[posterior_reals, onames].to_numpy(dtype=float).ravel()
            )

        if not oobs_nonzero.empty:
            y_values.extend(oobs_nonzero["obsval"].dropna().to_numpy(dtype=float))

        y_values = np.asarray(y_values, dtype=float)
        y_values = y_values[np.isfinite(y_values)]

        if y_values.size > 0:
            y_min_auto = y_values.min()
            y_max_auto = y_values.max()
            y_range = y_max_auto - y_min_auto

            if y_range == 0:
                pad = abs(y_max_auto) * ylim_pad_fraction
                if pad == 0:
                    pad = 1.0
            else:
                pad = y_range * ylim_pad_fraction

            if ymin is None:
                ymin = y_min_auto - pad

            if ymax is None:
                ymax = y_max_auto + pad

    # ------------------------------------------------------------------
    # Create figure.
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(width, height))

    ax.set_xlim(tvals.min(), tvals.max())

    if ymin is not None or ymax is not None:
        ax.set_ylim(ymin, ymax)

    ax.set_ylabel(ylabel)

    if title is None:
        if animate_only_posterior:
            if aggregate_freq is None:
                title = f"Posterior realization animation on prior: {obgnam}"
            else:
                title = (
                    f"Posterior realization animation on prior "
                    f"({aggregate_freq}, {aggregate_func}): {obgnam}"
                )
        else:
            if aggregate_freq is None:
                title = f"Ensemble realization animation: {obgnam}"
            else:
                title = (
                    f"Ensemble realization animation "
                    f"({aggregate_freq}, {aggregate_func}): {obgnam}"
                )

    ax.set_title(title)
    ax.grid(True, alpha=0.3)

    # ------------------------------------------------------------------
    # Optional posterior band shown from beginning.
    # ------------------------------------------------------------------
    if show_posterior_band and df_fill is not None:
        ax.fill_between(
            df_fill.index,
            df_fill["pt_min"].to_numpy(dtype=float),
            df_fill["pt_max"].to_numpy(dtype=float),
            interpolate=False,
            color="b",
            alpha=0.20,
            label="Posterior range",
            zorder=2,
        )

        ax.plot(
            df_fill.index,
            df_fill["pt_min"].to_numpy(dtype=float),
            color="b",
            lw=0.8,
            alpha=0.5,
            zorder=2,
        )

        ax.plot(
            df_fill.index,
            df_fill["pt_max"].to_numpy(dtype=float),
            color="b",
            lw=0.8,
            alpha=0.5,
            zorder=2,
        )

    # ------------------------------------------------------------------
    # Draw prior statically if requested.
    # ------------------------------------------------------------------
    if animate_only_posterior and has_prior:
        for idx, realization in enumerate(prior_reals):
            ax.plot(
                tvals,
                pr_oe.loc[realization, onames].to_numpy(dtype=float),
                color="0.5",
                lw=0.5,
                alpha=0.45,
                zorder=1,
                label=prior_label if idx == 0 else None,
            )

    # ------------------------------------------------------------------
    # Observed values shown from beginning.
    # ------------------------------------------------------------------
    if show_observed:
        ax.scatter(
            oobs_nonzero.time,
            oobs_nonzero.obsval,
            edgecolor="red",
            facecolor="none",
            s=14,
            zorder=5,
            alpha=0.8,
            label=observed_label,
        )

    # ------------------------------------------------------------------
    # Best-estimate line shown from beginning.
    # ------------------------------------------------------------------
    if bstcd is not None:
        if not has_posterior:
            raise ValueError("bstcd was provided, but pt_oe is None.")

        if bstcd not in pt_oe.index:
            raise KeyError(
                f"Best-estimate realization '{bstcd}' was not found in pt_oe.index."
            )

        ax.plot(
            tvals,
            pt_oe.loc[bstcd, onames].to_numpy(dtype=float),
            color="b",
            lw=1.5,
            zorder=4,
            label="Best estimate",
        )

    # ------------------------------------------------------------------
    # Axis formatting.
    # ------------------------------------------------------------------
    years = mdates.YearLocator()
    years_fmt = mdates.DateFormatter("%Y")

    months = mdates.MonthLocator()
    months_fmt = mdates.DateFormatter("%b")

    ax.xaxis.set_major_locator(years)
    ax.xaxis.set_major_formatter(years_fmt)

    ax.xaxis.set_minor_locator(months)
    ax.xaxis.set_minor_formatter(months_fmt)

    plt.setp(ax.xaxis.get_minorticklabels(), fontsize=6, rotation=90)

    ax.tick_params(axis="both", labelsize=8, rotation=0)
    ax.tick_params(axis="x", pad=15)
    ax.margins(x=0.01)

    # ------------------------------------------------------------------
    # Frame text.
    # ------------------------------------------------------------------
    frame_text = ax.text(
        0.98,
        0.95,
        "",
        transform=ax.transAxes,
        va="top",
        ha="right",
        fontsize=9,
        bbox={
            "boxstyle": "round",
            "facecolor": "white",
            "alpha": 0.8,
        },
    )

    # ------------------------------------------------------------------
    # Dummy artists for legend.
    # ------------------------------------------------------------------
    if animate_prior:
        ax.plot(
            [],
            [],
            color="0.5",
            lw=0.5,
            alpha=0.45,
            label=prior_label,
            zorder=1,
        )

    if has_posterior:
        ax.plot(
            [],
            [],
            color="b",
            lw=0.5,
            alpha=0.40,
            label=posterior_label,
            zorder=3,
        )

    handles, labels = ax.get_legend_handles_labels()

    if labels:
        unique = {}
        for handle, label in zip(handles, labels):
            if label not in unique:
                unique[label] = handle

        ax.legend(
            unique.values(),
            unique.keys(),
            fontsize=8,
            ncol=3,
        )

    fig.tight_layout()

    # ------------------------------------------------------------------
    # Optional first/last static figure paths.
    # ------------------------------------------------------------------
    if save_first_last_figures:
        if first_last_dir is None:
            if save_path is not None:
                first_last_dir = Path(save_path).parent
            else:
                first_last_dir = Path(".")

        first_last_dir = Path(first_last_dir)
        first_last_dir.mkdir(parents=True, exist_ok=True)

        if first_fig_name is None:
            first_fig_name = f"{obgnam}_ensemble_first.png"

        if last_fig_name is None:
            last_fig_name = f"{obgnam}_ensemble_last.png"

        first_fig_path = first_last_dir / first_fig_name
        last_fig_path = first_last_dir / last_fig_name
    else:
        first_fig_path = None
        last_fig_path = None

    # ------------------------------------------------------------------
    # Animation update.
    # ------------------------------------------------------------------
    plotted_artists = {
        "prior": [],
        "posterior": [],
    }

    saved_first = {"done": False}
    saved_last = {"done": False}

    def update(frame):
        artists = []

        if frame >= n_frames:
            i = n_frames - 1
            is_pause = True
        else:
            i = frame
            is_pause = False

        # Animate prior only if requested.
        if not is_pause and animate_prior and i < len(prior_reals):
            realization = prior_reals[i]

            y = pr_oe.loc[realization, onames].to_numpy(dtype=float)

            ln, = ax.plot(
                tvals,
                y,
                color="0.5",
                lw=0.5,
                alpha=0.45,
                zorder=1,
            )

            plotted_artists["prior"].append(ln)
            artists.append(ln)

        # Animate posterior.
        if not is_pause and animate_posterior and i < len(posterior_reals):
            realization = posterior_reals[i]

            y = pt_oe.loc[realization, onames].to_numpy(dtype=float)

            ln, = ax.plot(
                tvals,
                y,
                color="b",
                lw=0.5,
                alpha=0.40,
                zorder=3,
            )

            plotted_artists["posterior"].append(ln)
            artists.append(ln)

        if animate_only_posterior:
            n_prior = len(prior_reals) if has_prior else 0
            n_post = min(i + 1, len(posterior_reals)) if has_posterior else 0
        else:
            n_prior = min(i + 1, len(prior_reals)) if has_prior else 0
            n_post = min(i + 1, len(posterior_reals)) if has_posterior else 0

        frame_text.set_text(
            f"Prior realizations: {n_prior}\n"
            f"Posterior realizations: {n_post}"
        )

        artists.append(frame_text)

        # Optional first and last static figures.
        if save_first_last_figures and not is_pause:
            if frame == 0 and first_fig_path is not None and not saved_first["done"]:
                fig.savefig(first_fig_path, dpi=dpi, bbox_inches="tight")
                saved_first["done"] = True

            if (
                frame == n_frames - 1
                and last_fig_path is not None
                and not saved_last["done"]
            ):
                fig.savefig(last_fig_path, dpi=dpi, bbox_inches="tight")
                saved_last["done"] = True

        return artists

    anim = FuncAnimation(
        fig,
        update,
        frames=total_frames,
        interval=interval,
        blit=False,
        repeat=repeat,
    )

    # ------------------------------------------------------------------
    # Save animation.
    # ------------------------------------------------------------------
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        if writer.lower() == "pillow":
            anim.save(
                save_path,
                writer=PillowWriter(fps=fps),
                dpi=dpi,
            )

            if repeat is False:
                _make_gif_nonlooping(save_path)

        elif writer.lower() == "ffmpeg":
            anim.save(
                save_path,
                writer=FFMpegWriter(fps=fps),
                dpi=dpi,
            )

        else:
            raise ValueError("writer must be either 'pillow' or 'ffmpeg'.")

    if show:
        plt.show()

    if close:
        plt.close(fig)

    return anim, fig, ax


def animate_fdc_ensemble_by_realization(
    pst=None,
    obgnam=None,
    *,
    pst_file=None,
    model_dir=None,
    case=None,
    last_iter=None,
    auto_load_ies=False,
    pr_oe=None,
    pt_oe=None,
    width=6,
    height=5,
    logy=True,
    posterior_band=False,
    posterior_band_quantiles=(0.05, 0.95),
    animate_only_posterior=False,
    show_prior=True,
    show_posterior=True,
    show_observed=True,
    obs_dot=False,
    obs_marker_size=18,
    obs_line=True,
    max_prior_realizations=None,
    max_posterior_realizations=None,
    aggregate_freq=None,
    aggregate_func="mean",
    ymin=None,
    ymax=None,
    title=None,
    xlabel="Exceedance probability (%)",
    ylabel=None,
    prior_label="Prior ensemble",
    posterior_label="Posterior ensemble",
    observed_label="Observed",
    save_path=None,
    writer="pillow",
    fps=8,
    interval=250,
    pause_seconds=2.0,
    repeat=True,
    dpi=150,
    show=False,
    close=False,
    save_first_last_figures=False,
    first_last_dir=None,
    first_fig_name=None,
    last_fig_name=None,
):
    """
    Animate FDC ensemble plots by adding ensemble realizations one by one.

    This is not a time-progress animation. Each frame adds another full
    flow-duration curve realization.

    If animate_only_posterior=True, all prior FDCs are drawn statically first,
    and only posterior FDCs are animated.
    """

    from pathlib import Path

    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter, FFMpegWriter

    if obgnam is None:
        raise ValueError("obgnam must be provided.")

    # ------------------------------------------------------------------
    # Helper for making saved GIF non-looping.
    # ------------------------------------------------------------------
    def _make_gif_nonlooping(gif_path):
        try:
            from PIL import Image, ImageSequence
        except ImportError as err:
            raise ImportError(
                "Pillow is required to post-process GIF repeat behavior. "
                "Install it with: pip install pillow"
            ) from err

        gif_path = Path(gif_path)

        im = Image.open(gif_path)
        frames = [frame.copy() for frame in ImageSequence.Iterator(im)]

        if not frames:
            return

        # Use fps directly. Do not read duration from im.info, because
        # pause frames can make all frames slow after post-processing.
        frame_duration = int(1000 / fps)

        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=frame_duration,
            loop=1,
        )

    # ------------------------------------------------------------------
    # Optional automatic loading for PESTPP-IES output files.
    # ------------------------------------------------------------------
    if auto_load_ies:
        ies = load_ies_observation_ensembles(
            pst=pst,
            pst_file=pst_file,
            model_dir=model_dir,
            case=case,
            last_iter=last_iter,
            build_pt_fill=False,
        )

        pst = ies["pst"]

        if pr_oe is None:
            pr_oe = ies["pr_oe"]

        if pt_oe is None:
            pt_oe = ies["pt_oe"]

    if pst is None:
        raise ValueError("pst must be provided, or use pst_file with auto_load_ies=True.")

    # ------------------------------------------------------------------
    # Convert pyEMU ensemble-like objects to pandas DataFrames.
    # ------------------------------------------------------------------
    pr_oe = _ensemble_to_dataframe(pr_oe, name="pr_oe")
    pt_oe = _ensemble_to_dataframe(pt_oe, name="pt_oe")

    has_prior = pr_oe is not None and show_prior
    has_posterior = pt_oe is not None and show_posterior

    if not has_prior and not has_posterior:
        raise ValueError("At least one of pr_oe or pt_oe must be provided.")

    animate_prior = has_prior and not animate_only_posterior
    animate_posterior = has_posterior

    if animate_only_posterior and not has_posterior:
        raise ValueError(
            "animate_only_posterior=True requires posterior ensemble data (pt_oe)."
        )

    # ------------------------------------------------------------------
    # Get observation data from the PEST control file.
    # ------------------------------------------------------------------
    obs = pst.observation_data.copy()
    obs = obs.loc[obs.obgnme.isin(pst.nnz_obs_groups)].copy()

    # Assumes the last 8 characters are YYYYMMDD.
    obs["time"] = pd.to_datetime(obs.obsnme.str[-8:], errors="coerce")

    oobs = obs.loc[obs.obgnme == obgnam].copy()

    if oobs.empty:
        raise ValueError(f"No observations found for observation group: {obgnam}")

    oobs = oobs.dropna(subset=["time"]).copy()

    if oobs.empty:
        raise ValueError(
            f"Observations were found for {obgnam}, but no valid dates could be parsed."
        )

    oobs.sort_values("time", inplace=True)

    onames = oobs.obsnme.to_numpy()
    times = oobs["time"].to_numpy()

    # ------------------------------------------------------------------
    # Prepare observed values.
    # ------------------------------------------------------------------
    oobs_nonzero = oobs.loc[oobs.weight > 0].copy()

    obs_values = pd.to_numeric(oobs_nonzero.obsval, errors="coerce")
    obs_times = oobs_nonzero["time"].to_numpy()

    if aggregate_freq is not None:
        obs_values = aggregate_series(
            obs_values.to_numpy(),
            obs_times,
            freq=aggregate_freq,
            func=aggregate_func,
        )
    else:
        obs_values = obs_values.dropna()
        obs_values = obs_values.loc[obs_values > -999]

    if obs_values.empty:
        raise ValueError(f"No valid observed values found for group: {obgnam}")

    # ------------------------------------------------------------------
    # Prepare prior ensemble.
    # ------------------------------------------------------------------
    if has_prior:
        pr_oe = pr_oe.where(pr_oe > -999)

        missing_prior_cols = [name for name in onames if name not in pr_oe.columns]

        if missing_prior_cols:
            raise KeyError(
                f"{len(missing_prior_cols)} observation names are missing from pr_oe. "
                f"Example missing name: {missing_prior_cols[0]}"
            )

    # ------------------------------------------------------------------
    # Prepare posterior ensemble.
    # ------------------------------------------------------------------
    if has_posterior:
        pt_oe = pt_oe.where(pt_oe > -999)

        missing_post_cols = [name for name in onames if name not in pt_oe.columns]

        if missing_post_cols:
            raise KeyError(
                f"{len(missing_post_cols)} observation names are missing from pt_oe. "
                f"Example missing name: {missing_post_cols[0]}"
            )

    # ------------------------------------------------------------------
    # Helper to get one realization's values.
    # ------------------------------------------------------------------
    def _get_realization_values(ensemble_df, realization):
        values = ensemble_df.loc[realization, onames]

        if aggregate_freq is not None:
            return aggregate_series(
                values.to_numpy(),
                times,
                freq=aggregate_freq,
                func=aggregate_func,
            )

        return values

    # ------------------------------------------------------------------
    # Helper to calculate one FDC.
    # ------------------------------------------------------------------
    def _calculate_fdc(values):
        values = pd.Series(values)
        values = pd.to_numeric(values, errors="coerce").dropna()
        values = values.loc[values > -999]

        if logy:
            values = values.loc[values > 0]

        if values.empty:
            return None, None

        sorted_values = np.sort(values.to_numpy(dtype=float))[::-1]
        n = len(sorted_values)

        exceedance = np.arange(1, n + 1) / (n + 1) * 100.0

        return exceedance, sorted_values

    # ------------------------------------------------------------------
    # Helper to calculate posterior FDC uncertainty band.
    # ------------------------------------------------------------------
    def _calculate_fdc_band(ensemble_df, quantiles=(0.05, 0.95)):
        fdc_arrays = []
        exceedance_ref = None
        expected_length = None

        for realization in ensemble_df.index:
            values = _get_realization_values(ensemble_df, realization)
            x, y = _calculate_fdc(values)

            if x is None:
                continue

            if expected_length is None:
                expected_length = len(y)
                exceedance_ref = x

            if len(y) != expected_length:
                continue

            fdc_arrays.append(y)

        if not fdc_arrays:
            return None

        fdc_matrix = np.vstack(fdc_arrays)

        q_low, q_high = quantiles

        return {
            "exceedance": exceedance_ref,
            "low": np.nanquantile(fdc_matrix, q_low, axis=0),
            "high": np.nanquantile(fdc_matrix, q_high, axis=0),
            "median": np.nanmedian(fdc_matrix, axis=0),
            "matrix": fdc_matrix,
        }

    # ------------------------------------------------------------------
    # Calculate observed FDC.
    # ------------------------------------------------------------------
    x_obs, y_obs = _calculate_fdc(obs_values)

    if x_obs is None:
        raise ValueError(f"Could not calculate observed FDC for group: {obgnam}")

    # ------------------------------------------------------------------
    # Select realizations.
    # ------------------------------------------------------------------
    if has_prior:
        prior_reals = list(pr_oe.index)

        if max_prior_realizations is not None:
            prior_reals = prior_reals[:max_prior_realizations]
    else:
        prior_reals = []

    if has_posterior:
        posterior_reals = list(pt_oe.index)

        if max_posterior_realizations is not None:
            posterior_reals = posterior_reals[:max_posterior_realizations]
    else:
        posterior_reals = []

    if animate_only_posterior:
        n_frames = len(posterior_reals)
    else:
        n_frames = max(len(prior_reals), len(posterior_reals))

    if n_frames == 0:
        raise ValueError("No realizations available to animate.")

    pause_frames = int(fps * pause_seconds)
    total_frames = n_frames + pause_frames

    # ------------------------------------------------------------------
    # Optional posterior FDC band.
    # ------------------------------------------------------------------
    pt_band = None

    if posterior_band and has_posterior:
        pt_band = _calculate_fdc_band(
            pt_oe,
            quantiles=posterior_band_quantiles,
        )

    # ------------------------------------------------------------------
    # Automatic y-axis limits.
    # ------------------------------------------------------------------
    if ymin is None or ymax is None:
        y_values = []

        if len(y_obs) > 0:
            y_values.extend(y_obs)

        if pt_band is not None:
            y_values.extend(pt_band["low"])
            y_values.extend(pt_band["high"])

        if has_prior and prior_reals:
            for realization in prior_reals:
                x_tmp, y_tmp = _calculate_fdc(
                    _get_realization_values(pr_oe, realization)
                )
                if y_tmp is not None:
                    y_values.extend(y_tmp)

        if has_posterior and posterior_reals:
            for realization in posterior_reals:
                x_tmp, y_tmp = _calculate_fdc(
                    _get_realization_values(pt_oe, realization)
                )
                if y_tmp is not None:
                    y_values.extend(y_tmp)

        y_values = np.asarray(y_values, dtype=float)
        y_values = y_values[np.isfinite(y_values)]

        if logy:
            y_values = y_values[y_values > 0]

        if y_values.size > 0:
            y_min_auto = y_values.min()
            y_max_auto = y_values.max()

            if logy:
                ymin_auto = y_min_auto * 0.8
                ymax_auto = y_max_auto * 1.2
            else:
                y_range = y_max_auto - y_min_auto

                if y_range == 0:
                    pad = abs(y_max_auto) * 0.10
                    if pad == 0:
                        pad = 1.0
                else:
                    pad = y_range * 0.10

                ymin_auto = y_min_auto - pad
                ymax_auto = y_max_auto + pad

            if ymin is None:
                ymin = ymin_auto

            if ymax is None:
                ymax = ymax_auto

    # ------------------------------------------------------------------
    # Create figure.
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(width, height))

    ax.set_xlabel(xlabel)

    if ylabel is None:
        if aggregate_freq is None:
            ylabel = "Flow"
        else:
            ylabel = f"{aggregate_func.capitalize()} flow"

    ax.set_ylabel(ylabel)

    ax.set_xlim(0, 100)

    if logy:
        ax.set_yscale("log")

    if ymin is not None or ymax is not None:
        ax.set_ylim(ymin, ymax)

    ax.grid(True, which="both", alpha=0.3)

    # ------------------------------------------------------------------
    # Optional posterior band shown from beginning.
    # ------------------------------------------------------------------
    if pt_band is not None:
        ax.fill_between(
            pt_band["exceedance"],
            pt_band["low"],
            pt_band["high"],
            color="b",
            alpha=0.20,
            label=(
                f"Posterior "
                f"{posterior_band_quantiles[0]:.0%}-"
                f"{posterior_band_quantiles[1]:.0%} range"
            ),
            zorder=2,
        )

        ax.plot(
            pt_band["exceedance"],
            pt_band["median"],
            color="b",
            lw=1.4,
            alpha=0.9,
            label="Posterior median",
            zorder=3,
        )

    # ------------------------------------------------------------------
    # Draw prior statically if animate_only_posterior=True.
    # ------------------------------------------------------------------
    if animate_only_posterior and has_prior:
        for idx, realization in enumerate(prior_reals):
            x, y = _calculate_fdc(_get_realization_values(pr_oe, realization))

            if x is None:
                continue

            ax.plot(
                x,
                y,
                color="0.5",
                lw=0.5,
                alpha=0.30,
                label=prior_label if idx == 0 else None,
                zorder=1,
            )

    # ------------------------------------------------------------------
    # Observed FDC shown from beginning.
    # ------------------------------------------------------------------
    if show_observed:
        if obs_line:
            ax.plot(
                x_obs,
                y_obs,
                color="red",
                lw=1.8,
                label=observed_label if not obs_dot else "Observed line",
                zorder=5,
            )

        if obs_dot:
            ax.scatter(
                x_obs,
                y_obs,
                edgecolor="red",
                facecolor="none",
                s=obs_marker_size,
                alpha=0.8,
                label=observed_label if not obs_line else "Observed points",
                zorder=6,
            )

    # ------------------------------------------------------------------
    # Title.
    # ------------------------------------------------------------------
    if title is not None:
        ax.set_title(title)
    else:
        if animate_only_posterior:
            if aggregate_freq is None:
                ax.set_title(f"Posterior FDC realization animation on prior: {obgnam}")
            else:
                ax.set_title(
                    f"Posterior FDC realization animation on prior "
                    f"({aggregate_freq}, {aggregate_func}): {obgnam}"
                )
        else:
            if aggregate_freq is None:
                ax.set_title(f"FDC ensemble realization animation: {obgnam}")
            else:
                ax.set_title(
                    f"FDC ensemble realization animation "
                    f"({aggregate_freq}, {aggregate_func}): {obgnam}"
                )

    # ------------------------------------------------------------------
    # Frame text.
    # ------------------------------------------------------------------
    frame_text = ax.text(
        0.98,
        0.95,
        "",
        transform=ax.transAxes,
        va="top",
        ha="right",
        fontsize=9,
        bbox={
            "boxstyle": "round",
            "facecolor": "white",
            "alpha": 0.8,
        },
    )

    # ------------------------------------------------------------------
    # Dummy artists for legend.
    # ------------------------------------------------------------------
    if animate_prior:
        ax.plot(
            [],
            [],
            color="0.5",
            lw=0.5,
            alpha=0.30,
            label=prior_label,
            zorder=1,
        )

    if has_posterior:
        ax.plot(
            [],
            [],
            color="b",
            lw=0.5,
            alpha=0.40,
            label=posterior_label,
            zorder=3,
        )

    handles, labels = ax.get_legend_handles_labels()

    if labels:
        unique = {}

        for handle, label in zip(handles, labels):
            if label not in unique:
                unique[label] = handle

        ax.legend(
            unique.values(),
            unique.keys(),
            fontsize=8,
        )

    fig.tight_layout()

    # ------------------------------------------------------------------
    # Optional first/last static figure paths.
    # ------------------------------------------------------------------
    if save_first_last_figures:
        if first_last_dir is None:
            if save_path is not None:
                first_last_dir = Path(save_path).parent
            else:
                first_last_dir = Path(".")

        first_last_dir = Path(first_last_dir)
        first_last_dir.mkdir(parents=True, exist_ok=True)

        if first_fig_name is None:
            first_fig_name = f"{obgnam}_fdc_first.png"

        if last_fig_name is None:
            last_fig_name = f"{obgnam}_fdc_last.png"

        first_fig_path = first_last_dir / first_fig_name
        last_fig_path = first_last_dir / last_fig_name
    else:
        first_fig_path = None
        last_fig_path = None

    # ------------------------------------------------------------------
    # Animation update.
    # ------------------------------------------------------------------
    saved_first = {"done": False}
    saved_last = {"done": False}

    def update(frame):
        artists = []

        if frame >= n_frames:
            i = n_frames - 1
            is_pause = True
        else:
            i = frame
            is_pause = False

        # Animate prior only if requested.
        if not is_pause and animate_prior and i < len(prior_reals):
            realization = prior_reals[i]

            x, y = _calculate_fdc(_get_realization_values(pr_oe, realization))

            if x is not None:
                ln, = ax.plot(
                    x,
                    y,
                    color="0.5",
                    lw=0.5,
                    alpha=0.30,
                    zorder=1,
                )
                artists.append(ln)

        # Animate posterior.
        if not is_pause and animate_posterior and i < len(posterior_reals):
            realization = posterior_reals[i]

            x, y = _calculate_fdc(_get_realization_values(pt_oe, realization))

            if x is not None:
                ln, = ax.plot(
                    x,
                    y,
                    color="b",
                    lw=0.5,
                    alpha=0.40,
                    zorder=3,
                )
                artists.append(ln)

        if animate_only_posterior:
            n_prior = len(prior_reals) if has_prior else 0
            n_post = min(i + 1, len(posterior_reals)) if has_posterior else 0
        else:
            n_prior = min(i + 1, len(prior_reals)) if has_prior else 0
            n_post = min(i + 1, len(posterior_reals)) if has_posterior else 0

        frame_text.set_text(
            f"Prior realizations: {n_prior}\n"
            f"Posterior realizations: {n_post}"
        )

        artists.append(frame_text)

        # Optional first and last static figures.
        if save_first_last_figures and not is_pause:
            if frame == 0 and first_fig_path is not None and not saved_first["done"]:
                fig.savefig(first_fig_path, dpi=dpi, bbox_inches="tight")
                saved_first["done"] = True

            if (
                frame == n_frames - 1
                and last_fig_path is not None
                and not saved_last["done"]
            ):
                fig.savefig(last_fig_path, dpi=dpi, bbox_inches="tight")
                saved_last["done"] = True

        return artists

    anim = FuncAnimation(
        fig,
        update,
        frames=total_frames,
        interval=interval,
        blit=False,
        repeat=repeat,
    )

    # ------------------------------------------------------------------
    # Save animation.
    # ------------------------------------------------------------------
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        if writer.lower() == "pillow":
            anim.save(
                save_path,
                writer=PillowWriter(fps=fps),
                dpi=dpi,
            )

            if repeat is False:
                _make_gif_nonlooping(save_path)

        elif writer.lower() == "ffmpeg":
            anim.save(
                save_path,
                writer=FFMpegWriter(fps=fps),
                dpi=dpi,
            )

        else:
            raise ValueError("writer must be either 'pillow' or 'ffmpeg'.")

    if show:
        plt.show()

    if close:
        plt.close(fig)

    return anim, fig, ax


def animate_parameter_ensemble_by_realization(
    pst=None,
    *,
    pst_file=None,
    model_dir=None,
    case=None,
    last_iter=None,
    auto_load_ies=False,
    pr_pe=None,
    pt_pe=None,
    sel_pars=None,
    width=7,
    height=5,
    ncols=3,
    nbins=20,
    bestcand=None,
    parobj_file=None,
    wd=None,
    show_prior=True,
    show_posterior=True,
    animate_only_posterior=True,
    prior_label="Prior",
    posterior_label="Posterior",
    bestcand_label="Best candidate",
    prior_color="0.70",
    posterior_color="tab:blue",
    save_path=None,
    writer="pillow",
    fps=8,
    interval=250,
    pause_seconds=2.0,
    repeat=True,
    dpi=150,
    show=False,
    close=False,
    save_first_last_figures=False,
    first_last_dir=None,
    first_fig_name=None,
    last_fig_name=None,
    verbose=True,
):
    """
    Animate prior/posterior parameter ensemble histograms by realization.

    Fixed version:
    - Does not call ax.hist() during animation frames.
    - Precomputes cumulative histogram counts.
    - Creates bars once and updates bar heights.
    - Uses fixed colors so colors do not change during animation.
    """

    from pathlib import Path
    import math
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter, FFMpegWriter
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D

    def _log(message):
        if verbose:
            print(message, flush=True)

    def _make_gif_nonlooping(gif_path):
        try:
            from PIL import Image, ImageSequence
        except ImportError as err:
            raise ImportError(
                "Pillow is required to post-process GIF repeat behavior. "
                "Install it with: pip install pillow"
            ) from err

        gif_path = Path(gif_path)

        im = Image.open(gif_path)
        frames = [frame.copy() for frame in ImageSequence.Iterator(im)]

        if not frames:
            return

        # Force duration from fps.
        frame_duration = int(1000 / fps)

        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=frame_duration,
            loop=1,
        )

    def _values_to_cumulative_counts(values, bin_edges):
        """
        Convert one value per realization to cumulative histogram counts.

        Output shape:
            n_realizations x n_bins
        """

        values = pd.to_numeric(
            pd.Series(values),
            errors="coerce",
        ).to_numpy(dtype=float)

        n_reals = len(values)
        n_bins = len(bin_edges) - 1

        per_real_counts = np.zeros((n_reals, n_bins), dtype=float)

        for i, val in enumerate(values):
            if not np.isfinite(val):
                continue

            bin_idx = np.searchsorted(bin_edges, val, side="right") - 1

            # Include value exactly equal to rightmost edge.
            if bin_idx == n_bins and np.isclose(val, bin_edges[-1]):
                bin_idx = n_bins - 1

            if 0 <= bin_idx < n_bins:
                per_real_counts[i, bin_idx] = 1.0

        return np.cumsum(per_real_counts, axis=0)

    _log("Preparing parameter ensemble animation...")

    # ------------------------------------------------------------------
    # Optional automatic loading for PESTPP-IES parameter ensembles.
    # ------------------------------------------------------------------
    if auto_load_ies:
        _log("Loading IES parameter ensembles...")

        ies = load_ies_parameter_ensembles(
            pst=pst,
            pst_file=pst_file,
            model_dir=model_dir,
            case=case,
            last_iter=last_iter,
        )

        pst = ies["pst"]

        if pr_pe is None:
            pr_pe = ies["pr_pe"]

        if pt_pe is None:
            pt_pe = ies["pt_pe"]

        _log(
            f"Loaded parameter ensembles: "
            f"prior={ies['prior_par_file'].name}, "
            f"posterior={ies['posterior_par_file'].name}"
        )

    if pst is None:
        raise ValueError(
            "pst is required. Provide pst directly or use auto_load_ies=True "
            "with pst_file."
        )

    # ------------------------------------------------------------------
    # Convert ensembles.
    # ------------------------------------------------------------------
    pr_pe = _ensemble_to_dataframe(pr_pe, name="pr_pe")
    pt_pe = _ensemble_to_dataframe(pt_pe, name="pt_pe")

    has_prior = pr_pe is not None and show_prior
    has_posterior = pt_pe is not None and show_posterior

    if not has_prior and not has_posterior:
        raise ValueError("At least one of pr_pe or pt_pe must be provided.")

    if animate_only_posterior and not has_posterior:
        raise ValueError(
            "animate_only_posterior=True requires posterior parameter ensemble pt_pe."
        )

    animate_prior = has_prior and not animate_only_posterior
    animate_posterior = has_posterior

    # Normalize parameter names in ensembles.
    if has_prior:
        pr_pe = pr_pe.copy()
        pr_pe.columns = [str(c).lower() for c in pr_pe.columns]

    if has_posterior:
        pt_pe = pt_pe.copy()
        pt_pe.columns = [str(c).lower() for c in pt_pe.columns]

    # ------------------------------------------------------------------
    # Prepare pst.parameter_data safely.
    # ------------------------------------------------------------------
    _log("Preparing parameter metadata...")

    par_data_raw = pst.parameter_data.copy()
    index_parnmes = par_data_raw.index.astype(str)

    par_data_raw.index.name = None
    par_data = par_data_raw.reset_index(drop=True)

    if "parnme" not in par_data.columns:
        par_data["parnme"] = index_parnmes
    else:
        par_data["parnme"] = par_data["parnme"].astype(str)

    par_data["parnme"] = par_data["parnme"].str.lower()

    required_cols = ["parnme", "parlbnd", "parubnd"]
    missing_cols = [c for c in required_cols if c not in par_data.columns]

    if missing_cols:
        raise KeyError(
            f"pst.parameter_data is missing required columns: {missing_cols}"
        )

    meta_cols = ["parnme", "parlbnd", "parubnd"]

    for optional_col in ["partrans", "parchglim", "pargp", "scale", "offset"]:
        if optional_col in par_data.columns:
            meta_cols.append(optional_col)

    par_meta = par_data[meta_cols].copy()
    par_meta["parnme"] = par_meta["parnme"].astype(str).str.lower()

    if "offset" not in par_meta.columns:
        par_meta["offset"] = 0.0

    par_meta["offset"] = pd.to_numeric(
        par_meta["offset"],
        errors="coerce",
    ).fillna(0.0)

    # ------------------------------------------------------------------
    # Identify available parameters.
    # ------------------------------------------------------------------
    available_pars = set()

    if has_prior:
        available_pars.update(pr_pe.columns)

    if has_posterior:
        available_pars.update(pt_pe.columns)

    # ------------------------------------------------------------------
    # Build selected parameter dataframe.
    # ------------------------------------------------------------------
    if sel_pars is None:
        sel_pars_df = par_meta.loc[
            par_meta["parnme"].isin(available_pars)
        ].copy()

    elif isinstance(sel_pars, pd.DataFrame):
        sel_pars_df = sel_pars.copy()
        sel_pars_df.index.name = None
        sel_pars_df = sel_pars_df.reset_index(drop=True)

        if "parnme" not in sel_pars_df.columns:
            raise KeyError("sel_pars DataFrame must contain a 'parnme' column.")

        sel_pars_df["parnme"] = sel_pars_df["parnme"].astype(str).str.lower()

        missing_from_sel = [
            col for col in ["parlbnd", "parubnd", "offset"]
            if col not in sel_pars_df.columns
        ]

        if missing_from_sel:
            sel_pars_df = sel_pars_df.merge(
                par_meta,
                on="parnme",
                how="left",
                suffixes=("", "_pst"),
            )

            for col in missing_from_sel:
                pst_col = f"{col}_pst"
                if pst_col in sel_pars_df.columns:
                    sel_pars_df[col] = sel_pars_df[pst_col]

            drop_cols = [
                col for col in sel_pars_df.columns
                if col.endswith("_pst")
            ]
            sel_pars_df.drop(columns=drop_cols, inplace=True)

    else:
        sel_pars = [str(p).lower() for p in list(sel_pars)]

        sel_pars_df = pd.DataFrame({"parnme": sel_pars})

        sel_pars_df = sel_pars_df.merge(
            par_meta,
            on="parnme",
            how="left",
        )

    sel_pars_df["parnme"] = sel_pars_df["parnme"].astype(str).str.lower()

    missing_from_ensemble = [
        p for p in sel_pars_df["parnme"].tolist()
        if p not in available_pars
    ]

    if missing_from_ensemble:
        _log(
            "Skipped parameter(s) not found in parameter ensembles: "
            + ", ".join(missing_from_ensemble)
        )

    sel_pars_df = sel_pars_df.loc[
        sel_pars_df["parnme"].isin(available_pars)
    ].copy()

    if sel_pars_df.empty:
        raise ValueError(
            "No selected parameters were found in the provided ensemble(s)."
        )

    if sel_pars_df["parlbnd"].isna().any() or sel_pars_df["parubnd"].isna().any():
        missing_bound_pars = sel_pars_df.loc[
            sel_pars_df["parlbnd"].isna() | sel_pars_df["parubnd"].isna(),
            "parnme",
        ].tolist()

        raise ValueError(
            "Some selected parameters are missing bounds. "
            f"Example(s): {missing_bound_pars[:5]}"
        )

    sel_pars_df["parlbnd"] = pd.to_numeric(
        sel_pars_df["parlbnd"],
        errors="coerce",
    )
    sel_pars_df["parubnd"] = pd.to_numeric(
        sel_pars_df["parubnd"],
        errors="coerce",
    )
    sel_pars_df["offset"] = pd.to_numeric(
        sel_pars_df.get("offset", 0.0),
        errors="coerce",
    ).fillna(0.0)

    _log(f"Selected {len(sel_pars_df)} parameter(s).")

    # ------------------------------------------------------------------
    # Best-candidate file.
    # ------------------------------------------------------------------
    bestcand_df = None

    if parobj_file is not None:
        parobj_path = Path(parobj_file)

        if not parobj_path.is_absolute() and wd is not None:
            parobj_path = Path(wd) / parobj_path

        _log(f"Loading best-candidate parameter file: {parobj_path}")

        bestcand_df = pd.read_csv(parobj_path)

        if "real_name" not in bestcand_df.columns:
            raise KeyError("parobj_file must contain a 'real_name' column.")

        if bestcand is None:
            raise ValueError("parobj_file was provided, but bestcand is None.")

        bestcand_df.columns = [
            "real_name" if str(c).lower() == "real_name" else str(c).lower()
            for c in bestcand_df.columns
        ]

    # ------------------------------------------------------------------
    # Realizations.
    # ------------------------------------------------------------------
    prior_reals = list(pr_pe.index) if has_prior else []
    posterior_reals = list(pt_pe.index) if has_posterior else []

    if animate_only_posterior:
        n_frames = len(posterior_reals)
    else:
        n_frames = max(len(prior_reals), len(posterior_reals))

    if n_frames == 0:
        raise ValueError("No realizations available to animate.")

    pause_frames = int(fps * pause_seconds)
    total_frames = n_frames + pause_frames

    _log(
        f"Animation frames: {n_frames} realization frames "
        f"+ {pause_frames} pause frames = {total_frames} total frames."
    )

    # ------------------------------------------------------------------
    # Figure layout.
    # ------------------------------------------------------------------
    npars = len(sel_pars_df)
    nrows = math.ceil(npars / ncols)

    fig, axes = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        figsize=(width, height),
        squeeze=False,
    )

    # ------------------------------------------------------------------
    # Precompute histograms and create bars once.
    # ------------------------------------------------------------------
    _log("Precomputing histogram counts...")

    par_plot_info = []

    for i, ax in enumerate(axes.flat):
        if i >= npars:
            ax.axis("off")
            continue

        row = sel_pars_df.iloc[i]

        parnme = row["parnme"]
        parlbnd = float(row["parlbnd"])
        parubnd = float(row["parubnd"])
        offset = float(row["offset"])

        bin_edges = np.linspace(
            parlbnd + offset,
            parubnd + offset,
            nbins + 1,
        )

        bin_lefts = bin_edges[:-1]
        bin_widths = np.diff(bin_edges)

        prior_full_counts = np.zeros(nbins, dtype=float)
        posterior_full_counts = np.zeros(nbins, dtype=float)

        prior_cum_counts = None
        posterior_cum_counts = None

        if has_prior and parnme in pr_pe.columns:
            prior_values = (
                pd.to_numeric(pr_pe.loc[prior_reals, parnme], errors="coerce")
                .to_numpy(dtype=float)
                + offset
            )

            prior_full_counts, _ = np.histogram(prior_values, bins=bin_edges)

            if animate_prior:
                prior_cum_counts = _values_to_cumulative_counts(
                    prior_values,
                    bin_edges,
                )

        if has_posterior and parnme in pt_pe.columns:
            posterior_values = (
                pd.to_numeric(pt_pe.loc[posterior_reals, parnme], errors="coerce")
                .to_numpy(dtype=float)
                + offset
            )

            posterior_full_counts, _ = np.histogram(
                posterior_values,
                bins=bin_edges,
            )

            if animate_posterior:
                posterior_cum_counts = _values_to_cumulative_counts(
                    posterior_values,
                    bin_edges,
                )

        max_count = max(
            1,
            int(np.nanmax(prior_full_counts)) if prior_full_counts.size else 1,
            int(np.nanmax(posterior_full_counts)) if posterior_full_counts.size else 1,
        )

        # --------------------------------------------------------------
        # Static prior: full prior distribution shown from beginning.
        # --------------------------------------------------------------
        if animate_only_posterior and has_prior and parnme in pr_pe.columns:
            ax.bar(
                bin_lefts,
                prior_full_counts,
                width=bin_widths,
                align="edge",
                color=prior_color,
                alpha=0.65,
                edgecolor="none",
                zorder=1,
            )

        # --------------------------------------------------------------
        # Animated prior: starts at zero and grows.
        # --------------------------------------------------------------
        animated_prior_bars = None

        if animate_prior and has_prior and parnme in pr_pe.columns:
            animated_prior_bars = ax.bar(
                bin_lefts,
                np.zeros(nbins),
                width=bin_widths,
                align="edge",
                color=prior_color,
                alpha=0.65,
                edgecolor="none",
                zorder=1,
            )

        # --------------------------------------------------------------
        # Animated posterior: starts at zero and grows.
        # --------------------------------------------------------------
        animated_posterior_bars = None

        if animate_posterior and has_posterior and parnme in pt_pe.columns:
            animated_posterior_bars = ax.bar(
                bin_lefts,
                np.zeros(nbins),
                width=bin_widths,
                align="edge",
                color=posterior_color,
                alpha=0.65,
                edgecolor="none",
                zorder=2,
            )

        # --------------------------------------------------------------
        # Best-candidate vertical line.
        # --------------------------------------------------------------
        if bestcand_df is not None and parnme in bestcand_df.columns:
            match = bestcand_df.loc[
                bestcand_df["real_name"] == bestcand,
                parnme,
            ]

            if not match.empty:
                x_best = float(match.iloc[0]) + offset

                ax.axvline(
                    x=x_best,
                    color="red",
                    linestyle="--",
                    alpha=0.7,
                    zorder=3,
                )

        ax.set_title(
            parnme,
            fontsize=9,
            loc="left",
            x=0.05,
            y=0.92,
        )

        ax.tick_params(axis="x", labelsize=8)
        ax.tick_params(axis="y", labelsize=8)

        ax.set_xlim(bin_edges[0], bin_edges[-1])
        ax.set_ylim(0, max_count * 1.15)

        par_plot_info.append(
            {
                "prior_cum_counts": prior_cum_counts,
                "posterior_cum_counts": posterior_cum_counts,
                "animated_prior_bars": animated_prior_bars,
                "animated_posterior_bars": animated_posterior_bars,
            }
        )

    fig.supxlabel("Parameter relative change (%)", fontsize=10)
    fig.supylabel("Frequency", fontsize=10)

    # ------------------------------------------------------------------
    # Legend.
    # ------------------------------------------------------------------
    legend_handles = []

    if has_prior:
        legend_handles.append(
            Patch(
                facecolor=prior_color,
                alpha=0.65,
                edgecolor="none",
                label=prior_label,
            )
        )

    if has_posterior:
        legend_handles.append(
            Patch(
                facecolor=posterior_color,
                alpha=0.65,
                edgecolor="none",
                label=posterior_label,
            )
        )

    if bestcand_df is not None:
        legend_handles.append(
            Line2D(
                [0],
                [0],
                color="red",
                linestyle="--",
                alpha=0.7,
                label=bestcand_label,
            )
        )

    if legend_handles:
        axes.flat[0].legend(
            handles=legend_handles,
            fontsize=8,
        )

    # ------------------------------------------------------------------
    # Frame text.
    # ------------------------------------------------------------------
    frame_text = fig.text(
        0.99,
        0.99,
        "",
        va="top",
        ha="right",
        fontsize=9,
        bbox={
            "boxstyle": "round",
            "facecolor": "white",
            "alpha": 0.8,
        },
    )

    plt.tight_layout()

    # ------------------------------------------------------------------
    # First/last static figure paths.
    # ------------------------------------------------------------------
    if save_first_last_figures:
        if first_last_dir is None:
            if save_path is not None:
                first_last_dir = Path(save_path).parent
            else:
                first_last_dir = Path(".")

        first_last_dir = Path(first_last_dir)
        first_last_dir.mkdir(parents=True, exist_ok=True)

        if first_fig_name is None:
            first_fig_name = "parameter_ensemble_first.png"

        if last_fig_name is None:
            last_fig_name = "parameter_ensemble_last.png"

        first_fig_path = first_last_dir / first_fig_name
        last_fig_path = first_last_dir / last_fig_name
    else:
        first_fig_path = None
        last_fig_path = None

    saved_first = {"done": False}
    saved_last = {"done": False}

    # ------------------------------------------------------------------
    # Animation update.
    # ------------------------------------------------------------------
    def update(frame):
        artists = []

        if frame >= n_frames:
            i = n_frames - 1
            is_pause = True
        else:
            i = frame
            is_pause = False

        for info in par_plot_info:
            prior_cum_counts = info["prior_cum_counts"]
            posterior_cum_counts = info["posterior_cum_counts"]

            animated_prior_bars = info["animated_prior_bars"]
            animated_posterior_bars = info["animated_posterior_bars"]

            if animated_prior_bars is not None and prior_cum_counts is not None:
                idx = min(i, prior_cum_counts.shape[0] - 1)
                counts = prior_cum_counts[idx, :]

                for patch, height in zip(animated_prior_bars, counts):
                    patch.set_height(height)
                    artists.append(patch)

            if animated_posterior_bars is not None and posterior_cum_counts is not None:
                idx = min(i, posterior_cum_counts.shape[0] - 1)
                counts = posterior_cum_counts[idx, :]

                for patch, height in zip(animated_posterior_bars, counts):
                    patch.set_height(height)
                    artists.append(patch)

        if animate_only_posterior:
            n_prior = len(prior_reals) if has_prior else 0
            n_post = min(i + 1, len(posterior_reals)) if has_posterior else 0
        else:
            n_prior = min(i + 1, len(prior_reals)) if has_prior else 0
            n_post = min(i + 1, len(posterior_reals)) if has_posterior else 0

        frame_text.set_text(
            f"Prior realizations: {n_prior}\n"
            f"Posterior realizations: {n_post}"
        )

        artists.append(frame_text)

        if save_first_last_figures and not is_pause:
            if frame == 0 and first_fig_path is not None and not saved_first["done"]:
                fig.savefig(first_fig_path, dpi=dpi, bbox_inches="tight")
                saved_first["done"] = True

            if (
                frame == n_frames - 1
                and last_fig_path is not None
                and not saved_last["done"]
            ):
                fig.savefig(last_fig_path, dpi=dpi, bbox_inches="tight")
                saved_last["done"] = True

        return artists

    anim = FuncAnimation(
        fig,
        update,
        frames=total_frames,
        interval=interval,
        blit=False,
        repeat=repeat,
    )

    # ------------------------------------------------------------------
    # Save animation.
    # ------------------------------------------------------------------
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        def _progress_callback(current_frame, total_frames_to_save):
            if verbose:
                print(
                    f"Saving frame {current_frame + 1}/{total_frames_to_save}",
                    end="\r",
                    flush=True,
                )

        if writer.lower() == "pillow":
            _log(f"Saving GIF to: {save_path}")

            anim.save(
                save_path,
                writer=PillowWriter(fps=fps),
                dpi=dpi,
                progress_callback=_progress_callback,
            )

            if verbose:
                print()

            if repeat is False:
                _log("Post-processing GIF repeat setting...")
                _make_gif_nonlooping(save_path)

            _log("Done saving GIF.")

        elif writer.lower() == "ffmpeg":
            _log(f"Saving MP4 to: {save_path}")

            anim.save(
                save_path,
                writer=FFMpegWriter(fps=fps),
                dpi=dpi,
                progress_callback=_progress_callback,
            )

            if verbose:
                print()

            _log("Done saving MP4.")

        else:
            raise ValueError("writer must be either 'pillow' or 'ffmpeg'.")

    if show:
        plt.show()

    if close:
        plt.close(fig)

    return anim, fig, axes


if __name__ == "__main__":
    from pathlib import Path
    import matplotlib.pyplot as plt

    # --------------------------------------------------------------
    # Change this path to your current IES master folder.
    # --------------------------------------------------------------
    
    model_dir = Path(
        r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration_v02\ihydrocal_workspace\pecos_rw_ies"
    )

    # '''
    pst_file = model_dir / "pecos_rw_ies.pst"

    # --------------------------------------------------------------
    # Load IES observation ensembles.
    # This should automatically find:
    #   pecos_rw_ies.0.obs.csv
    #   pecos_rw_ies.<last_iter>.obs.csv
    # --------------------------------------------------------------
    ies = load_ies_observation_ensembles(
        pst_file=pst_file,
        last_iter=None,
        build_pt_fill=True,
    )

    pst = ies["pst"]
    pr_oe = ies["pr_oe"]
    pt_oe = ies["pt_oe"]
    pt_fill = ies["pt_fill"]
    # pt_oe = pd.read_csv(model_dir / "pecos_rw_ies.4.obs_demo_wide.csv", index_col=0)

    print("Case:", ies["case"])
    print("Last iteration:", ies["last_iter"])
    print("Prior observation ensemble:", pr_oe.shape)
    print("Posterior observation ensemble:", pt_oe.shape)
    print("Posterior fill:", pt_fill.shape)
    print("Observation groups:", pst.nnz_obs_groups)

    # --------------------------------------------------------------
    # Pick one observation group for testing.
    # --------------------------------------------------------------
    obgnam = pst.nnz_obs_groups[0]
    print("Testing observation group:", obgnam)

    # --------------------------------------------------------------
    # 1. Time-series ensemble plot
    # --------------------------------------------------------------
    # fig, ax = plot_tseries_ensemble(
    #     pst,
    #     obgnam=obgnam,
    #     pr_oe=pr_oe,
    #     pt_oe=pt_oe,
    #     # aggregate_freq="MS",
    #     # aggregate_func="mean",
    #     pt_fill=pt_fill,
    #     width=11,
    #     height=4,
    #     dot=False,
    #     auto_ylim_from_pt_fill=True,
    #     ylim_pad_fraction=0.15,
    #     include_obs_in_ylim=True,
    #     show=True,
    # )

    # --------------------------------------------------------------
    # 2. FDC ensemble plot
    # --------------------------------------------------------------
    # fig, ax, fdc_data = plot_fdc_ensemble(
    #     pst=pst,
    #     obgnam=obgnam,
    #     pr_oe=pr_oe,
    #     pt_oe=pt_oe,
    #     width=6,
    #     height=5,
    #     logy=True,
    #     posterior_band=True,
    #     posterior_band_quantiles=(0.05, 0.95),
    #     plot_prior_lines=True,
    #     plot_posterior_lines=False,
    #     aggregate_freq="MS",
    #     aggregate_func="mean",
    #     obs_dot=True,
    #     obs_line=False,
    #     obs_marker_size=18,
    #     show=True,
    # )

    
    # --------------------------------------------------------------
    # Batch export all IES diagnostic figures
    # --------------------------------------------------------------
    fig_dir = model_dir / "figures" / "ies"
    tseries_dir = fig_dir / "tseries"
    fdc_dir = fig_dir / "fdc"

    tseries_dir.mkdir(parents=True, exist_ok=True)
    fdc_dir.mkdir(parents=True, exist_ok=True)

    for obgnam in pst.nnz_obs_groups:
        print(f"Processing: {obgnam}")

        try:
            fig, ax = plot_tseries_ensemble(
                pst,
                obgnam=obgnam,
                pr_oe=pr_oe,
                pt_oe=pt_oe,
                # aggregate_freq="MS",
                # aggregate_func="mean",
                pt_fill=pt_fill,
                width=10,
                height=5,
                dot=False,
                auto_ylim_from_pt_fill=True,
                ylim_pad_fraction=0.15,
                include_obs_in_ylim=True,
                savefig=True,
                filename=tseries_dir / f"ies_tseries_{obgnam}.png",
                dpi=300,
                show=False,
            )
            plt.close(fig)

        except Exception as err:
            print(f"  Skipped time series: {err}")

        try:
            fig, ax, fdc_data = plot_fdc_ensemble(
                pst=pst,
                obgnam=obgnam,
                pr_oe=pr_oe,
                pt_oe=pt_oe,
                width=6,
                height=5,
                logy=True,
                posterior_band=True,
                posterior_band_quantiles=(0.05, 0.95),
                plot_prior_lines=True,
                plot_posterior_lines=False,
                obs_dot=True,
                obs_line=False,
                obs_marker_size=18,
                savefig=True,
                filename=fdc_dir / f"ies_fdc_{obgnam}.png",
                dpi=300,
                show=False,
            )
            plt.close(fig)

        except Exception as err:
            print(f"  Skipped FDC: {err}")

    print("Batch IES figures completed.")
    # '''

    # model_dir = Path(
    #     r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration_v02\ihydrocal_workspace\pecos_rw_ies"
    # )

    # pst_file = model_dir / "pecos_rw_ies.pst"
    # pst = pyemu.Pst(str(pst_file))

    # case = "pecos_rw_ies"
    # last_iter = 4

    # pr_pe = pd.read_csv(model_dir / f"{case}.0.par.csv", index_col=0)
    # pt_pe = pd.read_csv(model_dir / f"{case}.{last_iter}.par.csv", index_col=0)

    # print(pr_pe.shape)
    # print(pt_pe.shape)
    # print(pr_pe.columns)

    # par = pst.parameter_data.copy()

    # # Make a clean dataframe where parnme is only a column, not both index and column
    # par = par.reset_index(drop=True)

    # # If parnme still does not exist as a column, create it from the original index
    # if "parnme" not in par.columns:
    #     par["parnme"] = pst.parameter_data.index

    # sel_pars = par.loc[
    #     par["partrans"].str.lower() == "log",
    #     ["parnme", "parlbnd", "parubnd", "offset"]
    # ].copy()

    # print(sel_pars)


    # sel_pars = [
    #     "chl", "cn2", "chk", "lat_len", "flo_min", "canmx", "chd", "awc",
    #        "chs", 
         
    # ]


    # sel_pars = [
    #     "alpha", "awc", "canmx", "chd", "chk", "chl", "chn", "chs", "chw",
    #     "cn2", "cn3_swf", "epco", "esco", "flo_min", "lat_len",
    #     "latq_co", "perco", "petco", "revap_co", "surlag",
    # ]

    # fig, axes = plot_parameter_ensemble(
    #     pst,
    #     pr_pe=pr_pe,
    #     pt_pe=pt_pe,
    #     sel_pars=sel_pars,
    #     width=9,
    #     height=6,
    #     ncols=3,
    #     nbins=20,
    #     show=True,
    #     savefig=True,
    # )


    # # --------------------------------------------------------------
    # # IES phi diagnostic figures
    # # --------------------------------------------------------------
    # phi_dir = model_dir / "figures" / "ies" / "phi"
    # phi_dir.mkdir(parents=True, exist_ok=True)

    # # --------------------------------------------------------------
    # # 1. Phi evolution through IES iterations
    # # --------------------------------------------------------------
    # fig, ax, phi_df = plot_ies_phi_evolution(
    #     model_dir / "pecos_rw_ies.phi.actual.csv",
    #     title="PESTPP-IES Phi Evolution",
    #     logy=True,
    #     figsize=(5, 5),
    #     save_path=phi_dir / "ies_phi_evolution_actual.png",
    #     dpi=300,
    #     show=True,
    # )

    # plt.close(fig)

    # # --------------------------------------------------------------
    # # 2. Prior vs posterior phi distribution
    # # --------------------------------------------------------------
    # fig, axes, phi_data = plot_ies_phi_distribution(
    #     pst,
    #     pr_oe_file=model_dir / "pecos_rw_ies.0.obs.csv",
    #     pt_oe_file=model_dir / f"pecos_rw_ies.{4}.obs.csv",
    #     bins=20,
    #     log10=True,
    #     separate_axes=False,
    #     separate_layout="horizontal",
    #     figsize=(5, 5),
    #     title="Prior vs Posterior Phi Distribution",
    #     save_path=phi_dir / "ies_phi_distribution_prior_posterior.png",
    #     dpi=300,
    #     show=True,
    # )

    # plt.close(fig)