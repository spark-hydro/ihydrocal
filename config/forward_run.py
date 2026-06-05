from pathlib import Path
import platform
import subprocess
import sys

from ihydrocal.core.config import load_config
from ihydrocal.models.swatplus_gwflow.outputs import (
    extract_swatplus_channel_output_long,
)
from ihydrocal.models.swatplus_gwflow.observations import (
    prepare_streamflow_instruction_files,
)


def get_swat_executable(model_dir: Path, exe_name: str = "swatplus") -> Path:
    """
    Find the SWAT+ executable in the current model directory.

    On Windows, use:
        swatplus.exe

    On Linux/macOS, use:
        swatplus

    If the YAML gives a different executable name, this function can also
    use that basename.
    """
    system = platform.system().lower()

    exe_name = Path(exe_name).name

    if system == "windows" and not exe_name.endswith(".exe"):
        exe_name = f"{exe_name}.exe"

    exe_path = model_dir / exe_name

    if not exe_path.exists():
        raise FileNotFoundError(f"SWAT+ executable not found: {exe_path}")

    return exe_path


def run_swatplus(model_dir: Path, exe_path: Path) -> None:
    """
    Run SWAT+ inside the copied model directory.
    """
    print(f"Running SWAT+: {exe_path.name}")

    result = subprocess.run(
        [str(exe_path)],
        cwd=model_dir,
        capture_output=True,
        text=True,
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            f"SWAT+ failed with return code {result.returncode}"
        )


def main():
    """
    Forward run for iHydroCal + PEST++.

    This script:
    1. Loads the project YAML.
    2. Runs SWAT+ in ihydrocal_workspace/main.
    3. Extracts selected channel simulated streamflow from channel_sd_day.txt.
    4. Creates sim_stf_day.dat for PEST/PEST++.
    """
    model_dir = Path(__file__).resolve().parent

    # main folder:
    #   project/ihydrocal_workspace/main
    #
    # config folder:
    #   project/config/setup_swatplus.yml
    config_file = model_dir.parents[1] / "config" / "setup_swatplus.yml"

    cfg = load_config(config_file)
    config_dir = cfg["config_dir"]

    channel_cfg = cfg["outputs"]["swatplus"]["channel"]

    swat_exe_name = Path(cfg["paths"].get("swat_exe", "swatplus")).name
    exe_path = get_swat_executable(model_dir, swat_exe_name)

    # ------------------------------------------------------------------
    # 1. Run SWAT+
    # ------------------------------------------------------------------
    run_swatplus(model_dir, exe_path)

    # ------------------------------------------------------------------
    # 2. Extract selected channel output from large SWAT+ output file.
    #    This creates long-format cha_flo_out_day.csv:
    #
    #        date, channel_id, simulated
    # ------------------------------------------------------------------
    swat_output_file = model_dir / channel_cfg["file"]

    sim_channel_file = model_dir / "cha_flo_out_day.csv"

    extract_swatplus_channel_output_long(
        output_file=swat_output_file,
        output_csv=sim_channel_file,
        value_col=channel_cfg["variables"][0],   # e.g., flo_out
        cha_ids=channel_cfg["cha_ids"],
        id_col=channel_cfg["id_col"],            # e.g., gis_id
    )

    # ------------------------------------------------------------------
    # 3. Match simulated values with observed streamflow locations/dates.
    #    This creates:
    #
    #        sim_stf_day.dat
    #
    #    The instruction file is also regenerated. This is okay, but later
    #    we can avoid recreating the .ins file every run if desired.
    # ------------------------------------------------------------------
    prepare_streamflow_instruction_files(
        site_col="SITENO",
        obs_file=config_dir / "stf_day.obd.csv",
        mapping_file=config_dir / "channels_gages.csv",
        sim_file=sim_channel_file,
        output_dat=model_dir / "sim_stf_day.dat",
    )

    print("Forward run completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"Forward run failed: {err}", file=sys.stderr)
        raise