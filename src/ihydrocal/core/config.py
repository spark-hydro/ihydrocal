from pathlib import Path
from typing import Any

import yaml


def load_config(config_file: str | Path, validate: bool = True) -> dict[str, Any]:
    """
    Load an iHydroCal YAML configuration file.
    """
    config_file = Path(config_file).expanduser().resolve()

    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    with open(config_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if config is None:
        raise ValueError(f"Config file is empty: {config_file}")

    if validate:
        validate_config(config)

    config = resolve_config_paths(config)

    # Store config location for resolving repo-level paths
    config["config_file"] = config_file
    config["config_dir"] = config_file.parent
    config["repo_dir"] = config_file.parent.parent

    return config


def validate_config(config: dict[str, Any]) -> None:
    """
    Validate required sections and fields in an iHydroCal config dictionary.
    """
    required_sections = [
        "project",
        "paths",
        "simulation",
        "input_files",
        "calibration",
        "pest",
        "run_options",
        "binaries",
    ]

    missing_sections = [section for section in required_sections if section not in config]

    if missing_sections:
        raise KeyError(
            "Missing required config section(s): " + ", ".join(missing_sections)
        )

    required_fields = {
        "project": ["name", "model_type"],
        "paths": ["project_dir", "txtinout_dir", "workspace_dir", "swat_exe"],
        "simulation": ["start_date", "end_date", "warmup_years"],
        "pest": ["control_file", "model_command", "noptmax"],
        "binaries": ["bin_dir", "copy_to_model", "files"],
    }

    for section, fields in required_fields.items():
        missing_fields = [field for field in fields if field not in config[section]]

        if missing_fields:
            raise KeyError(
                f"Missing required field(s) in '{section}': "
                + ", ".join(missing_fields)
            )

    valid_model_types = [
        "swatplus",
        "swatplus_gwflow",
    ]

    model_type = config["project"]["model_type"]

    if model_type not in valid_model_types:
        raise ValueError(
            f"Invalid model_type: {model_type}. "
            f"Valid options are: {', '.join(valid_model_types)}"
        )


def resolve_config_paths(config: dict[str, Any]) -> dict[str, Any]:
    """
    Resolve important paths in the config dictionary.

    If workspace_dir is null, use:
        project_dir / "ihydrocal_workspace"
    """
    paths = config["paths"]

    project_dir = Path(paths["project_dir"]).expanduser().resolve()
    txtinout_dir = Path(paths["txtinout_dir"]).expanduser().resolve()

    workspace_dir = paths.get("workspace_dir")
    if workspace_dir is None:
        workspace_dir = project_dir / "ihydrocal_workspace"
    else:
        workspace_dir = Path(workspace_dir).expanduser().resolve()

    swat_exe = Path(paths["swat_exe"]).expanduser()

    config["paths"]["project_dir"] = project_dir
    config["paths"]["txtinout_dir"] = txtinout_dir
    config["paths"]["workspace_dir"] = workspace_dir
    config["paths"]["swat_exe"] = swat_exe

    return config


def print_config_summary(config: dict[str, Any]) -> None:
    """
    Print a short summary of the loaded iHydroCal configuration.
    """
    project = config["project"]
    paths = config["paths"]
    simulation = config["simulation"]

    print("iHydroCal configuration")
    print("-----------------------")
    print(f"Project name : {project['name']}")
    print(f"Model type   : {project['model_type']}")
    print(f"Project dir  : {paths['project_dir']}")
    print(f"TxtInOut dir : {paths['txtinout_dir']}")
    print(f"Workspace dir: {paths['workspace_dir']}")
    print(f"Simulation   : {simulation['start_date']} to {simulation['end_date']}")
    print(f"Warm-up years: {simulation['warmup_years']}")