from pathlib import Path
from typing import Any
import shutil
import re
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


def init_project_config(
    txtinout_dir: str | Path,
    project_dir: str | Path | None = None,
    template_config: str | Path | None = None,
    output_config: str | Path | None = None,
    parameter_databases: list[str | Path] | None = None,
    overwrite: bool = False,
) -> Path:
    """
    Copy the default YAML config template and update project paths.

    This preserves comments because it edits the file as text instead of
    loading/dumping YAML.
    """
    txtinout_dir = Path(txtinout_dir).expanduser().resolve()

    if not txtinout_dir.exists():
        raise FileNotFoundError(f"TxtInOut directory not found: {txtinout_dir}")

    if project_dir is None:
        project_dir = txtinout_dir.parent
    else:
        project_dir = Path(project_dir).expanduser().resolve()

    if template_config is None:
        repo_dir = Path(__file__).resolve().parents[3]
        template_config = repo_dir / "config" / "setup_swatplus.yml"
    else:
        template_config = Path(template_config).expanduser().resolve()

    if not template_config.exists():
        raise FileNotFoundError(f"Template config not found: {template_config}")

    if output_config is None:
        output_config = project_dir / "config" / "setup_swatplus.yml"
    else:
        output_config = Path(output_config).expanduser().resolve()

    if output_config.exists() and not overwrite:
        raise FileExistsError(
            f"Config file already exists: {output_config}\n"
            "Use overwrite=True to replace it."
        )

    output_config.parent.mkdir(parents=True, exist_ok=True)

    text = template_config.read_text(encoding="utf-8")

    # Use forward slashes for YAML portability
    project_dir_str = project_dir.as_posix()
    txtinout_dir_str = txtinout_dir.as_posix()

    text = re.sub(
        r"^\s*project_dir\s*:.*$",
        f"  project_dir: {project_dir_str}",
        text,
        flags=re.MULTILINE,
    )

    text = re.sub(
        r"^\s*txtinout_dir\s*:.*$",
        f"  txtinout_dir: {txtinout_dir_str}",
        text,
        flags=re.MULTILINE,
    )

    text = re.sub(
        r"^\s*workspace_dir\s*:.*$",
        "  workspace_dir: null",
        text,
        flags=re.MULTILINE,
    )

    output_config.write_text(text, encoding="utf-8")

    # Copy default parameter database files from repo config folder
    repo_config_dir = template_config.parent

    parameter_db_files = list(repo_config_dir.glob("*.db.csv"))

    for parameter_db in parameter_db_files:
        dst_file = output_config.parent / parameter_db.name
        shutil.copy2(parameter_db, dst_file)
        print(f"Parameter database copied to: {dst_file}")

    print(f"Config template created: {output_config}")
    print(f"project_dir updated to: {project_dir_str}")
    print(f"txtinout_dir updated to: {txtinout_dir_str}")
    print("workspace_dir set to: null")

    return output_config