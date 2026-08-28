from pathlib import Path
import matplotlib.pyplot as plt
import pyemu
from ihydrocal.analyzer.pest_ies import (
    animate_fdc_ensemble_by_realization, 
    # animate_tseries_ensemble, 
    animate_tseries_ensemble_by_realization,
    plot_fdc_ensemble, 
    plot_ies_fdc_ensemble_by_group, 
    plot_ies_tseries_ensemble_by_group,
    animate_parameter_ensemble_by_realization,
    plot_parameter_ensemble,
    )
import pandas as pd

# --------------------------------------------------------------
# Change this path to your current IES master folder.
# --------------------------------------------------------------

model_dir = Path(
    # r"C:\Users\spark\Documents\projects\watersheds\pecos\calibration_v03\ihydrocal_workspace\pecos_rw_ies"
    r"/home/spark/Documents/projects/watersheds/pecos/calibration_v03/ihydrocal_workspace/pecos_rw_ies" # linux

)



# '''
pst_file = model_dir / "pecos_rw_ies.pst"

# tseries_files = plot_ies_tseries_ensemble_by_group(
#     pst_file=model_dir / "pecos_rw_ies.pst",
#     model_dir=model_dir,
#     case="pecos_rw_ies",
#     last_iter=1,
#     auto_load_ies=True,
#     out_dir=model_dir / "figures" / "tseries_monthly",
#     prefix="ies_tseries_monthly",
#     width=10,
#     height=5,
#     dot=False,
#     # aggregate_freq="MS",
#     # aggregate_func="mean",
#     auto_ylim_from_pt_fill=True,
#     ylim_pad_fraction=0.15,
#     include_obs_in_ylim=True,
#     dpi=300,
#     show=False,
# )

# anim, fig, ax = animate_tseries_ensemble_by_realization(
#     pst_file=model_dir / "pecos_rw_ies.pst",
#     model_dir=model_dir,
#     case="pecos_rw_ies",
#     last_iter=1,
#     auto_load_ies=True,
#     obgnam="cha0508",
#     aggregate_freq="MS",
#     aggregate_func="mean",
#     animate_only_posterior=True,
#     show_prior=True,
#     show_posterior=True,
#     show_observed=True,
#     max_prior_realizations=300,
#     max_posterior_realizations=300,
#     ymax=3.7,
#     fps=8,
#     pause_seconds=2.0,
#     repeat=False,
#     save_first_last_figures=True,
#     first_last_dir=model_dir / "figures" / "animations",
#     save_path=model_dir / "figures" / "animations" / "posterior_only.gif",
#     writer="pillow",
# )

# anim, fig, ax = animate_fdc_ensemble_by_realization(
#     pst_file=model_dir / "pecos_rw_ies.pst",
#     model_dir=model_dir,
#     case="pecos_rw_ies",
#     last_iter=1,
#     auto_load_ies=True,
#     obgnam="cha0508",
#     # aggregate_freq="MS",
#     # aggregate_func="mean",
#     animate_only_posterior=True,
#     show_prior=True,
#     show_posterior=True,
#     show_observed=True,
#     posterior_band=False,
#     max_prior_realizations=300,
#     max_posterior_realizations=300,
#     fps=8,
#     pause_seconds=2.0,
#     repeat=False,
#     save_first_last_figures=True,
#     save_path=model_dir / "figures" / "animations" / "cha0508_fdc_posterior_only.gif",
#     writer="pillow",
#     dpi=150,
# )


# anim, fig, axes = animate_parameter_ensemble_by_realization(
#     pst_file=model_dir / "pecos_rw_ies.pst",
#     model_dir=model_dir,
#     case="pecos_rw_ies",
#     last_iter=3,          # automatically finds largest *.par.csv iteration
#     auto_load_ies=True,
#     sel_pars=["chl", "cn2", "chk"],
#     width=10,
#     height=3,
#     ncols=3,
#     nbins=10,
#     animate_only_posterior=True,
#     show_prior=True,
#     show_posterior=True,
#     fps=20,
#     pause_seconds=2.0,
#     repeat=False,
#     save_path=model_dir / "figures" / "animations" / "parameter_ensemble_build.gif",
#     writer="pillow",
#     dpi=150,
# )


# fdc_results = plot_ies_fdc_ensemble_by_group(
#     pst_file=model_dir / "pecos_rw_ies.pst",
#     model_dir=model_dir,
#     case="pecos_rw_ies",
#     last_iter=3,
#     auto_load_ies=True,
#     out_dir=model_dir / "figures" / "fdc_monthly",
#     prefix="ies_fdc_monthly",
#     width=6,
#     height=5,
#     logy=True,
#     posterior_band=True,
#     posterior_band_quantiles=(0.05, 0.95),
#     plot_prior_lines=True,
#     plot_posterior_lines=False,
#     obs_line=False,
#     obs_dot=True,
#     # aggregate_freq="MS",
#     # aggregate_func="mean",
#     dpi=300,
#     show=False,
# )

# anim, fig, axes = animate_parameter_ensemble_by_realization(
#     pst_file=model_dir / "pecos_rw_ies.pst",
#     model_dir=model_dir,
#     case="pecos_rw_ies",
#     last_iter=4,
#     auto_load_ies=True,
#     sel_pars=["chl"],
#     width=10,
#     height=3,
#     ncols=3,
#     nbins=10,
#     show_prior=True,
#     show_posterior=True,
#     realizations_per_frame=5,   # new option
#     fps=8,
#     pause_seconds=2.0,
#     repeat=False,
#     save_path=model_d2ir / "figures" / "animations" / "parameter_ensemble_build.gif",
#     writer="pillow",
#     dpi=150,
# )

anim, fig, ax = animate_tseries_ensemble_by_realization(
    pst_file=model_dir / "pecos_rw_ies.pst",
    model_dir=model_dir,
    case="pecos_rw_ies",
    last_iter=1,
    auto_load_ies=True,
    obgnam="cha0508",
    aggregate_freq="MS",
    aggregate_func="mean",
    animate_only_posterior=True,
    # show_prior=True,
    show_posterior=True,
    show_observed=True,
    max_prior_realizations=300,
    max_posterior_realizations=300,
    ymax=3.7,
    fps=0.5,
    pause_seconds=2.0,
    realizations_per_frame=64,   # new option
    repeat=False,
    save_first_last_figures=True,
    first_last_dir=model_dir / "figures" / "animations03",
    save_path=model_dir / "figures" / "animations03" / "posterior_only_obs.gif",
    writer="pillow",
)

# model_dir = Path(
#     r"C:\Users\spark\Documents\projects\watersheds\pecos\calibration_v03\ihydrocal_workspace\pecos_rw_ies"
# )

# pst_file = model_dir / "pecos_rw_ies.pst"
# pst = pyemu.Pst(str(pst_file))

# case = "pecos_rw_ies"
# last_iter = 3

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
#         "chs", 
        
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
#     savefig=True,
#     show=True,
# )



