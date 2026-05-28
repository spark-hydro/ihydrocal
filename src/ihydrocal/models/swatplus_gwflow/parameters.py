from pathlib import Path
from typing import Any

import pandas as pd


def read_parameter_database(parameter_db: str | Path) -> pd.DataFrame:
    """
    Read a SWAT+ parameter database CSV file.

    The SWAT+ parameter database exported from SWAT+ Editor has two metadata
    rows before the actual header, so we read it with skiprows=2.
    """
    parameter_db = Path(parameter_db)

    if not parameter_db.exists():
        raise FileNotFoundError(f"Parameter database not found: {parameter_db}")

    df = pd.read_csv(parameter_db, skiprows=2)

    # Remove empty unnamed columns
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    # Clean column names
    df.columns = df.columns.str.strip()

    # Required columns
    required_columns = ["flag", "name", "obj_typ", "abs_min", "abs_max"]

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise KeyError(
            "Missing required parameter database column(s): "
            + ", ".join(missing)
        )

    return df