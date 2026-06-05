from pathlib import Path
from typing import Any

import os
import pandas as pd
import pyemu
import psutil


def create_pest_control_file(
    cfg: dict,
    model_dir: str | Path,
    pst_file: str | Path | None = None,
    model_command: str | None = None,
    noptmax: int | None = None,
    update_observations: bool = True,
    update_parameters: bool = True,
) -> Path:
    """
    Create a PEST control file from template and instruction files.

    This function:
    1. Finds *.tpl and *.ins files in model_dir.
    2. Creates a PEST control file using pyEMU.
    3. Sets model command and noptmax.
    4. Optionally updates observation values and groups from observed data.
    5. Writes the PEST control file as version 2.
    """
    model_dir = Path(model_dir).resolve()

    if not model_dir.exists():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")

    if pst_file is None:
        pst_file = cfg["pest"]["control_file"]

    if model_command is None:
        model_command = cfg["pest"]["model_command"]

    if noptmax is None:
        noptmax = cfg["pest"]["noptmax"]

    pst_file = Path(pst_file)

    if not pst_file.is_absolute():
        pst_file = model_dir / pst_file

    old_cwd = Path.cwd()

    try:
        os.chdir(model_dir)

        io_files = pyemu.helpers.parse_dir_for_io_files(".")
        pst = pyemu.Pst.from_io_files(*io_files)

        pst.model_command = [model_command]
        pst.control_data.noptmax = noptmax

        if update_observations:
            from ihydrocal.models.swatplus_gwflow.observations import (
                build_streamflow_obs_table_from_config,
            )

            obs_table = build_streamflow_obs_table_from_config(cfg)

            pst = update_pest_observations_from_table(
                pst=pst,
                obs_table=obs_table,
            )

        # Update PEST parameter bounds, offsets, and groups
        if update_parameters:
            from ihydrocal.models.swatplus_gwflow.parameters import get_active_parameters

            parameter_db_name = cfg["input_files"]["swatplus"]["parameter_databases"][0]
            parameter_db = cfg["config_dir"] / parameter_db_name

            active_parameters = get_active_parameters(parameter_db)

            pest_par_cfg = cfg["pest"].get("parameters", {})

            use_offset_for_pctchg = pest_par_cfg.get(
                "use_offset_for_pctchg",
                True,
            )

            default_pctchg_range = pest_par_cfg.get(
                "default_pctchg_range",
                50.0,
            )

            pst = update_pest_parameters_from_table(
                pst=pst,
                active_parameters=active_parameters,
                use_offset_for_pctchg=use_offset_for_pctchg,
                default_pctchg_range=default_pctchg_range,
            )
        pst.write(str(pst_file), version=2)

    finally:
        os.chdir(old_cwd)

    return pst_file


def update_pest_observations_from_table(
    pst: pyemu.Pst,
    obs_table: pd.DataFrame,
    obsname_col: str = "obsname",
    observed_col: str = "observed",
    channel_col: str = "channel_id",
) -> pyemu.Pst:
    """
    Update PEST observation values and observation groups.

    Parameters
    ----------
    pst : pyemu.Pst
        PEST control object.

    obs_table : pandas.DataFrame
        Observation table created by iHydroCal.
        Required columns:
            obsname, observed, channel_id

    obsname_col : str
        Column containing PEST observation names.

    observed_col : str
        Column containing actual observed values.

    channel_col : str
        Column containing SWAT+ channel IDs.

    Returns
    -------
    pyemu.Pst
        Updated PEST control object.
    """
    required_cols = [obsname_col, observed_col, channel_col]
    missing = [col for col in required_cols if col not in obs_table.columns]

    if missing:
        raise KeyError(
            f"Missing required column(s) in obs_table: {missing}. "
            f"Available columns: {list(obs_table.columns)}"
        )
    
    obs_data = pst.observation_data

    if obs_data is None:
        raise ValueError(
            "pst.observation_data is None. "
            "Check that instruction files were parsed correctly."
        )


    obs_table = obs_table.copy()
    obs_table[obsname_col] = obs_table[obsname_col].astype(str)

    obs_meta = obs_table.set_index(obsname_col)

    common_obs = obs_data.index.intersection(obs_meta.index)

    if len(common_obs) == 0:
        raise ValueError("No matching observation names found between PEST and obs_table.")

    # Replace default obsval with actual observed values
    obs_data.loc[common_obs, "obsval"] = (
        obs_meta.loc[common_obs, observed_col]
        .astype(float)
        .values
    )


    # Set observation group name by channel ID, e.g., cha0015
    obs_data.loc[common_obs, "obgnme"] = (
        obs_meta.loc[common_obs, channel_col]
        .astype(int)
        .map(lambda x: f"cha{x:04d}")
        .values
    )

    return pst


def update_pest_parameters_from_table(
    pst: pyemu.Pst,
    active_parameters: pd.DataFrame,
    name_col: str = "name",
    chg_type_col: str = "chg_type",
    obj_type_col: str = "obj_typ",
    lower_col: str = "parlbnd",
    upper_col: str = "parubnd",
    val_col: str = "val",
    use_offset_for_pctchg: bool = True,
    default_pctchg_range: float = 100.0,
    log_safe_min: float = 1.0,
) -> pyemu.Pst:
    """
    Update PEST parameter data using active SWAT+ parameter database rows.

    This function updates the parameter section of a pyEMU Pst object using
    active SWAT+ calibration parameter information.

    It updates:
        - parval1  : initial parameter value in PEST-space
        - parlbnd  : lower bound in PEST-space
        - parubnd  : upper bound in PEST-space
        - offset   : offset used when writing values to model input files
        - pargp    : PEST parameter group

    Why special handling is needed for pctchg
    -----------------------------------------
    SWAT+ `pctchg` parameters often represent percent changes around zero.

    For example, a user may want:

        actual SWAT+ pctchg range = -100 to +100

    However, if PEST uses:

        partrans = log

    then the PEST-space parameter values must be strictly positive.
    PEST++ cannot take log(0) or log(negative value).

    Therefore, this function uses an offset approach.

    Example
    -------
    User-requested percent-change range:

        default_pctchg_range = 100

    Desired actual SWAT+ range:

        -100 to +100

    Backend PEST-space representation:

        parval1 = 101
        parlbnd = 1
        parubnd = 201
        offset  = -101

    Then when PEST writes the model input value:

        actual model value = pest_value * scale + offset

    assuming scale = 1:

        1   - 101 = -100
        101 - 101 = 0
        201 - 101 = +100

    This keeps all PEST-space values positive, so `partrans = log`
    is safe, while preserving the user-requested actual pctchg range.

    Parameters
    ----------
    pst : pyemu.Pst
        Existing PEST control file object.

    active_parameters : pandas.DataFrame
        Table containing active calibration parameters.

    name_col : str
        Column name containing parameter names.

    chg_type_col : str
        Column name containing SWAT+ change type.
        Common examples:
            - pctchg
            - absval
            - abschg

    obj_type_col : str
        Column name containing SWAT+ object type.
        This is used as the PEST parameter group.
        Examples:
            - hru
            - sol
            - aqu
            - rte
            - bsn

    lower_col : str
        Column name containing lower bound for non-pctchg parameters.

    upper_col : str
        Column name containing upper bound for non-pctchg parameters.

    val_col : str
        Column name containing initial value for non-pctchg parameters.

    use_offset_for_pctchg : bool
        If True, pctchg parameters are converted to positive PEST-space
        using the offset approach.

        If False, pctchg parameters are treated directly using values from
        active_parameters.

    default_pctchg_range : float
        User-facing percent-change range.

        Example:
            default_pctchg_range = 100

        means the actual SWAT+ pctchg value will range from:

            -100 to +100

    log_safe_min : float
        Minimum allowed PEST-space lower bound for offset pctchg parameters.

        Default is 1.0.

        This avoids zero lower bounds when partrans = log.

    Returns
    -------
    pyemu.Pst
        Updated PEST control file object.
    """

    # ------------------------------------------------------------------
    # Get the PEST parameter data table.
    # In pyEMU, this is usually a pandas DataFrame indexed by parameter name.
    # ------------------------------------------------------------------
    par_data = pst.parameter_data

    if par_data is None:
        raise ValueError(
            "pst.parameter_data is None. "
            "Check that template files were parsed correctly."
        )

    # ------------------------------------------------------------------
    # Make sure the input active parameter table contains all required
    # columns before modifying the PEST object.
    # ------------------------------------------------------------------
    required_cols = [
        name_col,
        chg_type_col,
        obj_type_col,
        lower_col,
        upper_col,
        val_col,
    ]

    missing = [col for col in required_cols if col not in active_parameters.columns]

    if missing:
        raise KeyError(
            f"Missing required column(s) in active_parameters: {missing}. "
            f"Available columns: {list(active_parameters.columns)}"
        )

    # Work on a copy to avoid modifying the user's original DataFrame.
    active_parameters = active_parameters.copy()

    updated = 0
    skipped = []

    # ------------------------------------------------------------------
    # Loop through each active SWAT+ calibration parameter.
    # ------------------------------------------------------------------
    for _, row in active_parameters.iterrows():

        # PEST parameter names are commonly lowercase.
        # We normalize here to avoid mismatch caused by capitalization.
        par_name = str(row[name_col]).strip().lower()

        # If this parameter does not exist in the PEST template/control file,
        # skip it and report it later.
        if par_name not in par_data.index:
            skipped.append(par_name)
            continue

        # Read SWAT+ change type and object type.
        chg_type = str(row[chg_type_col]).strip().lower()
        obj_type = str(row[obj_type_col]).strip().lower()

        # Read numeric values from the active parameter table.
        # These are used directly for non-pctchg parameters.
        lower = float(row[lower_col])
        upper = float(row[upper_col])
        val = float(row[val_col])

        # --------------------------------------------------------------
        # Use SWAT+ object type as the PEST parameter group.
        #
        # Example:
        #   hru parameters -> pargp = hru
        #   aqu parameters -> pargp = aqu
        #   rte parameters -> pargp = rte
        #
        # This is helpful later for grouping, regularization, and plots.
        # --------------------------------------------------------------
        par_data.loc[par_name, "pargp"] = obj_type

        # --------------------------------------------------------------
        # Special case: SWAT+ pctchg parameters.
        #
        # User thinks in actual SWAT+ percent-change space:
        #
        #   -default_pctchg_range to +default_pctchg_range
        #
        # But PEST++ may need positive values if:
        #
        #   partrans = log
        #
        # Therefore we create a positive PEST-space range and use offset
        # to shift it back to the desired SWAT+ range.
        # --------------------------------------------------------------
        if chg_type == "pctchg" and use_offset_for_pctchg:

            pct_range = float(default_pctchg_range)

            if pct_range <= 0:
                raise ValueError(
                    "default_pctchg_range must be positive when "
                    "use_offset_for_pctchg=True."
                )

            if log_safe_min <= 0:
                raise ValueError(
                    "log_safe_min must be greater than zero. "
                    "PEST log-transformed parameters cannot have zero "
                    "or negative lower bounds."
                )

            # ----------------------------------------------------------
            # Derive the PEST-space center.
            #
            # Example:
            #   pct_range = 100
            #   log_safe_min = 1
            #
            # We want actual model range:
            #   -100 to +100
            #
            # Let:
            #   pest_lower = 1
            #   pest_center = 101
            #   pest_upper = 201
            #   offset = -101
            #
            # Then:
            #   1   - 101 = -100
            #   101 - 101 = 0
            #   201 - 101 = +100
            #
            # General formula:
            #   pest_center = pct_range + log_safe_min
            #   pest_lower  = log_safe_min
            #   pest_upper  = pct_range + pest_center
            #   offset      = -pest_center
            # ----------------------------------------------------------
            pest_center = pct_range + log_safe_min
            pest_lower = log_safe_min
            pest_upper = pct_range + pest_center
            pest_offset = -pest_center

            par_data.loc[par_name, "parval1"] = pest_center
            par_data.loc[par_name, "parlbnd"] = pest_lower
            par_data.loc[par_name, "parubnd"] = pest_upper
            par_data.loc[par_name, "offset"] = pest_offset

            # ----------------------------------------------------------
            # Keep scale as 1.0 unless the user intentionally changes it.
            #
            # Model value written by PEST is:
            #
            #   model_value = parval1 * scale + offset
            #
            # For this offset approach, scale should normally be 1.0.
            # ----------------------------------------------------------
            if "scale" in par_data.columns:
                par_data.loc[par_name, "scale"] = 1.0

        else:
            # ----------------------------------------------------------
            # Non-pctchg parameters.
            #
            # These use the values directly from the active parameter table.
            #
            # This is appropriate for:
            #   - absval
            #   - abschg
            #   - pctchg when offset handling is disabled
            #
            # Important:
            #   If partrans = log for these parameters, the user must make
            #   sure val, lower, and upper are all strictly positive.
            # ----------------------------------------------------------
            par_data.loc[par_name, "parval1"] = val
            par_data.loc[par_name, "parlbnd"] = lower
            par_data.loc[par_name, "parubnd"] = upper
            par_data.loc[par_name, "offset"] = 0.0

        updated += 1

    # ------------------------------------------------------------------
    # Write updated parameter data back to the PEST object.
    # ------------------------------------------------------------------
    pst.parameter_data = par_data

    # ------------------------------------------------------------------
    # Report parameters that were in the active table but not found in
    # the PEST control/template files.
    # ------------------------------------------------------------------
    if skipped:
        print(
            "Skipped parameter(s) not found in PEST template file: "
            + ", ".join(skipped)
        )

    print(f"Updated PEST parameter data for {updated} parameter(s).")

    return pst


def run_pestpp(
    model_dir: str | Path,
    pst_file: str | Path,
    pestpp_exe: str = "pestpp-glm.exe",
) -> None:
    """
    Run PEST++ using the selected control file.

    Parameters
    ----------
    model_dir : str or Path
        Working directory where the PEST control file exists.

    pst_file : str or Path
        PEST control file name or path.

    pestpp_exe : str
        PEST++ executable name.
        Example:
            pestpp-glm.exe
            pestpp-ies.exe
    """
    model_dir = Path(model_dir).resolve()
    pst_file = Path(pst_file).name

    if not model_dir.exists():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")

    if not (model_dir / pst_file).exists():
        raise FileNotFoundError(f"PEST control file not found: {model_dir / pst_file}")

    pyemu.os_utils.run(
        f"{pestpp_exe} {pst_file}",
        cwd=str(model_dir),
    )

def reweight_pest_control_file(
    model_dir: str | Path,
    pst_file: str | Path,
    output_pst_file: str | Path = "swatp_rw.pst",
    target_phi: float = 1000.0,
) -> Path:
    """
    Reweight non-zero observation groups and write a new PEST control file.

    Parameters
    ----------
    model_dir : str or Path
        Working directory containing the PEST control file.

    pst_file : str or Path
        Input PEST control file.

    output_pst_file : str or Path
        Reweighted PEST control file to write.

    target_phi : float
        Target balanced phi contribution for each non-zero observation group.

    Returns
    -------
    Path
        Path to the reweighted PEST control file.
    """
    model_dir = Path(model_dir).resolve()

    pst_path = Path(pst_file)
    if not pst_path.is_absolute():
        pst_path = model_dir / pst_path

    if not pst_path.exists():
        raise FileNotFoundError(f"PEST control file not found: {pst_path}")

    output_pst_file = Path(output_pst_file)
    if not output_pst_file.is_absolute():
        output_pst_file = model_dir / output_pst_file

    pst = pyemu.Pst(str(pst_path))

    balanced_groups = {
        grp: target_phi
        for grp in pst.nnz_obs_groups
    }

    pst.adjust_weights(obsgrp_dict=balanced_groups)

    pst.write(str(output_pst_file), version=2)

    print(f"Reweighted PEST control file written: {output_pst_file}")

    return output_pst_file


def create_ies_control_file(
    model_dir: str | Path,
    base_pst_file: str | Path,
    ies_pst_file: str | Path = "pecos_rw_ies.pst",
    ies_num_reals: int = 300,
    noptmax: int = 10,
) -> Path:
    """
    Create a PESTPP-IES control file from an existing PEST control file.
    """
    model_dir = Path(model_dir).resolve()

    base_pst_file = Path(base_pst_file)
    if not base_pst_file.is_absolute():
        base_pst_file = model_dir / base_pst_file

    ies_pst_file = Path(ies_pst_file)
    if not ies_pst_file.is_absolute():
        ies_pst_file = model_dir / ies_pst_file

    if not base_pst_file.exists():
        raise FileNotFoundError(f"Base PEST control file not found: {base_pst_file}")

    pst = pyemu.Pst(str(base_pst_file))

    pst.pestpp_options["ies_num_reals"] = ies_num_reals
    pst.control_data.noptmax = noptmax

    # Sort parameters by parameter group to avoid PEST++ warning
    par_data = pst.parameter_data

    if par_data is not None:
        par_data = par_data.copy()
        par_data["_original_order"] = range(len(par_data))

        par_data = (
            par_data
            .sort_values(["pargp", "_original_order"])
            .drop(columns=["_original_order"])
        )

        pst.parameter_data = par_data
    pst.write(str(ies_pst_file), version=2)

    print(f"Created IES control file: {ies_pst_file}")

    return ies_pst_file


def run_pestpp_ies_workers(
    model_dir: str | Path,
    ies_pst_file: str | Path,
    master_dir: str | Path,
    num_workers: int | None = None,
    worker_root: str | Path | None = None,
    pestpp_exe: str = "pestpp-ies",
    reuse_master: bool = False,
) -> None:
    """
    Run PESTPP-IES in parallel using pyEMU workers.
    """
    model_dir = Path(model_dir).resolve()
    ies_pst_file = Path(ies_pst_file).name
    master_dir = Path(master_dir).resolve()

    if worker_root is None:
        worker_root = model_dir.parent
    else:
        worker_root = Path(worker_root).resolve()

    if num_workers is None:
        num_workers = psutil.cpu_count(logical=False)

    if num_workers is None:
        num_workers = 1

    print(f"Starting PESTPP-IES with {num_workers} workers")
    print(f"Template directory: {model_dir}")
    print(f"Worker root       : {worker_root}")
    print(f"Master directory  : {master_dir}")

    pyemu.os_utils.start_workers(
        str(model_dir),
        pestpp_exe,
        ies_pst_file,
        num_workers=num_workers,
        worker_root=str(worker_root),
        master_dir=str(master_dir),
        reuse_master=reuse_master,
    )

def create_morris_control_file(
    model_dir: str | Path,
    base_pst_file: str | Path,
    morris_pst_file: str | Path = "pecos_rw_sen_morris.pst",
    gsa_morris_r: int = 10,
    gsa_morris_p: int = 4,
) -> Path:
    """
    Create a PESTPP-SEN Morris control file from an existing PEST control file.

    Parameters
    ----------
    model_dir : str or Path
        Template model directory, usually ihydrocal_workspace/main.

    base_pst_file : str or Path
        Existing reweighted PEST control file, e.g., pecos_rw.pst.

    morris_pst_file : str or Path
        New Morris sensitivity control file.

    gsa_morris_r : int
        Number of Morris trajectories.
        Total model runs are approximately:
            gsa_morris_r * (number_of_parameters + 1)

    gsa_morris_p : int
        Number of grid levels. A common default is 4.

    Returns
    -------
    Path
        Path to the created Morris control file.
    """
    model_dir = Path(model_dir).resolve()

    base_pst_file = Path(base_pst_file)
    if not base_pst_file.is_absolute():
        base_pst_file = model_dir / base_pst_file

    morris_pst_file = Path(morris_pst_file)
    if not morris_pst_file.is_absolute():
        morris_pst_file = model_dir / morris_pst_file

    if not base_pst_file.exists():
        raise FileNotFoundError(f"Base PEST control file not found: {base_pst_file}")

    pst = pyemu.Pst(str(base_pst_file))

    pst.pestpp_options["gsa_method"] = "morris"
    pst.pestpp_options["gsa_morris_r"] = gsa_morris_r
    pst.pestpp_options["gsa_morris_p"] = gsa_morris_p

    pst.write(str(morris_pst_file), version=2)

    print(f"Created Morris control file: {morris_pst_file}")
    print(f"Estimated model runs: {gsa_morris_r * (pst.npar_adj + 1)}")

    return morris_pst_file

def run_pestpp_sen_workers(
    model_dir: str | Path,
    sen_pst_file: str | Path,
    master_dir: str | Path,
    num_workers: int | None = None,
    worker_root: str | Path | None = None,
    pestpp_exe: str = "pestpp-sen",
    reuse_master: bool = False,
) -> None:
    """
    Run PESTPP-SEN in parallel using pyEMU workers.
    """
    model_dir = Path(model_dir).resolve()
    sen_pst_file = Path(sen_pst_file).name
    master_dir = Path(master_dir).resolve()

    if worker_root is None:
        worker_root = model_dir.parent
    else:
        worker_root = Path(worker_root).resolve()

    if num_workers is None:
        num_workers = psutil.cpu_count(logical=False) or 1

    print(f"Starting PESTPP-SEN with {num_workers} workers")
    print(f"Template directory: {model_dir}")
    print(f"Worker root       : {worker_root}")
    print(f"Master directory  : {master_dir}")

    pyemu.os_utils.start_workers(
        str(model_dir),
        pestpp_exe,
        sen_pst_file,
        num_workers=num_workers,
        worker_root=str(worker_root),
        master_dir=str(master_dir),
        reuse_master=reuse_master,
    )