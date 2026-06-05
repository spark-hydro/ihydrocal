from pathlib import Path
from typing import Any
import os
import psutil
import pandas as pd
from tqdm import tqdm


def find_swatplus_output_header_row(output_file: str | Path) -> int:
    """
    Find the SWAT+ output header row.

    Looks for the row starting with:
        jday mon day yr unit
    """
    output_file = Path(output_file)

    with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            clean = line.strip().lower().split()
            if clean[:5] == ["jday", "mon", "day", "yr", "unit"]:
                return i

    raise ValueError(f"Could not find SWAT+ output header row: {output_file}")


def extract_swatplus_channel_output_long(
    output_file: str | Path,
    output_csv: str | Path,
    value_col: str,
    cha_ids: list[int],
    id_col: str = "gis_id",
    chunksize: int = 200_000,
) -> Path:
    """
    Extract selected SWAT+ channel output values from a large SWAT+ output file.

    This function is designed for very large SWAT+ output files such as
    channel_sd_day.txt, which can be several GB in size. Instead of reading
    the full file into memory, it reads the file in chunks and extracts only
    selected channel IDs and one selected variable.

    Parameters
    ----------
    output_file : str or Path
        Path to the original SWAT+ output file.
        Example:
            channel_sd_day.txt

    output_csv : str or Path
        Path to the extracted output CSV file.
        Example:
            cha_flo_out_day_long.csv

    value_col : str
        SWAT+ output variable to extract.
        Example:
            flo_out, flo_in, geo_bf

    cha_ids : list[int]
        List of channel IDs to extract.
        These should match the selected id_col.

    id_col : str, default "gis_id"
        Column used to identify channels in the SWAT+ output file.
        Common options:
            unit
            gis_id

    chunksize : int, default 200_000
        Number of rows read at a time.
        Smaller chunks use less memory but may be slower.
        Larger chunks may be faster but use more memory.

    Returns
    -------
    Path
        Path to the extracted long-format CSV file.

    Output format
    -------------
    The output CSV is written in long format:

        date,channel_id,simulated
        2022-01-01,1,0.00123
        2022-01-01,2,0.00234
        2022-01-02,1,0.00156

    Notes
    -----
    This long format is better for PEST/iHydroCal workflows because it can be
    directly matched with long-format observation tables using date and
    channel_id.
    """
    output_file = Path(output_file)
    output_csv = Path(output_csv)

    # ------------------------------------------------------------------
    # Check whether the SWAT+ output file exists.
    # ------------------------------------------------------------------
    if not output_file.exists():
        raise FileNotFoundError(f"SWAT+ output file not found: {output_file}")

    # ------------------------------------------------------------------
    # SWAT+ output files usually have several title/unit rows before the
    # actual data table. This helper finds the row containing column names:
    # jday mon day yr unit ...
    # ------------------------------------------------------------------
    header_row = find_swatplus_output_header_row(output_file)

    # ------------------------------------------------------------------
    # Read only the header row first. This is very fast and lets us check
    # whether required columns exist before reading the huge file.
    # ------------------------------------------------------------------
    header = pd.read_csv(
        output_file,
        sep=r"\s+",
        skiprows=header_row,
        nrows=0,
        engine="python",
    )

    # ------------------------------------------------------------------
    # We only need date columns, channel ID column, and selected value column.
    # This reduces memory use during chunk reading.
    # ------------------------------------------------------------------
    required_cols = ["yr", "mon", "day", id_col, value_col]
    missing = [col for col in required_cols if col not in header.columns]

    if missing:
        raise KeyError(
            f"Missing required column(s): {missing}. "
            f"Available columns: {list(header.columns)}"
        )

    # Make sure channel IDs are integers for reliable filtering.
    cha_ids = [int(v) for v in cha_ids]

    # Create output folder if needed.
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    # This controls whether we write the CSV header.
    first_write = True

    # ------------------------------------------------------------------
    # Read the large SWAT+ output file in chunks.
    #
    # skiprows = header_row + 2:
    #   + header_row skips rows before the column names
    #   + 1 skips the column-name row
    #   + 1 skips the units row
    #
    # names=list(header.columns):
    #   assigns the detected column names to all chunks.
    #
    # usecols=required_cols:
    #   reads only necessary columns.
    # ------------------------------------------------------------------
    reader = pd.read_csv(
        output_file,
        sep=r"\s+",
        skiprows=header_row + 2,
        names=list(header.columns),
        usecols=required_cols,
        chunksize=chunksize,
        engine="python",
    )

    pbar = tqdm(reader, desc=f"Extracting {value_col}", unit="chunk")

    for chunk in pbar:
        # Show memory usage in the tqdm progress bar if helper exists.
        # This requires get_memory_usage_mb() to be defined in this module.
        if "get_memory_usage_mb" in globals():
            pbar.set_postfix(memory=f"{get_memory_usage_mb():.1f} MB")

        # Convert the channel ID column to numeric.
        # Non-numeric values become NaN and will be excluded.
        chunk[id_col] = pd.to_numeric(chunk[id_col], errors="coerce")

        # Keep only selected channels.
        # .copy() avoids pandas SettingWithCopyWarning later.
        chunk = chunk[chunk[id_col].isin(cha_ids)].copy()

        # If no selected channels are found in this chunk, skip it.
        if chunk.empty:
            continue

        # Build date column from SWAT+ year/month/day columns.
        chunk["date"] = pd.to_datetime(
            {
                "year": chunk["yr"].astype(int),
                "month": chunk["mon"].astype(int),
                "day": chunk["day"].astype(int),
            }
        )

        # Keep only the columns needed for later observation matching.
        out = chunk[["date", id_col, value_col]].copy()

        # Rename columns to a general iHydroCal format.
        out = out.rename(
            columns={
                id_col: "channel_id",
                value_col: "simulated",
            }
        )

        # Ensure channel_id is integer.
        out["channel_id"] = out["channel_id"].astype(int)

        # Append this chunk to the output CSV.
        # Header is written only once.
        out.to_csv(
            output_csv,
            mode="w" if first_write else "a",
            header=first_write,
            index=False,
        )

        first_write = False

    return output_csv


def get_memory_usage_mb() -> float:
    """
    Return current Python process memory usage in MB.
    """
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024