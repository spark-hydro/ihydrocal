from ihydrocal.core.config import init_project_config

config_file = init_project_config(
    txtinout_dir="/home/spark/Documents/projects/watersheds/pecos/TxtInOut_v02/",
    overwrite=True,
)

print(f"Created config: {config_file}")