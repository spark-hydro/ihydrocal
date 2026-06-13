from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

from ihydrocal.analyzer.hydrograph import plot_simulated_discharge_comparison, plot_simulated_fdc_comparison
from ihydrocal.core.config import load_config
from ihydrocal.models.swatplus_gwflow.outputs import extract_swatplus_channel_output_long


def main():

    config_file = Path(
        r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration_v03\config\setup_swatplus.yml"
    )

    cfg = load_config(config_file)
    config_dir = cfg["config_dir"]
    channel_cfg = cfg["outputs"]["swatplus"]["channel"]
    workspace_dir = cfg["paths"]["workspace_dir"]

    base_channel_output = workspace_dir / "main_pre_cali" / "channel_sdmorph_day.txt"
    base_outlet_csv = workspace_dir / "scenario_compare" / "base_outlet_flo_out.csv"
    # extract_swatplus_channel_output_long(
    #     output_file=base_channel_output,
    #     output_csv=base_outlet_csv,
    #     value_col="flo_out",
    #     # cha_ids=channel_cfg["cha_ids"],
    #     cha_ids=[309],  # outlet only
    #     id_col=channel_cfg["id_col"],
    #     chunksize=200_000,
    # )

    scenario_channel_output = workspace_dir / "pecos_rw_swp" / "channel_sdmorph_day.txt"
    scenario_outlet_csv = workspace_dir / "scenario_compare" / "recall_outlet_flo_out.csv"
    # extract_swatplus_channel_output_long(
    #     output_file=scenario_channel_output,
    #     output_csv=scenario_outlet_csv,
    #     value_col="flo_out",
    #     # cha_ids=channel_cfg["cha_ids"],
    #     cha_ids=[309],
    #     id_col=channel_cfg["id_col"],
    #     chunksize=200_000,
    # )

    base_df = pd.read_csv(base_outlet_csv, parse_dates=["date"])
    recall_df = pd.read_csv(scenario_outlet_csv, parse_dates=["date"])
    # print(base_df.head())
    # print(recall_df.head())

    
    fig, axes, comparison_df = plot_simulated_discharge_comparison(
        base_df=base_df,
        scenario_df=recall_df,
        base_sim_col="simulated",
        scenario_sim_col="simulated",
        date_col="date",
        base_label="Base model",
        scenario_label="Recall point-source scenario",
        title="Outlet discharge comparison: base vs recall point-source",
        plot_difference=True,
        save_path=workspace_dir / "scenario_compare" / "outlet_base_vs_recall_hydrograph.png",
    )
    print(comparison_df)



    # fig, ax, fdc_df = plot_simulated_fdc_comparison(
    #     base_df=base_df,
    #     scenario_df=recall_df,
    #     base_sim_col="simulated",
    #     scenario_sim_col="simulated",
    #     date_col="date",
    #     base_label="Base model",
    #     scenario_label="Recall point-source scenario",
    #     title="Outlet FDC comparison: base vs recall point-source",
    #     save_path=workspace_dir / "figures" / "outlet_base_vs_recall_fdc.png",
    # )



if __name__ == "__main__":
    main()
