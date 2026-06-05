from pathlib import Path
import re

import pandas as pd


def read_ids_from_mapping(
    mapping_file: str | Path,
    id_col: str,
    sort_ids: bool = True,
) -> list[int]:
    """
    Read unique integer IDs from a mapping CSV file.

    Parameters
    ----------
    mapping_file : str or Path
        Path to the mapping CSV file.

    id_col : str
        Column name containing IDs to read.

    sort_ids : bool
        If True, return sorted IDs.

    Returns
    -------
    list[int]
        Unique IDs from the selected column.
    """
    mapping_file = Path(mapping_file)

    if not mapping_file.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_file}")

    df = pd.read_csv(mapping_file)

    if id_col not in df.columns:
        raise KeyError(
            f"Column '{id_col}' not found in {mapping_file}. "
            f"Available columns: {list(df.columns)}"
        )

    ids = (
        pd.to_numeric(df[id_col], errors="coerce")
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    if sort_ids:
        ids = sorted(ids)

    return ids


def update_yaml_list_value(
    config_file: str | Path,
    key: str,
    values: list[int],
) -> Path:
    """
    Update a simple YAML list line while preserving comments.

    Example:
        cha_ids: []  ->  cha_ids: [1, 2, 3]
    """
    config_file = Path(config_file)

    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    text = config_file.read_text(encoding="utf-8")

    values_text = "[" + ", ".join(str(v) for v in values) + "]"

    pattern = rf"^(\s*{key}\s*:\s*).*$"
    replacement = rf"\g<1>{values_text}"

    new_text, n = re.subn(
        pattern,
        replacement,
        text,
        flags=re.MULTILINE,
    )

    if n == 0:
        raise KeyError(f"Key '{key}' not found in config file: {config_file}")

    config_file.write_text(new_text, encoding="utf-8")

    return config_file


def update_ids_from_mapping(
    config_file: str | Path,
    mapping_file: str | Path,
    id_col: str,
    yaml_key: str,
    sort_ids: bool = True,
) -> list[int]:
    """
    Read IDs from a mapping CSV file and update a YAML list value.

    Example:
        channel_id column -> cha_ids in setup_swatplus.yml
    Usages:
    >>> update_ids_from_mapping(
    ...     config_file="config/setup_swatplus.yml",
    ...     mapping_file="config/channels_gages.csv",
    ...     id_col="channel_id",
    ...     yaml_key="cha_ids"
    ... )
    
    >>> update_ids_from_mapping(..., id_col="hru_id", yaml_key="hru_ids")
    >>> update_ids_from_mapping(..., id_col="grid_id", yaml_key="grid_ids")
    """
    
    ids = read_ids_from_mapping(
        mapping_file=mapping_file,
        id_col=id_col,
        sort_ids=sort_ids,
    )

    update_yaml_list_value(
        config_file=config_file,
        key=yaml_key,
        values=ids,
    )

    return ids