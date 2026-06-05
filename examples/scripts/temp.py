from pathlib import Path

import pyemu

from ihydrocal.core.config import load_config, print_config_summary
from ihydrocal.core.workspace import setup_workspace
from ihydrocal.core.pest import (
    create_morris_control_file,
    run_pestpp_sen_workers,
    )



CONFIG_FILE = Path(
    r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration_v02\config\setup_swatplus.yml"
    )

cfg = load_config(CONFIG_FILE)

workspace_dir = cfg["paths"]["workspace_dir"]
model_dir = workspace_dir / "main"

base_pst = cfg["pest"]["control_file"]

print(model_dir)
print(base_pst)



from pathlib import Path

import pyemu

model_dir = Path(
    r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration_v02\ihydrocal_workspace\pecos_rw_ies"
)

pst_file = model_dir / "pecos_rw_ies.pst"


pst = pyemu.Pst(str(pst_file))

case = "pecos_rw_ies"
last_iter = 4

pr_oe = pd.read_csv(model_dir / f"{case}.0.obs.csv", index_col=0)
pt_oe = pd.read_csv(model_dir / f"{case}.{last_iter}.obs.csv", index_col=0)


pt_fill = pd.DataFrame({
    "pt_min": pt_oe.min(axis=0),
    "pt_max": pt_oe.max(axis=0),
})

pt_fill["obgnme"] = pst.observation_data.loc[pt_fill.index, "obgnme"]

# Add parsed time from observation names
pt_fill["time"] = pd.to_datetime(pt_fill.index.str[-8:], errors="coerce")
pt_fill = pt_fill.dropna(subset=["time"]).set_index("time").sort_index()