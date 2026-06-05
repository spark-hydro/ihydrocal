from pathlib import Path

from ihydrocal.core.config import (
    init_project_config,
    load_config,
    print_config_summary,
)
from ihydrocal.core.mapping import update_ids_from_mapping
from ihydrocal.core.pest import create_pest_control_file
from ihydrocal.core.workspace import setup_workspace
from ihydrocal.models.swatplus_gwflow.observations import (
    build_streamflow_observation_table, 
    create_streamflow_simulation_table,
    make_channel_obsname,
    prepare_streamflow_instruction_files, 
    read_channel_gage_mapping, 
    read_streamflow_observations_long,
    write_simulation_dat,
    write_simulation_instruction_file
)
from ihydrocal.models.swatplus_gwflow.outputs import extract_swatplus_channel_output_long
from ihydrocal.models.swatplus_gwflow.parameters import (
    get_active_parameters,
    write_calibration_cal,
    write_calibration_template,
)


import pandas as pd


TXTINOUT_DIR = Path(
    r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration\TxtInOut_p_29hru_t10m"
)

CONFIG_FILE = Path(
    r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration\config\setup_swatplus.yml"
)


def create_config(overwrite: bool = False):
    config_file = init_project_config(
        txtinout_dir=TXTINOUT_DIR,
        overwrite=overwrite,
    )

    print(f"Created config: {config_file}")


def setup_calibration_files(cfg, model_dir: Path):
    parameter_db_name = cfg["input_files"]["swatplus"]["parameter_databases"][0]
    parameter_db = cfg["config_dir"] / parameter_db_name

    active = get_active_parameters(parameter_db)

    cal_file = model_dir / "calibration.cal"
    tpl_file = model_dir / "calibration.cal.tpl"

    write_calibration_cal(active, cal_file)
    write_calibration_template(active, cal_file, tpl_file)

    print(f"Created calibration file: {cal_file}")
    print(f"Created template file: {tpl_file}")
    print(f"Number of active parameters: {len(active)}")


def setup_workflow():
    cfg, workspace_dir, model_dir = setup_workspace(CONFIG_FILE)

    print_config_summary(cfg)
    print(f"Workspace ready: {workspace_dir}")
    print(f"Model ready: {model_dir}")

    setup_calibration_files(cfg, model_dir)


def mapping_test():

    config_file = Path(
        r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration\config\setup_swatplus.yml"
    )
    mapping_file = Path(
        r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration\channels_gages.csv"
    )

    cha_ids = update_ids_from_mapping(
        config_file=config_file,
        mapping_file=mapping_file,
        id_col="channel_id",
        yaml_key="cha_ids",
    )
    print(f"Updated cha_ids: {cha_ids}")
    print(f"Number of channel IDs: {len(cha_ids)}")


def stf_extractor():
    config_file = Path(
        r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration\config\setup_swatplus.yml"
    )

    cfg = load_config(config_file)

    channel_cfg = cfg["outputs"]["swatplus"]["channel"]

    model_dir = cfg["paths"]["workspace_dir"] / "main"
    output_file = model_dir / channel_cfg["file"]

    cha_ids = channel_cfg["cha_ids"]
    id_col = channel_cfg["id_col"]

    output_csv = model_dir / "cha_flo_out_day.csv"

    extract_swatplus_channel_output_long(
        output_file=output_file,
        output_csv=output_csv,
        value_col="flo_out",
        cha_ids=cha_ids,
        id_col=id_col,
        chunksize=500_000,
    )

    print(f"Created extracted output: {output_csv}")    


def create_sim_test():

    config_dir = Path(
        r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration"
    )

    # obs_long = read_streamflow_observations_long(config_dir / "stf_day.obd.csv")

    # obs_table = build_streamflow_observation_table(obs_long, mapping)

    # print(obs_table.head())
    # print(obs_table.shape)
    # print(obs_table["obsname"].head())

    model_dir = Path(
        r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration\ihydrocal_workspace\main"
    )

    obs_long = read_streamflow_observations_long(config_dir / "stf_day.obd.csv")
    mapping = read_channel_gage_mapping(config_dir / "channels_gages.csv", site_col="SITENO")
    # mapping = read_channel_gage_mapping(config_dir / "channels_gages.csv")
    obs_table = build_streamflow_observation_table(obs_long, mapping)

    sim_table = create_streamflow_simulation_table(
        obs_table=obs_table,
        sim_long_file=model_dir / "cha_flo_out_day.csv",
    )

    sim_csv = write_simulation_dat(
        sim_table=sim_table,
        output_file=model_dir / "sim_stf_day.dat",
    )

    print(f"Created simulation DAT: {sim_csv}")


def ins_test():
    model_dir = Path(
        r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration\ihydrocal_workspace\main"
    )
    config_dir = Path(
        r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration"
    )
    ins_file = write_simulation_instruction_file(
        sim_dat=model_dir / "sim_stf_day.dat",
        ins_file=model_dir / "sim_stf_day.dat.ins",
    )

    print(f"Created instruction file: {ins_file}")


    prepare_streamflow_instruction_files(
        site_col="SITENO",
        obs_file=config_dir / "stf_day.obd.csv",
        mapping_file=config_dir / "channels_gages.csv",
        sim_file=model_dir / "cha_flo_out_day.csv",
        output_dat=model_dir / "sim_stf_day.dat",
        output_ins=model_dir / "sim_stf_day.dat.ins",
    )

def control_file_test():
    model_dir = Path(
        r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration\ihydrocal_workspace\main"
    )
    config_file = Path(
        r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration\config\setup_swatplus.yml"
    )
    cfg = load_config(config_file)



    pst_file = create_pest_control_file(
        cfg,
        model_dir=model_dir,
        pst_file=cfg["pest"]["control_file"],
        model_command=cfg["pest"]["model_command"],
        noptmax=cfg["pest"]["noptmax"],
    )

    print(f"Created PEST control file: {pst_file}")





if __name__ == "__main__":
    # Step 00: run this once first, then edit YAML and parameter database.
    # create_config(overwrite=False)

    # Step 01+: after editing config files, run this.
    # setup_workflow()
    
    #### For testing the mapping function separately
    # mapping_test()

    #### For testing the output extractor separately
    control_file_test()