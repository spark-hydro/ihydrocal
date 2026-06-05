from ihydrocal.core.config import init_project_config

config_file = init_project_config(
    # txtinout_dir="/home/spark/Documents/projects/watersheds/pecos/TxtInOut_v02/", # linux
    txtinout_dir=r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration\TxtInOut_p_29hru_t10m",
    overwrite=True,
)

print(f"Created config: {config_file}")