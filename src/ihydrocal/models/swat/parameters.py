from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pandas as pd

try:
    from tqdm.auto import tqdm
except ImportError:
    tqdm = None


SWAT_SOIL_VARS = [
    "SNAM",
    "HYDGRP",
    "SOL_ZMX",
    "ANION_EXCL",
    "SOL_CRK",
    "TEXTURE",
    "SOL_Z",
    "SOL_BD",
    "SOL_AWC",
    "SOL_K",
    "SOL_CBN",
    "SOL_CLAY",
    "SOL_SILT",
    "SOL_SAND",
    "SOL_ROCK",
    "SOL_ALB",
    "USLE_K",
    "SOL_EC",
    "SOL_CAL",
    "SOL_PH",
]

SWAT_SOIL_FORMATS = [
    "s",
    "s",
    "12.2f",
    "6.3f",
    "6.3f",
    "s",
    "12.2f",
    "12.2f",
    "12.2f",
    "12.2f",
    "12.2f",
    "12.2f",
    "12.2f",
    "12.2f",
    "12.2f",
    "12.2f",
    "12.2f",
    "12.2f",
    "12.2f",
    "12.2f",
]

SWAT_CHM_VARS = ["SOL_NO3", "SOL_ORGN", "SOL_SOLP", "SOL_ORGP", "PPERCO_SUB"]
SWAT_CHM_FORMATS = ["12.2f", "12.2f", "12.2f", "12.2f", "12.2f"]


def _is_float(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _is_int(value: Any) -> bool:
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return False


def _validate_backup_dir(source_dir, target_dir):
    """Fail safely before modifying SWAT files.

    The SWAT parameter editor must always read original files from a backup
    directory and write modified files to the active model directory.
    """

    source_dir = Path(source_dir)
    target_dir = Path(target_dir)

    if not source_dir.exists():
        raise FileNotFoundError(
            f"\nBackup directory does not exist:\n"
            f"  {source_dir}\n\n"
            "SWAT parameter update stopped for safety.\n"
            "Create a backup folder containing the original SWAT input files before running calibration."
        )

    if not source_dir.is_dir():
        raise NotADirectoryError(
            f"Backup path exists but is not a directory:\n"
            f"  {source_dir}"
        )

    if source_dir.resolve() == target_dir.resolve():
        raise ValueError(
            f"\nBackup directory and model directory are the same:\n"
            f"  backup_dir = {source_dir}\n"
            f"  model_dir  = {target_dir}\n\n"
            "SWAT parameter update stopped for safety.\n"
            "The editor must read from backup and write to the active model folder."
        )

    swat_files = [
        p for p in source_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() in {
            ".hru", ".mgt", ".sol", ".rte", ".gw", ".sub", ".bsn", ".chm"
        }
        and not p.name.lower().startswith("output")
    ]

    if len(swat_files) == 0:
        raise FileNotFoundError(
            f"\nNo SWAT input files were found in backup directory:\n"
            f"  {source_dir}\n\n"
            "SWAT parameter update stopped for safety."
        )


def _apply_change(old_value, change_value, method):
    method = str(method).strip().lower()

    if method in {"replace", "absval", "absolute"}:
        return change_value
    if method in {"multiply", "pctchg"}:
        return (1.0 + change_value) * old_value
    if method in {"factor", "scale"}:
        return change_value * old_value
    if method in {"add", "addval"}:
        return old_value + change_value

    raise ValueError(
        f"Unsupported SWAT parameter change method '{method}'. "
        "Use replace, multiply/pctchg, factor, or add."
    )


def _format_numeric(value, old_token, width=16, decimals=6):
    if _is_int(old_token):
        return f"{int(value):{width}d}"
    if _is_float(old_token):
        return f"{float(value):{width}.{decimals}f}"
    return f"{str(value):13s}   "


def replace_swat_parameter_line(line, value, method, ext, num_format=""):
    """Return one SWAT input line with its value changed.

    Parameters
    ----------
    line : str
        Original SWAT text line.
    value : float or str
        Parameter change value.
    method : str
        ``replace``, ``multiply``/``pctchg``, ``factor``, or ``add``.
    ext : str
        SWAT file extension such as ``sol``, ``chm``, ``rte``, ``hru``.
    num_format : str, optional
        Fixed-width numeric format for array-style lines.
    """

    ext = str(ext).lower().strip(".")
    method = str(method).strip().lower()

    if _is_float(value):
        value = float(value)

    if ext in {"sol", "chm"}:
        parts = line.split(":", 1)
        if len(parts) != 2:
            raise ValueError(f"Expected ':' in {ext} line: {line!r}")

        old_text = parts[1].strip()

        if _is_float(old_text) or _is_int(old_text):
            new_value = _apply_change(float(old_text), value, method)
            formatted = f"{new_value:{num_format}}"
        elif num_format != "s":
            nums = [float(item) for item in old_text.split()]
            new_values = [_apply_change(num, value, method) for num in nums]
            formatted = "".join(f"{item:{num_format}}" for item in new_values)
        else:
            formatted = f" {str(value):13s}"

        return f"{parts[0]}:{formatted}\n"

    parts = line.split("|", 1)
    if len(parts) == 1:
        parts.append("\n")

    old_text = parts[0].strip()

    if ext == "rte" and not (_is_float(old_text) or _is_int(old_text)):
        if not num_format:
            raise ValueError(f"Array-style rte line requires num_format: {line!r}")
        width = int(num_format.split(".")[0])
        nums = [
            float(old_text[i : i + width])
            for i in range(0, len(old_text), width)
            if old_text[i : i + width].strip()
        ]
        new_values = [_apply_change(num, value, method) for num in nums]
        formatted = "".join(f"{item:{num_format}}" for item in new_values)
        return f"{formatted}|{parts[1]}"

    if _is_float(old_text) or _is_int(old_text):
        new_value = _apply_change(float(old_text), value, method)
        if ext == "rte":
            formatted = _format_numeric(new_value, old_text, width=14, decimals=6)
        else:
            formatted = _format_numeric(new_value, old_text, width=16, decimals=6)
    else:
        formatted = f"{str(value):13s}   "

    separator = "    |" if ext != "rte" else "    |"
    return f"{formatted}{separator}{parts[1]}"


def get_all_subs_hrus(model_dir):
    """Return all SWAT subbasin and HRU IDs from ``*.hru`` filenames."""

    model_dir = Path(model_dir)
    hru_codes = [
        path.stem
        for path in model_dir.glob("*.hru")
        if not path.name.lower().startswith("output")
    ]

    sub_aux = [code[:5] for code in hru_codes]
    hru_aux = [code[-4:] for code in hru_codes]
    sub_list = sorted(set(sub_aux))

    hru_list = []
    for sub in sub_list:
        indices = [i for i, item in enumerate(sub_aux) if item == sub]
        hru_list.append(sorted(int(hru_aux[i]) for i in indices))

    return [int(item) for item in sub_list], hru_list


def prepare_subs_hrus(model_dir, subs=None, hrus=None):
    """Normalize optional subbasin and HRU selections."""

    sub_list, hru_list = get_all_subs_hrus(model_dir)
    subs = subs or []
    hrus = hrus or []

    if len(subs) == 0:
        return [list(sub_list)], [list(hru_list)]

    normalized_subs = [item if len(item) > 0 else list(sub_list) for item in subs]
    normalized_hrus = []

    if len(hrus) == 0:
        for sub_group in normalized_subs:
            hru_group = []
            for sub in sub_group:
                indices = [i for i, item in enumerate(sub_list) if item == sub]
                for idx in indices:
                    hru_group.append(hru_list[idx])
            normalized_hrus.append(hru_group)
    else:
        for i, sub_group in enumerate(normalized_subs):
            hru_group = hrus[i]
            if len(hru_group) == 0:
                filled = []
                for sub in sub_group:
                    indices = [j for j, item in enumerate(sub_list) if item == sub]
                    for idx in indices:
                        filled.append(hru_list[idx])
                hru_group = filled
            normalized_hrus.append(hru_group)

    return normalized_subs, normalized_hrus


def _sort_subs_hrus(subs, hrus, params):
    indices = [i for i, _ in sorted(enumerate(subs), key=lambda x: len(x[1]), reverse=True)]
    return [subs[i] for i in indices], [hrus[i] for i in indices], [params[i] for i in indices]


def _file_refs_for_selection(subbasins, hrus):
    sub_refs = [f"{int(sub):05d}0000" for sub in subbasins]
    hru_refs = [
        f"{int(sub):05d}{int(hru):04d}"
        for i, sub in enumerate(subbasins)
        for hru in hrus[i]
    ]
    return sub_refs, hru_refs


def _parameter_line_info(param_name, ext, data):
    ext = str(ext).lower().strip(".")
    param_name = str(param_name).strip()

    if ext == "sol":
        idx = SWAT_SOIL_VARS.index(param_name)
        return idx + 1, SWAT_SOIL_FORMATS[idx]

    if ext == "chm":
        idx = SWAT_CHM_VARS.index(param_name)
        return idx + 3, SWAT_CHM_FORMATS[idx]

    if ext == "rte" and param_name == "CH_ERODMO":
        return 23, "6.2f"

    if ext == "rte" and param_name == "HRU_SALT":
        return 28, "6.2f"

    for idx, line in enumerate(data):
        if re.search(rf"\b{re.escape(param_name)}\b", line):
            return idx, ""

    raise KeyError(f"Could not find parameter '{param_name}' in .{ext} file.")


def _target_files_for_extension(model_dir, ext, subbasins, hrus):
    model_dir = Path(model_dir)
    ext = str(ext).lower().strip(".")
    files_all = sorted(
        path.name
        for path in model_dir.glob(f"*.{ext}")
        if not path.name.lower().startswith("output")
    )

    if len(files_all) == 0:
        raise FileNotFoundError(f"No .{ext} files found in {model_dir}")

    if len(files_all) == 1:
        return files_all

    sub_refs, hru_refs = _file_refs_for_selection(subbasins, hrus)
    crit = int(files_all[0][8])
    refs = sub_refs if crit == 0 else hru_refs
    return [f"{ref}.{ext}" for ref in refs]

def _progress_iter(iterable, desc=None, total=None, show_progress=True):
    """Use tqdm when available; otherwise return the original iterable."""
    if show_progress and tqdm is not None:
        return tqdm(iterable, desc=desc, total=total, unit="file")
    return iterable


def write_extension_files(
    param_df,
    source_dir,
    target_dir,
    subbasins,
    hrus,
    show_progress=True,
):
    """Apply parameter changes for one subbasin/HRU selection.

    Original files are always required in source_dir.
    Modified files are written to target_dir.
    """

    source_dir = Path(source_dir)
    target_dir = Path(target_dir)

    _validate_backup_dir(source_dir, target_dir)

    target_dir.mkdir(parents=True, exist_ok=True)

    for ext in param_df["ext"].dropna().unique():
        ext = str(ext).lower().strip(".")
        ext_params = param_df.loc[param_df["ext"] == ext]
        target_files = _target_files_for_extension(
            source_dir,
            ext,
            subbasins,
            hrus,
        )

        for param_name, row in ext_params.iterrows():
            desc = f"{param_name} (*.{ext})"

            for filename in _progress_iter(
                target_files,
                desc=desc,
                total=len(target_files),
                show_progress=show_progress,
            ):
                src = source_dir / filename
                dst = target_dir / filename

                if not src.exists():
                    raise FileNotFoundError(
                        f"Required backup SWAT file not found:\n"
                        f"  {src}\n\n"
                        "SWAT parameter update stopped for safety."
                    )

                # Read target only after backup has been verified.
                # This preserves earlier parameter edits in the same forward run.
                # But the backup folder is still mandatory.
                read_file = dst if dst.exists() else src

                with open(read_file, "r", encoding="ISO-8859-1") as f:
                    data = f.readlines()

                line_idx, num_format = _parameter_line_info(
                    param_name,
                    ext,
                    data,
                )

                data[line_idx] = replace_swat_parameter_line(
                    data[line_idx],
                    row["value"],
                    row["method"],
                    ext,
                    num_format,
                )

                with open(dst, "w", encoding="ISO-8859-1") as f:
                    f.writelines(data)


def write_new_swat_files(
    param_all,
    source_dir,
    target_dir,
    subs=None,
    hrus=None,
    show_progress=True,
):
    """Write updated SWAT text files after applying parameter changes.

    Parameters
    ----------
    param_all : dict or list[dict]
        Dictionary such as ``{"CN2": [0.1, "multiply", "mgt"]}``.
    source_dir : str or Path
        Usually the SWAT backup directory.
    target_dir : str or Path
        Working model directory where modified files are written.
    subs, hrus : list, optional
        Same nested-list convention as the legacy workflow.
    """

    source_dir = Path(source_dir)
    target_dir = Path(target_dir)
    _validate_backup_dir(source_dir, target_dir)

    if isinstance(param_all, dict):
        param_all = [param_all]

    subs, hrus = prepare_subs_hrus(source_dir, subs=subs, hrus=hrus)

    if len(param_all) < len(subs) and len(param_all) not in {0, 1}:
        raise ValueError(
            "List of parameters must have the same length as subbasins list, "
            "or contain one parameter dictionary applied to all selections."
        )

    if len(param_all) == 0:
        param_list = [{} for _ in subs]
    elif len(param_all) == 1:
        param_list = [param_all[0] for _ in subs]
    else:
        param_list = list(param_all)

    subs, hrus, param_list = _sort_subs_hrus(subs, hrus, param_list)

    for sub_group, hru_group, params in zip(subs, hrus, param_list):
        if len(params) == 0:
            continue

        param_df = pd.DataFrame.from_dict(
            params,
            orient="index",
            columns=["value", "method", "ext"],
        )
        param_df["ext"] = param_df["ext"].str.lower().str.strip(".")
        write_extension_files(
            param_df,
            source_dir,
            target_dir,
            sub_group,
            hru_group,
            show_progress=show_progress,
        )


def read_swat_parameter_cal(cal_file):
    """Read ``swat_pars.cal`` and return the legacy parameter dictionary."""

    df = pd.read_csv(cal_file, sep=r"\s+", comment="#")
    df = df[["parnam", "chg_val", "chg_type", "obj_type"]].copy()
    df = df.rename(
        columns={
            "chg_val": "value",
            "chg_type": "method",
            "obj_type": "ext",
        }
    )
    return df.set_index("parnam").T.to_dict("list")


def read_swat_parameter_database(parameter_db):
    """Read a SWAT parameter database CSV."""

    return pd.read_csv(parameter_db, comment="#")


def get_active_swat_parameters(parameter_db):
    """Return active SWAT parameters from a database with ``flag == 1``."""

    df = read_swat_parameter_database(parameter_db)
    df["flag"] = pd.to_numeric(df["flag"], errors="coerce").fillna(0).astype(int)
    active = df.loc[df["flag"] == 1].copy()
    active["chg_type"] = active["chg_type"].fillna("multiply")
    active["chg_val"] = active.get("chg_val", 0)
    return active


def write_swat_parameter_cal(active, cal_file, tpl_file=None):
    """Write ``swat_pars.cal`` and optional PEST template file."""

    cal_file = Path(cal_file)
    cal_file.parent.mkdir(parents=True, exist_ok=True)

    cols = ["parnam", "obj_type", "chg_type", "chg_val", "lb", "ub"]
    data = active.copy()
    data["chg_type"] = data["chg_type"].fillna("multiply")
    data["chg_val"] = data.get("chg_val", 0)

    with open(cal_file, "w", encoding="utf-8") as f:
        f.write("# SWAT parameter changes generated by iHydroCal\n")
        f.write(
            data.loc[:, cols].to_string(
                col_space=2,
                index=False,
                header=True,
                justify="left",
            )
        )

    if tpl_file is None:
        tpl_file = cal_file.with_suffix(cal_file.suffix + ".tpl")
    else:
        tpl_file = Path(tpl_file)

    tpl_data = data.copy()
    tpl_data["chg_val"] = tpl_data["parnam"].apply(lambda name: f" ~   {name:<15s}   ~")

    with open(tpl_file, "w", encoding="utf-8") as f:
        f.write("ptf ~\n")
        f.write("# SWAT parameter changes generated by iHydroCal\n")
        f.write(
            tpl_data.loc[:, cols].to_string(
                col_space=2,
                index=False,
                header=True,
                justify="left",
            )
        )

    return cal_file, tpl_file


class SWATParameterEditor:
    """Edit classic SWAT input files using a backup source directory."""

    def __init__(self, model_dir, backup_dir=None):
        self.model_dir = Path(model_dir)

        if backup_dir is None:
            backup_dir = self.model_dir / "backup"
        else:
            backup_dir = Path(backup_dir)
            if not backup_dir.is_absolute():
                backup_dir = self.model_dir / backup_dir
        self.backup_dir = backup_dir
        _validate_backup_dir(self.backup_dir, self.model_dir)

    def read_subbasins_from_fig(self, fig_file=None):
        fig_file = Path(fig_file) if fig_file else self.model_dir / "fig.fig"
        with open(fig_file, "r", encoding="ISO-8859-1") as f:
            return [
                int(line.strip().split()[3])
                for line in f
                if line.strip() and line.strip().startswith("subbasin")
            ]

    def read_parameter_cal(self, cal_file=None):
        cal_file = Path(cal_file) if cal_file else self.model_dir / "swat_pars.cal"
        return read_swat_parameter_cal(cal_file)

    def update_parameters(self, params, subs=None, hrus=None, show_progress=True):
        write_new_swat_files(
            params,
            source_dir=self.backup_dir,
            target_dir=self.model_dir,
            subs=subs,
            hrus=hrus,
            show_progress=show_progress,
        )

