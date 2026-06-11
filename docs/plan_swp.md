# Implementation Plan: `pestpp-swp` Release-Water Scenario Sweep for iHydroCal

**Goal:** Add a working `pestpp-swp` workflow to iHydroCal for SWAT+ release-water scenario sweeps, using the current project structure and minimizing disruption to existing GLM/IES/SEN workflows.

---

## 1. Design decision

### 1.1 What `pestpp-swp` should do here

`pestpp-swp` should be used as a **parallel scenario-sweep engine**. It will not calibrate or optimize. It will run many release scenarios and collect summary outputs.

For the first implementation, each row of `sweep_in.csv` will represent one release-water scenario. Example:

```csv
real_name,rel_0447_low,rel_0281_low
scenario_000,0.0,0.0
scenario_001,1.0,0.0
scenario_002,2.0,0.0
scenario_003,0.0,1.0
scenario_004,0.0,2.0
```

Each release parameter is written by PEST++ into a release schedule file using a PEST template.

### 1.2 Recommended first implementation approach

Use a **post-processing release layer** first:

```text
run SWAT+ baseline
    ↓
extract channel flow
    ↓
read release_schedule.csv
    ↓
add release to selected channel/date rows
    ↓
calculate SWP metrics/constraints
    ↓
write swp_outputs.dat
```

This is simpler and safer than immediately editing real SWAT+ reservoir/recall/point-source files.

### 1.3 Trade-off

| Approach | Advantage | Disadvantage | Recommendation |
|---|---|---|---|
| Post-processing release | Fast, safe, easy to debug, fits current code | Does not physically route release through downstream SWAT+ network | Use first |
| SWAT+ input-side release | Physically more correct | Needs exact SWAT+ file mechanism and more error-prone templates | Add later |
| `pestpp-opt` / `pestpp-mou` | True optimization | More setup and constraints/objectives required | Use after SWP works |

---

## 2. Files to add or modify

### 2.1 Add new source file

Add:

```text
src/ihydrocal/models/swatplus_gwflow/releases.py
```

Purpose:

- create release template files,
- create default sweep input files,
- apply release schedules to extracted channel flow,
- calculate SWP summary outputs,
- write SWP output instruction files.

### 2.2 Modify existing source file

Modify:

```text
src/ihydrocal/core/pest.py
```

Add:

- `create_swp_control_file()`
- `run_pestpp_swp_workers()`
- optionally `rank_swp_results()`

This matches the current pattern for IES and SEN in the same file.

### 2.3 Modify package exports

Modify:

```text
src/ihydrocal/models/swatplus_gwflow/__init__.py
```

Add exports for release helper functions if desired.

Potentially modify:

```text
src/ihydrocal/core/__init__.py
```

only if we want top-level imports from `ihydrocal.core`.

### 2.4 Add new forward run script

Add:

```text
config/forward_run_swp.py
```

Purpose: keep SWP scenario runs separate from the current calibration `forward_run.py`.

### 2.5 Modify config template

Modify:

```text
config/setup_swatplus.yml
```

Add:

- missing `outputs:` section,
- new `scenario:` or `swp:` section,
- `pestpp-swp` in `binaries.files`.

### 2.6 Add example script

Add:

```text
examples/scripts/04_run_swp.py
```

Purpose: provide a copy-paste workflow similar to the existing `all_workflows.py` and `temp.py` patterns.

### 2.7 Optional future analyzer

Later, add:

```text
src/ihydrocal/analyzer/pest_swp.py
```

Purpose: plot/rank `sweep_out.csv` results.

This can wait until the run workflow is stable.

---

## 3. Required config changes

### 3.1 Add missing outputs section

The current `forward_run.py` expects `cfg["outputs"]["swatplus"]["channel"]`, but the provided YAML does not include this. Add:

```yaml
outputs:
  swatplus:
    channel:
      file: channel_sd_day.txt       # or channel_sdmorph_day.txt
      id_col: gis_id
      variables:
        - flo_out
      cha_ids:
        - 281
        - 447
```

For your Pecos application, replace `281` and `447` with the relevant release and downstream evaluation channels.

### 3.2 Add SWP section

Add:

```yaml
swp:
  control_file: pestpp_swp.pst
  model_command: python forward_run_swp.py
  sweep_parameter_csv_file: sweep_in.csv
  sweep_output_csv_file: sweep_out.csv

  release:
    schedule_file: release_schedule.csv
    template_file: release_schedule.csv.tpl
    units: cms
    date_col: date
    channel_col: channel_id
    release_col: release_cms

    # The first implementation uses post-processing.
    application_method: postprocess

    # Simple low-flow-season example.
    decision_variables:
      - name: rel_0447_low
        channel_id: 447
        start_date: "2003-01-01"
        end_date: "2005-12-31"
        value: 0.0
        lower_bound: 0.0
        upper_bound: 20.0
        pargp: release

      - name: rel_0281_low
        channel_id: 281
        start_date: "2003-01-01"
        end_date: "2005-12-31"
        value: 0.0
        lower_bound: 0.0
        upper_bound: 20.0
        pargp: release

  objectives:
    evaluation_channel_id: 447
    min_flow_cms: 5.0
    max_flow_cms: 100.0
    start_date: "2003-01-01"
    end_date: "2005-12-31"
```

### 3.3 Add SWP binary

Modify:

```yaml
binaries:
  files:
    - swatplus
    - pestpp-glm
    - pestpp-ies
    - pestpp-opt
    - pestpp-sen
    - pestpp-swp
```

Also add the actual executable:

```text
bin/windows/pestpp-swp.exe
```

or make sure `pestpp-swp` is on your system `PATH` and skip copying.

---

## 4. New file: `src/ihydrocal/models/swatplus_gwflow/releases.py`

### 4.1 Purpose

This module should contain SWAT+ release-scenario utilities. It should not depend directly on PEST++ execution. It should only prepare files and process model outputs.

### 4.2 Proposed implementation

```python
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


def read_release_decision_variables(cfg: dict) -> pd.DataFrame:
    """
    Read release decision variables from cfg['swp']['release']['decision_variables'].
    """
    try:
        records = cfg["swp"]["release"]["decision_variables"]
    except KeyError as err:
        raise KeyError(
            "Missing cfg['swp']['release']['decision_variables']. "
            "Add an swp.release.decision_variables section to setup_swatplus.yml."
        ) from err

    df = pd.DataFrame(records)

    required = [
        "name",
        "channel_id",
        "start_date",
        "end_date",
        "value",
        "lower_bound",
        "upper_bound",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(
            f"Missing release decision-variable column(s): {missing}. "
            f"Available columns: {list(df.columns)}"
        )

    df["name"] = df["name"].astype(str).str.strip().str.lower()
    df["channel_id"] = pd.to_numeric(df["channel_id"], errors="raise").astype(int)
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])

    for col in ["value", "lower_bound", "upper_bound"]:
        df[col] = pd.to_numeric(df[col], errors="raise")

    if "pargp" not in df.columns:
        df["pargp"] = "release"

    if df["name"].duplicated().any():
        dupes = df.loc[df["name"].duplicated(), "name"].tolist()
        raise ValueError(f"Duplicate release parameter names: {dupes}")

    bad_bounds = df["lower_bound"] > df["upper_bound"]
    if bad_bounds.any():
        raise ValueError("Release lower_bound cannot exceed upper_bound.")

    return df
```

### 4.3 Write release schedule template

The release template should create a daily or period-based release schedule. For first implementation, period-based is easier:

```csv
parameter_name,channel_id,start_date,end_date,release_cms
rel_0447_low,447,2003-01-01,2005-12-31,~ rel_0447_low ~
```

Function:

```python
def write_release_schedule_template(
    release_vars: pd.DataFrame,
    tpl_file: str | Path,
    schedule_file: str | Path | None = None,
    release_col: str = "release_cms",
) -> tuple[Path, Path]:
    """
    Write a PEST template file for release decision variables.
    """
    tpl_file = Path(tpl_file)
    tpl_file.parent.mkdir(parents=True, exist_ok=True)

    if schedule_file is None:
        if tpl_file.name.endswith(".tpl"):
            schedule_file = tpl_file.with_suffix("")
        else:
            schedule_file = tpl_file.with_suffix(".csv")
    schedule_file = Path(schedule_file)

    lines = ["ptf ~"]
    lines.append("parameter_name,channel_id,start_date,end_date," + release_col)

    for _, row in release_vars.iterrows():
        par = str(row["name"]).strip().lower()
        line = (
            f"{par},"
            f"{int(row['channel_id'])},"
            f"{pd.to_datetime(row['start_date']).date()},"
            f"{pd.to_datetime(row['end_date']).date()},"
            f"~ {par} ~"
        )
        lines.append(line)

    tpl_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Write a non-template initial schedule too. This is useful for tests.
    initial = release_vars[["name", "channel_id", "start_date", "end_date", "value"]].copy()
    initial = initial.rename(columns={"name": "parameter_name", "value": release_col})
    initial.to_csv(schedule_file, index=False)

    return tpl_file, schedule_file
```

### 4.4 Expand release schedule to daily rows

```python
def expand_release_schedule(
    release_schedule_file: str | Path,
    date_col: str = "date",
    release_col: str = "release_cms",
) -> pd.DataFrame:
    """
    Convert period-based release_schedule.csv to daily rows.
    """
    release_schedule_file = Path(release_schedule_file)
    if not release_schedule_file.exists():
        raise FileNotFoundError(f"Release schedule file not found: {release_schedule_file}")

    sched = pd.read_csv(release_schedule_file)

    required = ["channel_id", "start_date", "end_date", release_col]
    missing = [c for c in required if c not in sched.columns]
    if missing:
        raise KeyError(
            f"Missing required release schedule column(s): {missing}. "
            f"Available columns: {list(sched.columns)}"
        )

    rows = []
    for _, row in sched.iterrows():
        dates = pd.date_range(row["start_date"], row["end_date"], freq="D")
        tmp = pd.DataFrame(
            {
                date_col: dates,
                "channel_id": int(row["channel_id"]),
                release_col: float(row[release_col]),
            }
        )
        rows.append(tmp)

    if not rows:
        return pd.DataFrame(columns=[date_col, "channel_id", release_col])

    out = pd.concat(rows, ignore_index=True)
    out = out.groupby([date_col, "channel_id"], as_index=False)[release_col].sum()
    return out
```

### 4.5 Apply release to extracted channel output

```python
def apply_release_to_channel_output(
    sim_file: str | Path,
    release_schedule_file: str | Path,
    output_file: str | Path,
    date_col: str = "date",
    channel_col: str = "channel_id",
    sim_col: str = "simulated",
    release_col: str = "release_cms",
    adjusted_col: str = "simulated_with_release",
    keep_nonnegative: bool = True,
) -> Path:
    """
    Add release values to extracted SWAT+ channel output.
    """
    sim_file = Path(sim_file)
    output_file = Path(output_file)

    if not sim_file.exists():
        raise FileNotFoundError(f"Simulation file not found: {sim_file}")

    sim = pd.read_csv(sim_file, parse_dates=[date_col])
    required_sim = [date_col, channel_col, sim_col]
    missing = [c for c in required_sim if c not in sim.columns]
    if missing:
        raise KeyError(
            f"Missing simulation column(s): {missing}. "
            f"Available columns: {list(sim.columns)}"
        )

    rel = expand_release_schedule(
        release_schedule_file=release_schedule_file,
        date_col=date_col,
        release_col=release_col,
    )

    sim[channel_col] = sim[channel_col].astype(int)
    rel[channel_col] = rel[channel_col].astype(int)

    merged = sim.merge(rel, on=[date_col, channel_col], how="left")
    merged[release_col] = merged[release_col].fillna(0.0)
    merged[adjusted_col] = merged[sim_col].astype(float) + merged[release_col].astype(float)

    if keep_nonnegative:
        merged[adjusted_col] = merged[adjusted_col].clip(lower=0.0)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_file, index=False)
    return output_file
```

### 4.6 Calculate SWP summary outputs

```python
def calculate_swp_summary_outputs(
    adjusted_file: str | Path,
    output_dat: str | Path,
    evaluation_channel_id: int,
    min_flow_cms: float | None = None,
    max_flow_cms: float | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    date_col: str = "date",
    channel_col: str = "channel_id",
    flow_col: str = "simulated_with_release",
    release_col: str = "release_cms",
) -> Path:
    """
    Write stable SWP outputs for pestpp-swp collection.
    """
    adjusted_file = Path(adjusted_file)
    output_dat = Path(output_dat)

    df = pd.read_csv(adjusted_file, parse_dates=[date_col])
    df[channel_col] = df[channel_col].astype(int)

    site = df[df[channel_col] == int(evaluation_channel_id)].copy()

    if start_date is not None:
        site = site[site[date_col] >= pd.to_datetime(start_date)]
    if end_date is not None:
        site = site[site[date_col] <= pd.to_datetime(end_date)]

    if site.empty:
        raise ValueError(
            f"No rows found for evaluation_channel_id={evaluation_channel_id} "
            f"in {adjusted_file}."
        )

    min_flow = float(site[flow_col].min())
    max_flow = float(site[flow_col].max())
    mean_flow = float(site[flow_col].mean())

    low_flow_deficit = 0.0
    if min_flow_cms is not None:
        low_flow_deficit = max(0.0, float(min_flow_cms) - min_flow)

    high_flow_excess = 0.0
    if max_flow_cms is not None:
        high_flow_excess = max(0.0, max_flow - float(max_flow_cms))

    total_release = float(df[release_col].sum()) if release_col in df.columns else 0.0

    out = pd.DataFrame(
        {
            "obsnme": [
                "min_flow",
                "max_flow",
                "mean_flow",
                "low_flow_deficit",
                "high_flow_excess",
                "total_release",
            ],
            "obsval": [
                min_flow,
                max_flow,
                mean_flow,
                low_flow_deficit,
                high_flow_excess,
                total_release,
            ],
        }
    )

    output_dat.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_dat, sep=" ", index=False)
    return output_dat
```

### 4.7 Write SWP instruction file

```python
def write_swp_output_instruction_file(
    output_dat: str | Path,
    ins_file: str | Path | None = None,
) -> Path:
    """
    Write instruction file for swp_outputs.dat.
    """
    output_dat = Path(output_dat)
    if ins_file is None:
        ins_file = output_dat.with_suffix(output_dat.suffix + ".ins")
    else:
        ins_file = Path(ins_file)

    df = pd.read_csv(output_dat, sep=r"\s+")
    if "obsnme" not in df.columns:
        raise KeyError(f"obsnme column not found in {output_dat}")

    lines = ["pif ~", "l1"]
    for obsname in df["obsnme"]:
        lines.append(f"l1 w !{obsname}!")

    ins_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ins_file
```

---

## 5. Modify `src/ihydrocal/core/pest.py`

Add functions near the existing IES/SEN helpers.

### 5.1 Create SWP control file

```python
def create_swp_control_file(
    model_dir: str | Path,
    base_pst_file: str | Path | None = None,
    swp_pst_file: str | Path = "pestpp_swp.pst",
    sweep_parameter_csv_file: str = "sweep_in.csv",
    sweep_output_csv_file: str = "sweep_out.csv",
    model_command: str = "python forward_run_swp.py",
    noptmax: int = 0,
) -> Path:
    """
    Create a PESTPP-SWP control file.

    If base_pst_file is provided, start from that control file.
    Otherwise parse template/instruction files in model_dir.
    """
    model_dir = Path(model_dir).resolve()

    swp_pst_file = Path(swp_pst_file)
    if not swp_pst_file.is_absolute():
        swp_pst_file = model_dir / swp_pst_file

    if base_pst_file is None:
        old_cwd = Path.cwd()
        try:
            os.chdir(model_dir)
            io_files = pyemu.helpers.parse_dir_for_io_files(".")
            pst = pyemu.Pst.from_io_files(*io_files)
        finally:
            os.chdir(old_cwd)
    else:
        base_pst_file = Path(base_pst_file)
        if not base_pst_file.is_absolute():
            base_pst_file = model_dir / base_pst_file
        if not base_pst_file.exists():
            raise FileNotFoundError(f"Base PEST control file not found: {base_pst_file}")
        pst = pyemu.Pst(str(base_pst_file))

    pst.model_command = [model_command]
    pst.control_data.noptmax = noptmax

    pst.pestpp_options["sweep_parameter_csv_file"] = sweep_parameter_csv_file
    pst.pestpp_options["sweep_output_csv_file"] = sweep_output_csv_file

    # Release decision variables should be direct non-log parameters.
    par = pst.parameter_data
    if par is not None:
        rel_mask = par.index.astype(str).str.startswith("rel_")
        par.loc[rel_mask, "partrans"] = "none"
        par.loc[rel_mask, "parchglim"] = "relative"
        par.loc[rel_mask, "pargp"] = "release"
        pst.parameter_data = par

    pst.write(str(swp_pst_file), version=2)
    print(f"Created SWP control file: {swp_pst_file}")
    return swp_pst_file
```

### 5.2 Run SWP with workers

```python
def run_pestpp_swp_workers(
    model_dir: str | Path,
    swp_pst_file: str | Path,
    master_dir: str | Path,
    num_workers: int | None = None,
    worker_root: str | Path | None = None,
    pestpp_exe: str = "pestpp-swp",
    reuse_master: bool = False,
) -> None:
    """
    Run PESTPP-SWP in parallel using pyEMU workers.
    """
    model_dir = Path(model_dir).resolve()
    swp_pst_file = Path(swp_pst_file).name
    master_dir = Path(master_dir).resolve()

    if worker_root is None:
        worker_root = model_dir.parent
    else:
        worker_root = Path(worker_root).resolve()

    if num_workers is None:
        num_workers = psutil.cpu_count(logical=False) or 1

    print(f"Starting PESTPP-SWP with {num_workers} workers")
    print(f"Template directory: {model_dir}")
    print(f"Worker root       : {worker_root}")
    print(f"Master directory  : {master_dir}")

    pyemu.os_utils.start_workers(
        str(model_dir),
        pestpp_exe,
        swp_pst_file,
        num_workers=num_workers,
        worker_root=str(worker_root),
        master_dir=str(master_dir),
        reuse_master=reuse_master,
    )
```

### 5.3 Rank SWP results

```python
def rank_swp_results(
    sweep_output_csv: str | Path,
    low_flow_col: str = "low_flow_deficit",
    high_flow_col: str = "high_flow_excess",
    release_col: str = "total_release",
    low_flow_weight: float = 1000.0,
    high_flow_weight: float = 1000.0,
    release_weight: float = 1.0,
) -> pd.DataFrame:
    """
    Rank SWP scenarios with a simple penalty score.
    """
    sweep_output_csv = Path(sweep_output_csv)
    if not sweep_output_csv.exists():
        raise FileNotFoundError(f"SWP output file not found: {sweep_output_csv}")

    df = pd.read_csv(sweep_output_csv)

    required = [low_flow_col, high_flow_col, release_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(
            f"Missing required SWP result column(s): {missing}. "
            f"Available columns: {list(df.columns)}"
        )

    df = df.copy()
    df["swp_score"] = (
        low_flow_weight * df[low_flow_col].astype(float)
        + high_flow_weight * df[high_flow_col].astype(float)
        + release_weight * df[release_col].astype(float)
    )

    return df.sort_values("swp_score").reset_index(drop=True)
```

---

## 6. Add `config/forward_run_swp.py`

This script should be copied into `workspace_dir/main` before running SWP.

```python
from pathlib import Path
import platform
import subprocess
import sys

from ihydrocal.core.config import load_config
from ihydrocal.models.swatplus_gwflow.outputs import extract_swatplus_channel_output_long
from ihydrocal.models.swatplus_gwflow.releases import (
    apply_release_to_channel_output,
    calculate_swp_summary_outputs,
)


def get_swat_executable(model_dir: Path, exe_name: str = "swatplus") -> Path:
    system = platform.system().lower()
    exe_name = Path(exe_name).name

    if system == "windows" and not exe_name.endswith(".exe"):
        exe_name = f"{exe_name}.exe"

    exe_path = model_dir / exe_name
    if not exe_path.exists():
        raise FileNotFoundError(f"SWAT+ executable not found: {exe_path}")
    return exe_path


def run_swatplus(model_dir: Path, exe_path: Path) -> None:
    result = subprocess.run(
        [str(exe_path)],
        cwd=model_dir,
        capture_output=True,
        text=True,
    )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"SWAT+ failed with return code {result.returncode}")


def main():
    model_dir = Path(__file__).resolve().parent
    config_file = model_dir.parents[1] / "config" / "setup_swatplus.yml"

    cfg = load_config(config_file)

    channel_cfg = cfg["outputs"]["swatplus"]["channel"]
    swp_cfg = cfg["swp"]
    rel_cfg = swp_cfg["release"]
    obj_cfg = swp_cfg["objectives"]

    swat_exe_name = Path(cfg["paths"].get("swat_exe", "swatplus")).name
    exe_path = get_swat_executable(model_dir, swat_exe_name)

    # 1. Run SWAT+ baseline for this worker/scenario.
    run_swatplus(model_dir, exe_path)

    # 2. Extract selected channel output.
    swat_output_file = model_dir / channel_cfg["file"]
    sim_channel_file = model_dir / "cha_flo_out_day.csv"

    extract_swatplus_channel_output_long(
        output_file=swat_output_file,
        output_csv=sim_channel_file,
        value_col=channel_cfg["variables"][0],
        cha_ids=channel_cfg["cha_ids"],
        id_col=channel_cfg["id_col"],
    )

    # 3. Apply release schedule generated by PEST++.
    adjusted_file = model_dir / "cha_flo_out_day_with_release.csv"
    apply_release_to_channel_output(
        sim_file=sim_channel_file,
        release_schedule_file=model_dir / rel_cfg.get("schedule_file", "release_schedule.csv"),
        output_file=adjusted_file,
        release_col=rel_cfg.get("release_col", "release_cms"),
    )

    # 4. Calculate summary outputs for pestpp-swp.
    calculate_swp_summary_outputs(
        adjusted_file=adjusted_file,
        output_dat=model_dir / "swp_outputs.dat",
        evaluation_channel_id=obj_cfg["evaluation_channel_id"],
        min_flow_cms=obj_cfg.get("min_flow_cms"),
        max_flow_cms=obj_cfg.get("max_flow_cms"),
        start_date=obj_cfg.get("start_date"),
        end_date=obj_cfg.get("end_date"),
    )

    print("SWP forward run completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"SWP forward run failed: {err}", file=sys.stderr)
        raise
```

---

## 7. Add `examples/scripts/04_run_swp.py`

This script should prepare and run the SWP workflow.

```python
from pathlib import Path
import shutil

from ihydrocal.core.config import load_config
from ihydrocal.core.workspace import setup_workspace
from ihydrocal.core.pest import create_swp_control_file, run_pestpp_swp_workers, rank_swp_results
from ihydrocal.models.swatplus_gwflow.releases import (
    read_release_decision_variables,
    write_release_schedule_template,
    calculate_swp_summary_outputs,
    write_swp_output_instruction_file,
)


CONFIG_FILE = Path(
    r"C:/Users/seonggpa/Documents/projects/watersheds/Pecos/Analysis/calibration/config/setup_swatplus.yml"
)


def make_sweep_file(release_vars, output_csv):
    """
    Simple first version: use lower, midpoint, and upper for each release variable.
    """
    import itertools
    import pandas as pd

    names = release_vars["name"].tolist()
    levels = []
    for _, row in release_vars.iterrows():
        low = float(row["lower_bound"])
        high = float(row["upper_bound"])
        mid = (low + high) / 2.0
        levels.append([low, mid, high])

    rows = []
    for i, combo in enumerate(itertools.product(*levels)):
        rec = {"real_name": f"scenario_{i:04d}"}
        rec.update(dict(zip(names, combo)))
        rows.append(rec)

    df = pd.DataFrame(rows)
    df.to_csv(output_csv, index=False)
    print(f"Created sweep file: {output_csv}")
    print(f"Number of scenarios: {len(df)}")
    return df


def main():
    cfg, workspace_dir, model_dir = setup_workspace(CONFIG_FILE)

    # Copy SWP forward-run script into model workspace.
    repo_config_dir = Path(__file__).resolve().parents[2] / "config"
    shutil.copy2(repo_config_dir / "forward_run_swp.py", model_dir / "forward_run_swp.py")

    release_vars = read_release_decision_variables(cfg)

    # Create release schedule template and initial input file.
    write_release_schedule_template(
        release_vars=release_vars,
        tpl_file=model_dir / cfg["swp"]["release"].get("template_file", "release_schedule.csv.tpl"),
        schedule_file=model_dir / cfg["swp"]["release"].get("schedule_file", "release_schedule.csv"),
    )

    # Create a dummy/stable SWP output file and instruction file before PEST control creation.
    # This is required because pyemu parses existing .ins/.dat files.
    dummy = model_dir / "swp_outputs.dat"
    dummy.write_text(
        "obsnme obsval\n"
        "min_flow 0.0\n"
        "max_flow 0.0\n"
        "mean_flow 0.0\n"
        "low_flow_deficit 0.0\n"
        "high_flow_excess 0.0\n"
        "total_release 0.0\n",
        encoding="utf-8",
    )
    write_swp_output_instruction_file(dummy, model_dir / "swp_outputs.dat.ins")

    # Create sweep input CSV.
    make_sweep_file(release_vars, model_dir / cfg["swp"].get("sweep_parameter_csv_file", "sweep_in.csv"))

    # Create SWP control file.
    swp_pst = create_swp_control_file(
        model_dir=model_dir,
        swp_pst_file=cfg["swp"].get("control_file", "pestpp_swp.pst"),
        sweep_parameter_csv_file=cfg["swp"].get("sweep_parameter_csv_file", "sweep_in.csv"),
        sweep_output_csv_file=cfg["swp"].get("sweep_output_csv_file", "sweep_out.csv"),
        model_command=cfg["swp"].get("model_command", "python forward_run_swp.py"),
    )

    # Run SWP.
    master_dir = workspace_dir / "swp_master"
    run_pestpp_swp_workers(
        model_dir=model_dir,
        swp_pst_file=swp_pst.name,
        master_dir=master_dir,
        num_workers=10,
        pestpp_exe="pestpp-swp",
    )

    # Rank output.
    ranked = rank_swp_results(master_dir / "sweep_out.csv")
    ranked.to_csv(master_dir / "sweep_out_ranked.csv", index=False)
    print(ranked.head(10))


if __name__ == "__main__":
    main()
```

---

## 8. PEST file behavior

### 8.1 Files in `workspace_dir/main`

After setup, the SWP template directory should contain:

```text
workspace_dir/main/
├── forward_run_swp.py
├── release_schedule.csv.tpl
├── release_schedule.csv
├── swp_outputs.dat
├── swp_outputs.dat.ins
├── sweep_in.csv
├── pestpp_swp.pst
├── swatplus.exe or rev6102.exe
└── SWAT+ input files
```

### 8.2 Template/instruction parsing

`pyemu.helpers.parse_dir_for_io_files(".")` should find:

```text
release_schedule.csv.tpl  -> release_schedule.csv
swp_outputs.dat.ins       -> swp_outputs.dat
```

Then `pestpp-swp` will use `sweep_in.csv` to override release parameter values.

### 8.3 Important PEST option names

The control file should include PEST++ options:

```python
pst.pestpp_options["sweep_parameter_csv_file"] = "sweep_in.csv"
pst.pestpp_options["sweep_output_csv_file"] = "sweep_out.csv"
```

These should be stored through `pyemu.Pst.write(..., version=2)`.

---

## 9. Edge cases to handle in code

### 9.1 Missing `outputs` section

Raise a clear error:

```python
if "outputs" not in cfg:
    raise KeyError("Missing outputs section in setup_swatplus.yml. Add outputs.swatplus.channel.")
```

### 9.2 Empty channel IDs

Do not let SWP run with empty `cha_ids` unless all-channel extraction is implemented.

```python
if not channel_cfg.get("cha_ids"):
    raise ValueError("outputs.swatplus.channel.cha_ids cannot be empty for SWP.")
```

### 9.3 Release/evaluation channel not extracted

Make sure release channels and evaluation channel are included in `cha_ids`.

```python
needed = set(release_vars["channel_id"].astype(int)) | {int(evaluation_channel_id)}
missing = needed - set(channel_cfg["cha_ids"])
if missing:
    raise ValueError(f"These SWP channels are missing from outputs.swatplus.channel.cha_ids: {missing}")
```

### 9.4 Duplicate release names

Reject duplicates before template generation.

### 9.5 Negative release values

For first implementation, reject negative release if the goal is release-water addition. Later, negative values could represent withdrawals.

### 9.6 Stable instruction files

Create `swp_outputs.dat` and `.ins` once before PEST control-file creation. Do not regenerate the `.ins` file with different observation names during worker runs.

### 9.7 Unit consistency

Make `units: cms` explicit in YAML. If users later use `m3/day`, add conversion before adding to `flo_out`.

### 9.8 PEST parameter-name length

Keep names short:

```text
rel_0447_low
rel_0281_low
rel_0447_jan
```

Avoid names longer than PEST limits or names that duplicate after truncation.

---

## 10. Testing plan

### 10.1 Unit tests to add

Add:

```text
tests/test_swp_releases.py
```

Tests:

1. `read_release_decision_variables()` accepts valid config.
2. Duplicate release names raise `ValueError`.
3. `write_release_schedule_template()` creates `.tpl` and initial `.csv`.
4. `expand_release_schedule()` expands period rows to daily rows.
5. `apply_release_to_channel_output()` adds release correctly.
6. `calculate_swp_summary_outputs()` writes stable output metrics.
7. `write_swp_output_instruction_file()` writes expected instruction names.

### 10.2 Example minimal test

```python
def test_apply_release_to_channel_output(tmp_path):
    import pandas as pd
    from ihydrocal.models.swatplus_gwflow.releases import apply_release_to_channel_output

    sim = pd.DataFrame(
        {
            "date": ["2000-01-01", "2000-01-02"],
            "channel_id": [447, 447],
            "simulated": [1.0, 2.0],
        }
    )
    sim_file = tmp_path / "sim.csv"
    sim.to_csv(sim_file, index=False)

    rel = pd.DataFrame(
        {
            "parameter_name": ["rel_0447"],
            "channel_id": [447],
            "start_date": ["2000-01-01"],
            "end_date": ["2000-01-02"],
            "release_cms": [3.0],
        }
    )
    rel_file = tmp_path / "release_schedule.csv"
    rel.to_csv(rel_file, index=False)

    out_file = tmp_path / "adjusted.csv"
    apply_release_to_channel_output(sim_file, rel_file, out_file)

    out = pd.read_csv(out_file)
    assert out["simulated_with_release"].tolist() == [4.0, 5.0]
```

### 10.3 Existing test fixes before adding SWP tests

Fix current package tests:

```python
# tests/test_basic.py
import ihydrocal


def test_version():
    assert hasattr(ihydrocal, "__version__")
    assert ihydrocal.__version__ == "0.0.0b3"
```

Run tests with an editable install:

```bash
pip install -e .
pytest -q
```

---

## 11. Step-by-step implementation order

### Step 1: Fix config foundation

Modify:

```text
config/setup_swatplus.yml
```

Add `outputs:` and `swp:` sections.

### Step 2: Add release utilities

Create:

```text
src/ihydrocal/models/swatplus_gwflow/releases.py
```

Add the helper functions from Section 4.

### Step 3: Add SWP PEST helpers

Modify:

```text
src/ihydrocal/core/pest.py
```

Add:

```text
create_swp_control_file
run_pestpp_swp_workers
rank_swp_results
```

### Step 4: Add SWP forward-run script

Create:

```text
config/forward_run_swp.py
```

Use Section 6 as the first version.

### Step 5: Add SWP example script

Create:

```text
examples/scripts/04_run_swp.py
```

Use Section 7 as the first version.

### Step 6: Add binary support

Add `pestpp-swp` to YAML binary list and place executable in:

```text
bin/windows/pestpp-swp.exe
```

or configure PATH-based execution.

### Step 7: Run a tiny sweep

Start with only one release parameter and three scenarios:

```csv
real_name,rel_0447_low
scenario_000,0.0
scenario_001,1.0
scenario_002,2.0
```

Verify:

```text
swp_master/sweep_out.csv
```

is created.

### Step 8: Expand to multiple channels/periods

After the one-parameter sweep works, add more release variables.

---

## 12. Recommended first user workflow

After implementation, the user workflow should look like:

```python
from pathlib import Path

from ihydrocal.core.config import load_config
from ihydrocal.core.workspace import setup_workspace
from ihydrocal.core.pest import create_swp_control_file, run_pestpp_swp_workers, rank_swp_results
from ihydrocal.models.swatplus_gwflow.releases import (
    read_release_decision_variables,
    write_release_schedule_template,
    write_swp_output_instruction_file,
)
```

Then:

```python
cfg, workspace_dir, model_dir = setup_workspace("config/setup_swatplus.yml")
```

Then create SWP files and run:

```python
release_vars = read_release_decision_variables(cfg)

write_release_schedule_template(
    release_vars,
    tpl_file=model_dir / "release_schedule.csv.tpl",
    schedule_file=model_dir / "release_schedule.csv",
)

swp_pst = create_swp_control_file(
    model_dir=model_dir,
    swp_pst_file="pestpp_swp.pst",
    model_command="python forward_run_swp.py",
)

run_pestpp_swp_workers(
    model_dir=model_dir,
    swp_pst_file="pestpp_swp.pst",
    master_dir=workspace_dir / "swp_master",
    num_workers=10,
)

ranked = rank_swp_results(workspace_dir / "swp_master" / "sweep_out.csv")
ranked.head(10)
```

---

## 13. Later upgrade path: true SWAT+ release input

Once the post-processing SWP workflow is validated, add a second application method:

```yaml
swp:
  release:
    application_method: swatplus_input
```

Then implement a function such as:

```python
def apply_release_to_swatplus_input_files(...):
    ...
```

Candidate SWAT+ mechanisms may include reservoir release, recall, point-source, or water allocation files depending on the exact SWAT+ setup. This should be implemented only after identifying the exact SWAT+ input file that should receive release water.

---

## 14. Final recommendation

Do not start by adding true SWAT+ input-side release logic. Start with the post-processing release scenario sweep. This gives you a working `pestpp-swp` framework quickly and makes it easier to debug:

- PEST template parsing,
- SWP control-file options,
- worker execution,
- release scenario generation,
- output collection,
- ranking.

After that works, the release application method can be switched from post-processing to a true SWAT+ input-side implementation.
