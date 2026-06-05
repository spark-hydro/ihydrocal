from pathlib import Path

import pandas as pd


def make_channel_obsname(channel_id: int, date, site_no: str | None = None) -> str:
    """
    Create PEST++ observation name.

    Example:
        channel_id = 389
        site_no = 08405400
        date = 2022-01-01

        -> cha0389_site08405400_20220101
    """
    date_str = pd.to_datetime(date).strftime("%Y%m%d")

    if site_no is None:
        return f"cha{int(channel_id):04d}_{date_str}"

    site_no = str(site_no).strip()

    return f"cha{int(channel_id):04d}_site{site_no}_{date_str}"


def remove_missing_observations(
    df: pd.DataFrame,
    value_col: str = "observed",
    missing_values: list[float] | None = None,
) -> pd.DataFrame:
    """
    Remove missing observations while keeping valid zero values.
    """
    if missing_values is None:
        missing_values = [-999]

    df = df.copy()

    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")

    # Remove user-defined missing values such as -999.
    # Important: zero values are preserved.
    df.loc[df[value_col].isin(missing_values), value_col] = pd.NA

    # Remove blank/NaN observations.
    df = df.dropna(subset=[value_col])

    return df


def read_streamflow_observations_long(
    obs_file: str | Path,
    date_col: str = "date",
    site_prefix: str = "site_",
    missing_values: list[float] | None = None,
) -> pd.DataFrame:
    """
    Read wide streamflow observation file and convert to long format.

    Input example:
        date, site_08379500, site_08380500

    Output columns:
        date, site_col, site_no, observed
    """
    obs_file = Path(obs_file)

    if not obs_file.exists():
        raise FileNotFoundError(f"Observation file not found: {obs_file}")

    df = pd.read_csv(obs_file)

    if date_col not in df.columns:
        raise KeyError(
            f"Date column '{date_col}' not found in {obs_file}. "
            f"Available columns: {list(df.columns)}"
        )

    df[date_col] = pd.to_datetime(df[date_col])

    site_cols = [col for col in df.columns if col.startswith(site_prefix)]

    if not site_cols:
        raise ValueError(
            f"No observation columns starting with '{site_prefix}' found in {obs_file}"
        )

    obs_long = df.melt(
        id_vars=date_col,
        value_vars=site_cols,
        var_name="site_col",
        value_name="observed",
    )

    obs_long = obs_long.rename(columns={date_col: "date"})

    obs_long["site_no"] = obs_long["site_col"].str.replace(
        site_prefix, "", regex=False
    )

    obs_long = remove_missing_observations(
        obs_long,
        value_col="observed",
        missing_values=missing_values,
    )

    return obs_long


def read_channel_gage_mapping(
    mapping_file: str | Path,
    site_col: str = "site_no",
    channel_col: str = "channel_id",
) -> pd.DataFrame:
    """
    Read channel-gage mapping file.

    Expected output columns:
        site_no, channel_id
    """
    mapping_file = Path(mapping_file)

    if not mapping_file.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_file}")

    df = pd.read_csv(mapping_file, dtype={site_col: str})

    required_cols = [site_col, channel_col]
    missing = [col for col in required_cols if col not in df.columns]

    if missing:
        raise KeyError(
            f"Missing required column(s) in mapping file: {missing}. "
            f"Available columns: {list(df.columns)}"
        )

    mapping = df[[site_col, channel_col]].copy()

    mapping = mapping.rename(
        columns={
            site_col: "site_no",
            channel_col: "channel_id",
        }
    )

    mapping["site_no"] = mapping["site_no"].astype(str).str.strip()
    mapping["channel_id"] = pd.to_numeric(
        mapping["channel_id"],
        errors="coerce",
    )

    mapping = mapping.dropna(subset=["channel_id"])
    mapping["channel_id"] = mapping["channel_id"].astype(int)

    mapping = mapping.drop_duplicates(subset=["site_no", "channel_id"])

    return mapping


def build_streamflow_observation_table(
    obs_long: pd.DataFrame,
    mapping: pd.DataFrame,
) -> pd.DataFrame:
    """
    Match observed streamflow sites with channel IDs and create PEST obsnames.

    Required input columns:
        obs_long: date, site_no, observed
        mapping: site_no, channel_id

    Output columns:
        obsname, date, site_no, channel_id, observed
    """
    obs_long = obs_long.copy()
    mapping = mapping.copy()

    obs_long["site_no"] = obs_long["site_no"].astype(str).str.strip()
    mapping["site_no"] = mapping["site_no"].astype(str).str.strip()

    obs_table = obs_long.merge(
        mapping,
        on="site_no",
        how="inner",
    )

    obs_table["obsname"] = [
        make_channel_obsname(channel_id, date, site_no)
        for channel_id, date, site_no in zip(
            obs_table["channel_id"],
            obs_table["date"],
            obs_table["site_no"],
        )
    ]

    obs_table = obs_table[
        ["obsname", "date", "site_no", "channel_id", "observed"]
    ]

    obs_table = obs_table.sort_values(["date", "channel_id"]).reset_index(drop=True)

    return obs_table


def create_streamflow_simulation_table(
    obs_table: pd.DataFrame,
    sim_long_file: str | Path,
    sim_value_col: str = "simulated",
) -> pd.DataFrame:
    """
    Create a PEST-ready simulated streamflow table.

    Input simulation file:
        date, channel_id, simulated

    Output:
        obsname, simulated
    """
    sim_long_file = Path(sim_long_file)

    if not sim_long_file.exists():
        raise FileNotFoundError(f"Simulation file not found: {sim_long_file}")

    sim_long = pd.read_csv(sim_long_file, parse_dates=["date"])

    required_cols = ["date", "channel_id", sim_value_col]
    missing = [col for col in required_cols if col not in sim_long.columns]

    if missing:
        raise KeyError(
            f"Missing required column(s) in simulation file: {missing}. "
            f"Available columns: {list(sim_long.columns)}"
        )

    obs_table = obs_table.copy()
    obs_table["date"] = pd.to_datetime(obs_table["date"])
    obs_table["channel_id"] = obs_table["channel_id"].astype(int)

    sim_long["date"] = pd.to_datetime(sim_long["date"])
    sim_long["channel_id"] = sim_long["channel_id"].astype(int)

    merged = obs_table.merge(
        sim_long,
        on=["date", "channel_id"],
        how="inner",
    )

    sim_table = merged[["obsname", sim_value_col]].copy()

    return sim_table


def write_simulation_csv(
    sim_table: pd.DataFrame,
    output_file: str | Path,
) -> Path:
    """
    Write PEST-ready simulated values to CSV.

    Output columns:
        obsname, simulated
    """
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    sim_table.to_csv(output_file, index=False)

    return output_file

def write_simulation_dat(
    sim_table: pd.DataFrame,
    output_file: str | Path,
) -> Path:
    """
    Write PEST-ready simulated values as a whitespace-delimited DAT file.

    Output format:
        obsname simulated
        cha0015_site08447300_20200101 0.05089

    This format works well with PEST instruction files using the `w` command.
    """
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    sim_table.to_csv(
        output_file,
        sep=" ",
        index=False,
    )

    return output_file


def write_simulation_instruction_file(
    sim_dat: str | Path,
    ins_file: str | Path | None = None,
    obsname_col: str = "obsname",
) -> Path:
    """
    Create a PEST instruction file for a PEST-ready simulation DAT file.

    Expected simulation DAT format:
        obsname simulated
        cha0123_20220101 1.234
        cha0123_20220102 1.456

    Instruction file format:
        pif ~
        l1
        l1 w !cha0123_20220101!
        l1 w !cha0123_20220102!

    Notes
    -----
    The first 'l1' skips the header line.

    Each following line:
        l1  -> move to the next line
        w   -> skip the obsname column
        !obsname! -> read the simulated value column
    """
    sim_dat = Path(sim_dat)

    if not sim_dat.exists():
        raise FileNotFoundError(f"Simulation DAT not found: {sim_dat}")

    if ins_file is None:
        ins_file = sim_dat.with_suffix(sim_dat.suffix + ".ins")
    else:
        ins_file = Path(ins_file)

    # Read whitespace-delimited DAT file
    df = pd.read_csv(sim_dat, sep=r"\s+")

    if obsname_col not in df.columns:
        raise KeyError(
            f"Observation name column '{obsname_col}' not found in {sim_dat}. "
            f"Available columns: {list(df.columns)}"
        )

    lines = ["pif ~", "l1"]

    for obsname in df[obsname_col]:
        lines.append(f"l1 w !{obsname}!")

    ins_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return ins_file


def prepare_streamflow_instruction_files(
    obs_file: str | Path,
    mapping_file: str | Path,
    sim_file: str | Path,
    output_dat: str | Path,
    output_ins: str | Path | None = None,
    date_col: str = "date",
    site_prefix: str = "site_",
    site_col: str = "site_no",
    channel_col: str = "channel_id",
    missing_values: list[float] | None = None,
    create_ins: bool = True,
) -> tuple[Path, Path, pd.DataFrame]:
    """
    Prepare PEST-ready streamflow simulation CSV and instruction file.

    This function:
    1. Reads observed streamflow from a wide observation file.
    2. Converts observations to long format.
    3. Removes missing observations, including -999 by default.
       Valid zero streamflow values are preserved.
    4. Reads site-to-channel mapping.
    5. Creates unique PEST observation names.
    6. Matches observations with extracted simulated streamflow.
    7. Writes a PEST-ready simulation CSV.
    8. Writes the corresponding PEST instruction file.

    Parameters
    ----------
    obs_file : str or Path
        Observed streamflow file.
        Example:
            stf_day.obd.csv

    mapping_file : str or Path
        Site-to-channel mapping file.
        Must include site_no and channel_id columns.
        Example:
            channels_gages.csv

    sim_file : str or Path
        Extracted simulated streamflow file in long format.
        Expected columns:
            date, channel_id, simulated
        Example:
            cha_flo_out_day.csv

    output_csv : str or Path
        Output PEST-ready simulation CSV.
        Example:
            sim_stf_day.csv

    output_ins : str or Path, optional
        Output PEST instruction file.
        If None, use:
            output_csv + ".ins"

    date_col : str
        Date column in the observed file.

    site_prefix : str
        Prefix of observed site columns.
        Example:
            site_08379500

    missing_values : list[float], optional
        User-defined missing value codes.
        Default:
            [-999]
    
    create_ins : bool
        During normal PEST forward runs, create_ins should usually be False
        because the instruction file is already created during setup.    

    Returns
    -------
    output_csv : Path
        Path to the PEST-ready simulation CSV.

    output_ins : Path
        Path to the PEST instruction file.

    obs_table : pandas.DataFrame
        Matched observation table with obsname, date, site_no, channel_id,
        and observed values.
    """
    obs_long = read_streamflow_observations_long(
        obs_file=obs_file,
        date_col=date_col,
        site_prefix=site_prefix,
        missing_values=missing_values,
    )

    mapping = read_channel_gage_mapping(
        mapping_file=mapping_file,
        site_col=site_col,
        channel_col=channel_col,
    )

    obs_table = build_streamflow_observation_table(
        obs_long=obs_long,
        mapping=mapping,
    )

    sim_table = create_streamflow_simulation_table(
        obs_table=obs_table,
        sim_long_file=sim_file,
    )

    output_dat = write_simulation_dat(
        sim_table=sim_table,
        output_file=output_dat,
    )

    # Always define expected instruction-file path
    if output_ins is None:
        output_ins = output_dat.with_suffix(output_dat.suffix + ".ins")
    else:
        output_ins = Path(output_ins)

    # Only write/rewrite instruction file when requested
    if create_ins:
        output_ins = write_simulation_instruction_file(
            sim_dat=output_dat,
            ins_file=output_ins,
        )
        print(f"Created instruction file: {output_ins}")

    print(f"Created simulation DAT: {output_dat}")
    print(f"Number of streamflow observations: {len(sim_table)}")

    return output_dat, output_ins, obs_table


def build_streamflow_obs_table_from_config(
    cfg: dict,
    site_col: str = "SITENO",
    channel_col: str = "channel_id",
) -> pd.DataFrame:
    """
    Build streamflow observation table from iHydroCal config.

    This reads:
        config/stf_day.obd.csv
        config/channels_gages.csv

    and returns:
        obsname, date, site_no, channel_id, observed
    """
    config_dir = cfg["config_dir"]

    obs_long = read_streamflow_observations_long(
        obs_file=config_dir / "stf_day.obd.csv",
        date_col="date",
        site_prefix="site_",
        missing_values=[-999],
    )

    mapping = read_channel_gage_mapping(
        mapping_file=config_dir / "channels_gages.csv",
        site_col=site_col,
        channel_col=channel_col,
    )

    obs_table = build_streamflow_observation_table(
        obs_long=obs_long,
        mapping=mapping,
    )

    return obs_table
