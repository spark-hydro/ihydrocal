from pathlib import Path
from typing import Any

import pandas as pd


def find_parameter_header_row(parameter_db: str | Path) -> int:
    """
    Find the row index where the actual parameter database header starts.
    """
    parameter_db = Path(parameter_db)

    with open(parameter_db, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line_clean = line.strip().lower().replace(" ", "")
            if line_clean.startswith("flag,name,"):
                return i

    raise ValueError(
        f"Could not find parameter database header row starting with 'flag,name': {parameter_db}"
    )


def read_parameter_database(parameter_db: str | Path) -> pd.DataFrame:
    """
    Read an iHydroCal SWAT+ parameter database CSV file.
    """
    parameter_db = Path(parameter_db)

    if not parameter_db.exists():
        raise FileNotFoundError(f"Parameter database not found: {parameter_db}")

    header_row = find_parameter_header_row(parameter_db)

    df = pd.read_csv(parameter_db, skiprows=header_row)

    # Remove empty unnamed columns
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    # Clean column names
    df.columns = df.columns.str.strip()

    required_columns = [
        "flag",
        "name",
        "chg_type",
        "val",
        "obj_typ",
        "obj_ids",
        "conds",
        "lyr1",
        "lyr2",
        "year1",
        "year2",
        "day1",
        "day2",
        "obj_tot",
        "abs_min",
        "abs_max",
        "parlbnd",
        "parubnd",
        "partrans",
        "pargp",
        "scale",
        "offset",
        "dercom",
    ]

    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        raise KeyError(
            "Missing required parameter database column(s): "
            + ", ".join(missing)
        )

    return df


def normalize_chg_type(value: Any, default: str = "pctchg") -> str:
    """
    Use default change type when chg_type is empty, none, null, or NaN.
    """
    if pd.isna(value):
        return default

    value = str(value).strip()

    if value == "" or value.lower() in ["none", "nan", "null"]:
        return default

    return value


def get_active_parameters(parameter_db: str | Path) -> pd.DataFrame:
    """
    Read parameter database and return only active parameters where flag == 1.
    """
    df = read_parameter_database(parameter_db)
    df["flag"] = pd.to_numeric(df["flag"], errors="coerce").fillna(0).astype(int)
    active = df[df["flag"] == 1].copy()
    active["chg_type"] = active["chg_type"].apply(normalize_chg_type)
    return active


def write_calibration_cal(active: pd.DataFrame, output_file: str | Path) -> Path:
    """
    Write SWAT+ calibration.cal file from active parameter dataframe.
    """
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    n_pars = len(active)

    lines = []
    lines.append("  calibration.cal developed from iHydroCal\n")
    lines.append(f"{n_pars:6d}\n")
    lines.append(
        " NAME       CHG_TYP                VAL   CONDS  LYR1  LYR2   "
        "YEAR1  YEAR2   DAY1   DAY2  OBJ_TOT\n"
    )

    for _, row in active.iterrows():
        name = str(row["name"]).strip()
        chg_type = normalize_chg_type(row.get("chg_type", "pctchg"))
        val = float(row.get("val", 1.0e-7))

        conds = int(row.get("conds", 0))
        lyr1 = int(row.get("lyr1", 0))
        lyr2 = int(row.get("lyr2", 0))
        year1 = int(row.get("year1", 0))
        year2 = int(row.get("year2", 0))
        day1 = int(row.get("day1", 0))
        day2 = int(row.get("day2", 0))
        obj_tot = int(row.get("obj_tot", 0))

        line = (
            f"{name:<12}"
            f"{chg_type:<12}"
            f"{val:14.6E}"
            f"{conds:4d}"
            f"{lyr1:12d}"
            f"{lyr2:12d}"
            f"{year1:12d}"
            f"{year2:12d}"
            f"{day1:12d}"
            f"{day2:12d}"
            f"{obj_tot:12d}\n"
        )

        lines.append(line)

    output_file.write_text("".join(lines), encoding="utf-8")

    return output_file

def make_pest_parameter_name(name: str, index: int | None = None) -> str:
    """
    Create a PEST-safe parameter name.

    PEST parameter names should be short and unique.
    If the same SWAT+ parameter appears multiple times, index can be used.
    """
    par_name = str(name).strip().lower()

    if index is not None:
        par_name = f"{par_name}_{index}"

    return par_name[:12]


def write_calibration_template(
    active: pd.DataFrame,
    cal_file: str | Path,
    tpl_file: str | Path | None = None,
) -> Path:
    """
    Create a PEST template file from calibration.cal.

    The template file is written as:
        calibration.cal.tpl
    """
    cal_file = Path(cal_file)

    if tpl_file is None:
        tpl_file = cal_file.with_suffix(cal_file.suffix + ".tpl")
    else:
        tpl_file = Path(tpl_file)

    if not cal_file.exists():
        raise FileNotFoundError(f"calibration.cal not found: {cal_file}")

    lines = cal_file.read_text(encoding="utf-8").splitlines()

    # First line required by PEST template files
    tpl_lines = ["ptf ~"]

    # Keep the first 3 calibration.cal lines unchanged after ptf line
    tpl_lines.extend(lines[:3])

    data_lines = lines[3:]

    for i, line in enumerate(data_lines):
        if i >= len(active):
            tpl_lines.append(line)
            continue

        row = active.iloc[i]
        name = str(row["name"]).strip()

        par_name = make_pest_parameter_name(name)

        # PEST template placeholder.
        # Width kept similar to calibration value field.
        placeholder = f"~ {par_name:<16} ~"

        # Replace the value field using fixed columns from our generated file.
        # In write_calibration_cal(), value starts after name + chg_type.
        # name field: 12 chars, chg_type field: 12 chars, val field: 20 chars
        start = 12 + 12
        end = start + 20

        new_line = line[:start] + f"{placeholder:>20}" + line[end:]
        tpl_lines.append(new_line)

    tpl_file.write_text("\n".join(tpl_lines) + "\n", encoding="utf-8")

    return tpl_file
