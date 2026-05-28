from pathlib import Path

from ihydrocal.models.swatplus_gwflow import read_parameter_database

def main():
    script_dir = Path(__file__).resolve().parent
    config_file = script_dir / "../../config/setup_swatplus.yml"

    script_dir = Path(__file__).resolve().parent
    parameter_db = script_dir / "../../config/swatp_pars.db.csv"

    df = read_parameter_database(parameter_db)

    print(df.head())
    print(df.columns)
    print(df.shape)

if __name__ == "__main__":
    main()
