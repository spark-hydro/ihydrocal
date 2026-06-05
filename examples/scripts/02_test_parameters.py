from pathlib import Path

from ihydrocal.core.config import load_config
from ihydrocal.models.swatplus_gwflow.parameters import (
    get_active_parameters, write_calibration_cal, write_calibration_template
)

def main():
    config_file = Path(
        r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration\config\setup_swatplus.yml"
    )

    cfg = load_config(config_file)

    parameter_db_name = cfg["input_files"]["swatplus"]["parameter_databases"][0]
    parameter_db = cfg["config_dir"] / parameter_db_name

    active = get_active_parameters(parameter_db)

    model_dir = cfg["paths"]["workspace_dir"] / "main"

    cal_file = model_dir / "calibration.cal"
    tpl_file = model_dir / "calibration.cal.tpl"

    write_calibration_cal(active, cal_file)
    write_calibration_template(active, cal_file, tpl_file)

    print(f"Created calibration file: {cal_file}")
    print(f"Created template file: {tpl_file}")


if __name__ == "__main__":
    main()
