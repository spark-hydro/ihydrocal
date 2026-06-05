import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

import numpy as np
import math
import matplotlib.dates as mdates

from matplotlib.gridspec import GridSpec
from matplotlib.patches import Rectangle
import matplotlib.gridspec as gridspec
import pyemu
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from pathlib import Path
from typing import Optional, Union


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

    It supports four main cases:

        1. Observed data only
        2. Observed data + prior ensemble
        3. Observed data + posterior ensemble
        4. Observed data + prior and posterior ensembles

    Recommended visual order
    ------------------------
    The plotting order is intentionally controlled as:

        1. Prior ensemble
        2. Posterior ensemble or posterior uncertainty band
        3. Best-estimate posterior realization, if requested
        4. Observed values

    This order keeps the observed data visible on top of the uncertainty
    information.

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

    ymin, ymax : float, optional
        Optional manual y-axis limits.

        If provided, these override auto y-axis behavior.

    auto_ylim_from_pt_fill : bool, default False
        If True, automatically set y-axis limits from the posterior
        uncertainty band.

        This is very useful when looping over many observation groups because
        prior ensemble outliers can otherwise make the posterior band hard to see.

    ylim_pad_fraction : float, default 0.10
        Fractional padding added to automatically calculated y-axis limits.

        Example:
            ylim_pad_fraction = 0.10

        adds 10% padding above and below the plotted range.

    include_obs_in_ylim : bool, default True
        If True and auto_ylim_from_pt_fill=True, observed values are also
        included when calculating automatic y-axis limits.

        This prevents observations from being clipped.

    savefig : bool, default False
        If True, save the figure as a PNG file.

    filename : str or pathlib.Path, optional
        Output filename.

        If None and savefig=True, a default filename is generated.

    dpi : int, default 300
        Resolution for saved figure.

    show : bool, default False
        If True, call plt.show().

        In IPython/Jupyter, you may prefer:

            display(fig)
            plt.close(fig)

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
    #
    # This allows direct use of:
    #
    #     pyemu.ObservationEnsemble.from_csv(...)
    #
    # or plain pandas DataFrames loaded using:
    #
    #     pd.read_csv(..., index_col=0)
    #
    # If either ensemble is None, it remains None.
    # ------------------------------------------------------------------
    pr_oe = _ensemble_to_dataframe(pr_oe, name="pr_oe")
    pt_oe = _ensemble_to_dataframe(pt_oe, name="pt_oe")

    has_prior = pr_oe is not None
    has_posterior = pt_oe is not None

    # ------------------------------------------------------------------
    # Get observation data from the PEST control file.
    #
    # We keep only observations from non-zero-weight observation groups.
    # These are the observations that actually contribute to the objective
    # function.
    # ------------------------------------------------------------------
    obs = pst.observation_data.copy()
    obs = obs.loc[obs.obgnme.isin(pst.nnz_obs_groups)].copy()

    # ------------------------------------------------------------------
    # Extract time information from observation names.
    #
    # This assumes the last 8 characters of obsnme are dates.
    #
    # Example:
    #     stf_08447300_20010515
    #                         ^^^^^^^^
    #
    # If your observation-name date format changes later, this is the
    # line to modify.
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
    # Values <= -999 are treated as missing values. This is useful because
    # many model workflows use values like -999 or -9999 as missing-data flags.
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
    # Prepare posterior uncertainty band if provided.
    #
    # pt_fill should already contain posterior min/max values by observation.
    #
    # Expected:
    #     index  : datetime-like values
    #     columns: obgnme, pt_min, pt_max
    #
    # The function filters pt_fill to the requested observation group.
    # ------------------------------------------------------------------
    if pt_fill is not None:
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
    # Prepare observed values with non-zero weight.
    #
    # These will be plotted last so they remain visible.
    # ------------------------------------------------------------------
    oobs_nonzero = oobs.loc[oobs.weight > 0].copy()

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
        #    Gray and semi-transparent so it stays in the background.
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
        # For scatter mode, we plot it as a blue line so it is easy to
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
        #    Hollow red circles are easy to see on top of ensembles.
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
        #    This stays in the background.
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
        # If df_fill is provided, plot posterior uncertainty as a band.
        # This is much cleaner than plotting all posterior lines when the
        # ensemble is large.
        #
        # If df_fill is not provided, plot all posterior realizations.
        # --------------------------------------------------------------
        if has_posterior:
            if df_fill is not None:

                # Posterior uncertainty band.
                # Use explicit numpy arrays to avoid dtype issues in
                # matplotlib.fill_between.
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

                # Plot lower edge of posterior band.
                # This makes the band visible even when the uncertainty
                # range is very narrow.
                ax.plot(
                    df_fill.index,
                    df_fill["pt_min"].to_numpy(dtype=float),
                    color="b",
                    lw=0.8,
                    alpha=0.8,
                    zorder=3,
                )

                # Plot upper edge of posterior band.
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
        #    This goes above prior/posterior ensemble but below observed.
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
        #    Plotting them last keeps observations visible.
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
    # This is useful when plotting many observation groups in a loop.
    # Otherwise, a very narrow posterior band can be hard to see because
    # the y-axis may be dominated by prior ensemble outliers.
    #
    # If include_obs_in_ylim=True, observed values are also included in
    # the y-axis range so observations are not clipped.
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
                # Avoid identical ymin/ymax.
                pad = abs(y_max_auto) * ylim_pad_fraction

                if pad == 0:
                    pad = 1.0
            else:
                pad = y_range * ylim_pad_fraction

            ymin = y_min_auto - pad
            ymax = y_max_auto + pad

    # ------------------------------------------------------------------
    # Optional y-axis limits.
    #
    # This supports:
    #     ymin only
    #     ymax only
    #     both ymin and ymax
    #
    # If auto_ylim_from_pt_fill=True, ymin/ymax may have been calculated
    # automatically above.
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
    # This is helpful because ensemble loops may create repeated labels.
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
            filename = f"tensemble_{obgnam}.png"

        fig.savefig(filename, bbox_inches="tight", dpi=dpi)

    if show:
        plt.show()

    return fig, ax



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

    This function supports:

    1. Prior only
    2. Posterior only
    3. Prior + posterior

    The function also accepts pyemu.ParameterEnsemble objects directly,
    as long as `_ensemble_to_dataframe()` is available in the same module.

    Parameters
    ----------
    pst : pyemu.Pst
        PEST control file object. Used to access pst.parameter_data.

    pr_pe : pandas.DataFrame or pyemu.ParameterEnsemble, optional
        Prior parameter ensemble. Rows are realizations and columns are parameter names.

    pt_pe : pandas.DataFrame or pyemu.ParameterEnsemble, optional
        Posterior parameter ensemble. Rows are realizations and columns are parameter names.

    sel_pars : pandas.DataFrame, list-like, or None, optional
        Selected parameters to plot.

        If DataFrame, it should contain at least:
        - parnme

        Recommended columns:
        - parnme
        - parlbnd
        - parubnd
        - offset

        If sel_pars is None, parameters are selected from the available ensemble columns
        and merged with pst.parameter_data.

    width, height : float, optional
        Figure size in inches.

    ncols : int, optional
        Number of subplot columns.

    nbins : int, optional
        Number of histogram bins.

    bestcand : str, optional
        Best candidate realization name. Used only with parobj_file.

    parobj_file : str or path-like, optional
        CSV file containing parameter values for candidate realizations.
        It should contain a "real_name" column and parameter-name columns.

    wd : str or path-like, optional
        Working directory for parobj_file if parobj_file is a relative path.

    savefig : bool, optional
        If True, save the figure.

    filename : str, optional
        Output filename. If None, "parameter_ensemble.png" is used.

    dpi : int, optional
        Resolution for saved figure.

    show : bool, optional
        If True, call plt.show() inside the function.

    Returns
    -------
    fig : matplotlib.figure.Figure
        Matplotlib figure object.

    axes : numpy.ndarray
        Array of matplotlib axes.
    """

    # ------------------------------------------------------------------
    # Convert pyemu ensemble-like objects to pandas DataFrames.
    # This allows direct use of:
    #
    # pyemu.ParameterEnsemble.from_csv(...)
    # ------------------------------------------------------------------
    pr_pe = _ensemble_to_dataframe(pr_pe, name="pr_pe")
    pt_pe = _ensemble_to_dataframe(pt_pe, name="pt_pe")

    has_prior = pr_pe is not None
    has_posterior = pt_pe is not None

    if not has_prior and not has_posterior:
        raise ValueError("At least one of pr_pe or pt_pe must be provided.")

    # ------------------------------------------------------------------
    # Prepare pst.parameter_data.
    # Some PEST/pyEMU objects store parameter names in the index, so we
    # make sure a 'parnme' column exists.
    # ------------------------------------------------------------------
    par_data = pst.parameter_data.copy()

    if "parnme" not in par_data.columns:
        par_data["parnme"] = par_data.index

    # These columns are needed to create histogram bins.
    required_cols = ["parnme", "parlbnd", "parubnd"]
    missing_cols = [col for col in required_cols if col not in par_data.columns]

    if missing_cols:
        raise KeyError(
            f"pst.parameter_data is missing required columns: {missing_cols}"
        )

    # Keep useful metadata columns if they exist.
    meta_cols = ["parnme", "parlbnd", "parubnd"]

    for optional_col in ["partrans", "parchglim", "pargp", "scale", "offset"]:
        if optional_col in par_data.columns:
            meta_cols.append(optional_col)

    par_meta = par_data[meta_cols].copy()

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
    # - None
    # - list of parameter names
    # - DataFrame such as your df_pars filtered by partrans == "log"
    # ------------------------------------------------------------------
    if sel_pars is None:
        sel_pars_df = par_meta.loc[
            par_meta["parnme"].isin(available_pars)
        ].copy()

    elif isinstance(sel_pars, pd.DataFrame):
        sel_pars_df = sel_pars.copy()

        if "parnme" not in sel_pars_df.columns:
            raise KeyError("sel_pars DataFrame must contain a 'parnme' column.")

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
        sel_pars_df = pd.DataFrame({"parnme": list(sel_pars)})
        sel_pars_df = sel_pars_df.merge(
            par_meta,
            on="parnme",
            how="left",
        )

    # ------------------------------------------------------------------
    # Keep only parameters that exist in at least one provided ensemble.
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Use parameter offsets if available.
    # If not available, assume zero offset.
    #
    # In your sel_pars table, offset already exists, so the function
    # will use it directly.
    # ------------------------------------------------------------------
    if "offset" not in sel_pars_df.columns:
        sel_pars_df["offset"] = 0.0

    sel_pars_df["offset"] = sel_pars_df["offset"].fillna(0.0)

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
            raise KeyError(
                "parobj_file must contain a 'real_name' column."
            )

        if bestcand is None:
            raise ValueError(
                "parobj_file was provided, but bestcand is None."
            )

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

        # Histogram bins are based on parameter bounds plus offset.
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
    # In notebooks, using display(fig); plt.close(fig) outside the function
    # is often cleaner.
    # ------------------------------------------------------------------
    if show:
        plt.show()

    return fig, axes


def _ensemble_to_dataframe(ensemble, name="ensemble"):
    """
    Convert a pyemu ensemble-like object or pandas DataFrame to a pandas DataFrame.

    This helper makes the plotting function safer because pyemu objects such as
    pyemu.ObservationEnsemble may behave like a dataframe but may not pass a strict
    isinstance(..., pd.DataFrame) check.
    """

    if ensemble is None:
        return None

    if isinstance(ensemble, pd.DataFrame):
        return ensemble.copy()

    if hasattr(ensemble, "_df"):
        return ensemble._df.copy()

    if hasattr(ensemble, "to_dataframe"):
        return ensemble.to_dataframe().copy()

    try:
        return pd.DataFrame(
            ensemble,
            index=ensemble.index,
            columns=ensemble.columns,
        ).copy()
    except Exception as err:
        raise TypeError(
            f"{name} must be a pandas DataFrame, pyemu ensemble-like object, or None. "
            f"Could not convert object of type {type(ensemble)} to DataFrame."
        ) from err




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

    This function is designed for streamflow ensemble diagnostics after
    PESTPP-IES.

    Main plot elements
    ------------------
    The recommended visual order is:

        1. Prior ensemble FDCs
        2. Posterior FDC uncertainty band
        3. Posterior median FDC
        4. Observed FDC

    Why posterior FDC band is different from time-series pt_fill
    ------------------------------------------------------------
    For a time-series plot, the posterior band is calculated by date:

        date -> posterior min/max simulated flow

    For a flow duration curve, the x-axis is not date. It is exceedance
    probability. Therefore, the uncertainty band must be calculated after
    sorting each realization into FDC space.

    Parameters
    ----------
    pst : pyemu.Pst, optional
        PEST control file object.

    obgnam : str
        Observation group name to plot.

    pst_file : str or pathlib.Path, optional
        PEST control file path. Used when auto_load_ies=True.

        Example:
            model_dir / "pecos_rw_ies.pst"

    model_dir : str or pathlib.Path, optional
        Folder containing PESTPP-IES output files.

    case : str, optional
        PEST++ case name. If None, inferred from pst_file stem.

    last_iter : int, optional
        Posterior iteration number.

        If None and auto_load_ies=True, the latest available iteration is used.

    auto_load_ies : bool, default False
        If True, automatically load prior and posterior observation ensembles.

        Expected files:
            case.0.obs.csv
            case.<last_iter>.obs.csv

    pr_oe : pandas.DataFrame or pyemu.ObservationEnsemble, optional
        Prior output ensemble. Rows are realizations and columns are observation names.

    pt_oe : pandas.DataFrame or pyemu.ObservationEnsemble, optional
        Posterior output ensemble.

    width, height : float
        Figure size in inches.

    logy : bool, default True
        If True, use logarithmic y-axis.

    posterior_band : bool, default True
        If True, calculate and plot posterior FDC uncertainty band.

    posterior_band_quantiles : tuple, default (0.05, 0.95)
        Lower and upper posterior quantiles for the FDC band.

        Example:
            (0.05, 0.95) gives a 5-95% interval.

    plot_prior_lines : bool, default True
        If True, plot individual prior ensemble FDCs.

    plot_posterior_lines : bool, default False
        If True, plot individual posterior ensemble FDCs.

        Usually False is cleaner when posterior_band=True.

    ymin, ymax : float, optional
        Optional y-axis limits.

    title : str, optional
        Plot title.

    savefig : bool, default False
        If True, save figure.

    filename : str or pathlib.Path, optional
        Output filename.

    dpi : int, default 300
        Save resolution.

    show : bool, default False
        If True, call plt.show().

    Returns
    -------
    fig, ax, fdc_data
        Matplotlib figure, axis, and dictionary containing FDC data.
    """

    # ------------------------------------------------------------------
    # Optional automatic loading for PESTPP-IES output files.
    #
    # This allows a simple call:
    #
    #     plot_fdc_ensemble(
    #         pst_file=model_dir / "pecos_rw_ies.pst",
    #         obgnam="stf_08447300",
    #         auto_load_ies=True,
    #     )
    #
    # This relies on load_ies_observation_ensembles(), which should already
    # exist in pest_ies.py.
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
    # Select requested observation group.
    # ------------------------------------------------------------------
    oobs = obs.loc[obs.obgnme == obgnam].copy()

    if oobs.empty:
        raise ValueError(f"No observations found for observation group: {obgnam}")

    # Observation names are used to select matching ensemble columns.
    onames = oobs.obsnme.to_numpy()

    # ------------------------------------------------------------------
    # Prepare observed values.
    # Use only non-zero-weight observations.
    # ------------------------------------------------------------------
    oobs_nonzero = oobs.loc[oobs.weight > 0].copy()

    obs_values = pd.to_numeric(oobs_nonzero.obsval, errors="coerce")
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
    # Helper function to calculate one FDC.
    #
    # Exceedance probability:
    #     P = rank / (n + 1) * 100
    #
    # Larger flows are assigned smaller exceedance probabilities.
    # ------------------------------------------------------------------
    def _calculate_fdc(values):
        values = pd.Series(values).dropna()
        values = pd.to_numeric(values, errors="coerce").dropna()
        values = values.loc[values > -999]

        if logy:
            # Log y-axis cannot show zero or negative flow.
            values = values.loc[values > 0]

        if values.empty:
            return None, None

        sorted_values = np.sort(values.to_numpy(dtype=float))[::-1]
        n = len(sorted_values)

        exceedance = np.arange(1, n + 1) / (n + 1) * 100.0

        return exceedance, sorted_values

    # ------------------------------------------------------------------
    # Helper function to calculate posterior FDC band.
    #
    # Steps:
    #   1. Calculate FDC for each posterior realization.
    #   2. Stack all sorted FDC values into an array.
    #   3. Calculate quantiles across realizations at each exceedance rank.
    #
    # This assumes each realization has the same number of valid flow values,
    # which is normally true because all realizations share the same observation
    # columns. If some realizations have missing values, they are skipped if
    # their FDC length differs from the first valid realization.
    # ------------------------------------------------------------------
    def _calculate_fdc_band(ensemble_df, obs_names, quantiles=(0.05, 0.95)):
        fdc_arrays = []
        exceedance_ref = None
        expected_length = None

        for realization in ensemble_df.index:
            x, y = _calculate_fdc(ensemble_df.loc[realization, obs_names])

            if x is None:
                continue

            if expected_length is None:
                expected_length = len(y)
                exceedance_ref = x

            # Skip inconsistent realization lengths.
            # This prevents array-shape errors when missing values differ.
            if len(y) != expected_length:
                continue

            fdc_arrays.append(y)

        if not fdc_arrays:
            return None

        fdc_matrix = np.vstack(fdc_arrays)

        q_low, q_high = quantiles

        fdc_low = np.nanquantile(fdc_matrix, q_low, axis=0)
        fdc_high = np.nanquantile(fdc_matrix, q_high, axis=0)
        fdc_median = np.nanmedian(fdc_matrix, axis=0)

        return {
            "exceedance": exceedance_ref,
            "low": fdc_low,
            "high": fdc_high,
            "median": fdc_median,
            "matrix": fdc_matrix,
        }

    # ------------------------------------------------------------------
    # Create figure.
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(width, height))

    fdc_data = {}

    # ------------------------------------------------------------------
    # 1. Prior ensemble FDCs.
    # Plot first so they stay in the background.
    # ------------------------------------------------------------------
    if has_prior and plot_prior_lines:
        for idx, realization in enumerate(pr_oe.index):
            x, y = _calculate_fdc(pr_oe.loc[realization, onames])

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
    # 2. Posterior ensemble FDC band.
    #
    # This is the FDC-space uncertainty band, not date-based pt_fill.
    # ------------------------------------------------------------------
    if has_posterior and posterior_band:
        pt_band = _calculate_fdc_band(
            pt_oe,
            onames,
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
    #
    # Usually leave this False if posterior_band=True.
    # ------------------------------------------------------------------
    if has_posterior and plot_posterior_lines:
        for idx, realization in enumerate(pt_oe.index):
            x, y = _calculate_fdc(pt_oe.loc[realization, onames])

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
    # Plot last and thicker so it is clearly visible.
    # ------------------------------------------------------------------
    x_obs, y_obs = _calculate_fdc(obs_values)

    if x_obs is None:
        raise ValueError(f"Could not calculate observed FDC for group: {obgnam}")

    fdc_data["observed"] = {
        "exceedance": x_obs,
        "flow": y_obs,
    }

    # ------------------------------------------------------------------
    # 4. Observed FDC.
    #
    # The observed FDC is plotted last so it stays visible above the
    # prior/posterior ensemble information.
    #
    # Options:
    #   obs_line=True, obs_dot=False
    #       -> red observed line only
    #
    #   obs_line=False, obs_dot=True
    #       -> red hollow observed dots only
    #
    #   obs_line=True, obs_dot=True
    #       -> red line with hollow observed dots
    # ------------------------------------------------------------------
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
    ax.set_ylabel("Flow")
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

    ax.set_title(title or f"Flow Duration Curve: {obgnam}")

    fig.tight_layout()

    if savefig:
        if filename is None:
            filename = f"fdc_ensemble_{obgnam}.png"

        fig.savefig(filename, bbox_inches="tight", dpi=dpi)

    if show:
        plt.show()

    return fig, ax, fdc_data


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
