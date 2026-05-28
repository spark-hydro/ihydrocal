import platform
import shutil
from pathlib import Path
from typing import Any

from tqdm import tqdm

from ihydrocal.core.config import load_config


def get_os_name() -> str:
    """
    Return normalized operating system name.
    """
    system = platform.system().lower()

    if system == "windows":
        return "windows"
    if system == "linux":
        return "linux"
    if system == "darwin":
        return "macos"

    raise OSError(f"Unsupported operating system: {system}")


def get_binary_name(name: str) -> str:
    """
    Add OS-specific binary extension if needed.
    """
    if get_os_name() == "windows" and not name.endswith(".exe"):
        return f"{name}.exe"

    return name


def create_workspace(config: dict[str, Any]) -> Path:
    """
    Create the iHydroCal workspace directory if it does not exist.
    """
    workspace_dir = config["paths"]["workspace_dir"]
    workspace_dir.mkdir(parents=True, exist_ok=True)

    return workspace_dir


def copy_model_to_workspace(config: dict[str, Any]) -> Path:
    """
    Copy the original model directory into the iHydroCal workspace.

    The copied model is stored in:
        workspace_dir / "model"
    """
    txtinout_dir = config["paths"]["txtinout_dir"]
    workspace_dir = config["paths"]["workspace_dir"]
    model_dir = workspace_dir / "model"

    overwrite = config["run_options"].get("overwrite_workspace", False)

    if not txtinout_dir.exists():
        raise FileNotFoundError(f"TxtInOut directory not found: {txtinout_dir}")

    if model_dir.exists():
        if overwrite:
            shutil.rmtree(model_dir)
        else:
            raise FileExistsError(
                f"Model workspace already exists: {model_dir}\n"
                "Set overwrite_workspace: true in the YAML file to overwrite it."
            )

    model_dir.mkdir(parents=True, exist_ok=True)

    files_to_copy = [file for file in txtinout_dir.rglob("*") if file.is_file()]

    for src_file in tqdm(files_to_copy, desc="Copying model files", unit="file"):
        relative_path = src_file.relative_to(txtinout_dir)
        dst_file = model_dir / relative_path

        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)

    return model_dir


def copy_binaries_to_model(config: dict[str, Any], model_dir: Path) -> None:
    """
    Copy OS-specific binaries into the copied model folder.
    """
    if not config["binaries"].get("copy_to_model", True):
        return

    os_name = get_os_name()

    bin_root = Path(config["binaries"].get("bin_dir", "bin")).expanduser()

    if not bin_root.is_absolute():
        bin_root = config["repo_dir"] / bin_root

    bin_dir = bin_root / os_name

    if not bin_dir.exists():
        raise FileNotFoundError(f"Binary directory not found: {bin_dir}")

    binary_files = config["binaries"].get("files", [])

    for binary in tqdm(binary_files, desc="Copying binaries", unit="file"):
        binary_name = get_binary_name(binary)

        src_file = bin_dir / binary_name
        dst_file = model_dir / binary_name

        if not src_file.exists():
            raise FileNotFoundError(f"Binary file not found: {src_file}")

        shutil.copy2(src_file, dst_file)


def setup_workspace(config_file: str | Path) -> tuple[dict[str, Any], Path, Path]:
    """
    Set up an iHydroCal workspace from a YAML configuration file.
    """
    config = load_config(config_file)

    workspace_dir = create_workspace(config)
    model_dir = copy_model_to_workspace(config)
    copy_binaries_to_model(config, model_dir)

    return config, workspace_dir, model_dir