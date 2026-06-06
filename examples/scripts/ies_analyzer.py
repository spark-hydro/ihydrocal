from pathlib import Path
import matplotlib.pyplot as plt
from ihydrocal.analyzer.pest_ies import plot_ies_tseries_ensemble_by_group

# --------------------------------------------------------------
# Change this path to your current IES master folder.
# --------------------------------------------------------------

model_dir = Path(
    r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration_v02\ihydrocal_workspace\pecos_rw_ies"
)

# '''
pst_file = model_dir / "pecos_rw_ies.pst"

tseries_files = plot_ies_tseries_ensemble_by_group(
    pst_file=model_dir / "pecos_rw_ies.pst",
    model_dir=model_dir,
    case="pecos_rw_ies",
    last_iter=4,
    auto_load_ies=True,
    out_dir=model_dir / "figures02" / "tseries_monthly",
    prefix="ies_tseries_monthly",
    width=11,
    height=4,
    dot=False,
    aggregate_freq="MS",
    aggregate_func="mean",
    auto_ylim_from_pt_fill=True,
    ylim_pad_fraction=0.15,
    include_obs_in_ylim=True,
    dpi=300,
    show=False,
)