from pathlib import Path
import numpy as np
import pandas as pd
import pyemu
import matplotlib.pyplot as plt

def create_demo_well_calibrated_obs_ensemble(
    posterior_obs_file,
    obs_data_file,
    output_file,
    *,
    spread_fraction=0.75,
    min_spread=0.10,
    random_sigma=0.25,
    random_seed=20260605,
    keep_nonnegative=True,
):
    """
    Create a synthetic/demo posterior observation ensemble that covers observations.

    This is useful only for visualization or future/well-calibrated-looking
    demonstration figures. It should not be used as real calibration output.

    Parameters
    ----------
    posterior_obs_file : str or Path
        Existing PESTPP-IES posterior observation ensemble file.

        Example:
            pecos_rw_ies.4.obs.csv

    obs_data_file : str or Path
        PEST observation data file containing observed values.

        Example:
            pecos_rw_ies.obs_data.csv

    output_file : str or Path
        Output modified posterior observation ensemble file.

    spread_fraction : float, default 0.75
        Controls the band width relative to the observed value.

        Example:
            spread_fraction=0.25 gives approximately ±25%
            spread_fraction=0.75 gives approximately ±75%
            spread_fraction=1.00 gives approximately ±100%

    min_spread : float, default 0.10
        Minimum absolute spread added to every observation.

        This is important when observed values are small or zero.

    random_sigma : float, default 0.25
        Standard deviation of random perturbation around observed values.

        Larger value creates a wider and noisier ensemble cloud.

    random_seed : int, default 20260605
        Random seed for reproducibility.

    keep_nonnegative : bool, default True
        If True, negative values are forced to zero.

        This is recommended for streamflow.

    Returns
    -------
    pandas.DataFrame
        Modified posterior observation ensemble.
    """

    posterior_obs_file = Path(posterior_obs_file)
    obs_data_file = Path(obs_data_file)
    output_file = Path(output_file)

    # --------------------------------------------------------------
    # Read files.
    # --------------------------------------------------------------
    post = pd.read_csv(posterior_obs_file, low_memory=False)
    obs_data = pd.read_csv(obs_data_file, low_memory=False)

    # First column is usually realization name.
    real_col = post.columns[0]
    obs_cols = list(post.columns[1:])

    # --------------------------------------------------------------
    # Build observed-value lookup.
    # Expected columns in obs_data:
    #     obsnme, obsval
    # --------------------------------------------------------------
    obs_lookup = obs_data.set_index("obsnme")["obsval"]

    missing = [c for c in obs_cols if c not in obs_lookup.index]
    if missing:
        raise KeyError(
            f"{len(missing)} observation columns were not found in obs_data. "
            f"Example missing column: {missing[0]}"
        )

    obs_values = obs_lookup.loc[obs_cols].to_numpy(dtype=float)

    nreal = len(post)
    nobs = len(obs_cols)

    rng = np.random.default_rng(random_seed)

    # --------------------------------------------------------------
    # Define spread around observed values.
    #
    # For each observed value:
    #     spread = abs(obs) * spread_fraction + min_spread
    #
    # This means high flows get wider bands, while zero/small flows still
    # get some visible uncertainty.
    # --------------------------------------------------------------
    spread = np.abs(obs_values) * spread_fraction + min_spread

    lower = obs_values - spread
    upper = obs_values + spread

    # --------------------------------------------------------------
    # Create new synthetic posterior ensemble.
    #
    # First few rows are designed intentionally:
    #     row 0 = lower envelope
    #     row 1 = upper envelope
    #     row 2 = observed value
    #
    # Remaining rows are random values around observation.
    # --------------------------------------------------------------
    new_vals = np.empty((nreal, nobs), dtype=np.float32)

    if nreal >= 1:
        new_vals[0, :] = lower

    if nreal >= 2:
        new_vals[1, :] = upper

    if nreal >= 3:
        new_vals[2, :] = obs_values

    if nreal > 3:
        random_noise = rng.normal(
            loc=0.0,
            scale=random_sigma,
            size=(nreal - 3, nobs),
        )

        # Random values around obs_values.
        # Example:
        #     obs + random_noise * spread
        new_vals[3:, :] = obs_values + random_noise * spread

        # Clip random values to the deterministic lower/upper range.
        # This keeps the synthetic ensemble controlled.
        new_vals[3:, :] = np.clip(new_vals[3:, :], lower, upper)

    if keep_nonnegative:
        new_vals = np.maximum(new_vals, 0.0)

    # --------------------------------------------------------------
    # Save output with same structure as original posterior ensemble.
    # --------------------------------------------------------------
    out = pd.DataFrame(new_vals, columns=obs_cols)
    out.insert(0, real_col, post[real_col].values)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_file, index=False, float_format="%.6g")

    print(f"Saved modified posterior ensemble:")
    print(output_file)
    print(f"Shape: {out.shape}")
    print(f"spread_fraction={spread_fraction}, min_spread={min_spread}, random_sigma={random_sigma}")

    return out



if __name__ == "__main__":

    from ihydrocal.analyzer.pest_ies import build_posterior_fill, plot_tseries_ensemble, plot_fdc_ensemble

    model_dir = Path(
        r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration_v02\ihydrocal_workspace\pecos_rw_ies"
    )

    out = create_demo_well_calibrated_obs_ensemble(
        posterior_obs_file=model_dir / "pecos_rw_ies.4.obs.csv",
        obs_data_file=model_dir / "pecos_rw_ies.obs_data.csv",
        output_file=model_dir / "pecos_rw_ies.4.obs_demo_wide.csv",
        spread_fraction=0.35,   # try 0.75, 1.00, 1.50
        min_spread=0.05,        # helps widen low/zero flows
        random_sigma=0.15,      # larger = wider/noisier cloud
    )
    pst_file = model_dir / "pecos_rw_ies.pst"

    obgnam = "cha0015"
    pst = pyemu.Pst(str(pst_file))

    pr_oe = pd.read_csv(model_dir / "pecos_rw_ies.0.obs.csv", index_col=0)
    pt_oe = pd.read_csv(model_dir / "pecos_rw_ies.4.obs_demo_wide.csv", index_col=0)

    pt_fill = build_posterior_fill(
        pt_oe,
        pst=pst,
    )

    fig, ax = plot_tseries_ensemble(
        pst,
        obgnam=obgnam,
        pr_oe=pr_oe,
        pt_oe=pt_oe,
        pt_fill=pt_fill,
        auto_ylim_from_pt_fill=True,
        show=True,
    )

    # '''
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
                width=11,
                height=4,
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



