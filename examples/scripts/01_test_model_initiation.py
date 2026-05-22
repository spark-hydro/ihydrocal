import os
# from turtle import pd
import pandas as pd
import ihydrocal as ihc
import matplotlib.pyplot as plt

from ihydrocal.analyzer.precipitation import plot_precip_timeseries


# def main():
#     model_dir = r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\america-pecos\Scenarios\Default\TxtInOut_v02"
#     model = ihc.create_model(
#         "swatplus_gwflow",
#         model_dir=model_dir
#     )
#     print(model.validate())

#     sim_flow  = model.io.read_channel_flow_day_wide()

#     site_channel_map = {
#         "08447300": 447,
#         "08412500": 281,
#     }

#     matched_df = model.io.read_observed_flow_wide(
#         obs_file=model_dir + r"\data_dailyvalues_Pecos.csv",
#         site_channel_map=site_channel_map,
#         sim_flow_wide=sim_flow,
#     )

#     print(matched_df.head())


def main():
    from ihydrocal.analyzer import plot_hydrograph

    model_dir = r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\america-pecos\Scenarios\Default\TxtInOut_v02"
    model = ihc.create_model(
        "swatplus_gwflow",
        model_dir=model_dir
    )

    sim_flow  = model.io.read_channel_flow_day_wide()
    site_channel_map = {
        "08447300": 447,
        "08412500": 281,
    }

    matched_df = model.io.read_observed_flow_wide(
        obs_file=model_dir + r"\data_dailyvalues_Pecos.csv",
        site_channel_map=site_channel_map,
        sim_flow_wide=sim_flow,
    )


    for site_no, channel in site_channel_map.items():
        obs_col = f"{site_no}_obs"
        sim_col = f"ch{channel:03d}_sim"

        fig, ax, metrics = plot_hydrograph(
            matched_df,
            obs_col=obs_col,
            sim_col=sim_col,
            title=f"USGS {site_no} vs SWAT+ Channel {channel:03d}",
            # save_path=f"outputs/hydrograph_{site_no}_ch{channel:03d}.png",
        )
        plt.show()

        print(site_no, sim_col, metrics)


def precip():
    model_dir = r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\america-pecos\Scenarios\Default\TxtInOut_v02"
    model = ihc.create_model(
        "swatplus_gwflow",
        model_dir=model_dir
    )

    pcp_df = model.io.read_pcp_files_wide(
        pcp_dir=model_dir
    )

    pcp_df.head()    
    fig, ax = plot_precip_timeseries(
        pcp_df,
        title="Precipitation Variation Across PCP Stations",
    )
    plt.show()


def main_precip():
    from ihydrocal.analyzer import plot_hydrograph_with_precip
    model_dir = r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\america-pecos\Scenarios\Default\TxtInOut_v02"
    model = ihc.create_model(
        "swatplus_gwflow",
        model_dir=model_dir
    )

    sim_flow  = model.io.read_channel_flow_day_wide()
    site_channel_map = {
        "08447300": 447,
        "08412500": 281,
    }

    matched_df = model.io.read_observed_flow_wide(
        obs_file=model_dir + r"\data_dailyvalues_Pecos.csv",
        site_channel_map=site_channel_map,
        sim_flow_wide=sim_flow,
    )


    pcp_df = model.io.read_channel_precip_depth_wide()

    matched_with_pcp = matched_df.merge(
        pcp_df,
        on="date",
        how="left",
    )


    fig, axes, metrics = plot_hydrograph_with_precip(
        matched_with_pcp,
        obs_col="08447300_obs",
        sim_col="ch447_sim",
        pcp_col="ch447_pcp_mm",
        title="USGS 08447300 vs SWAT+ Channel 447",
    )
    plt.show()


def main_precip_mutiple_sites():
    from ihydrocal.analyzer import plot_hydrograph_with_precip
    model_dir = r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\america-pecos\Scenarios\Default\TxtInOut_v02"
    model = ihc.create_model(
        "swatplus_gwflow",
        model_dir=model_dir
    )
    sim_flow  = model.io.read_channel_flow_day_wide()
    site_channel_map = {
        "08447300": 447,
        "08412500": 281,
    }
    matched_df = model.io.read_observed_flow_wide(
        obs_file=model_dir + r"\data_dailyvalues_Pecos.csv",
        site_channel_map=site_channel_map,
        sim_flow_wide=sim_flow,
    )
    pcp_df = model.io.read_channel_precip_depth_wide()
    matched_with_pcp = matched_df.merge(
        pcp_df,
        on="date",
        how="left",
    )

    for site_no, channel in site_channel_map.items():
        obs_col = f"{site_no}_obs"
        sim_col = f"ch{channel:03d}_sim"
        pcp_col = f"ch{channel:03d}_pcp_mm"

        fig, axes, metrics = plot_hydrograph_with_precip(
            matched_with_pcp,
            obs_col=obs_col,
            sim_col=sim_col,
            pcp_col=pcp_col,
            title=f"USGS {site_no} vs SWAT+ Channel {channel:03d}",
            save_path=f"outputs/hydrograph_pcp_{site_no}_ch{channel:03d}.png",
        )

        print(site_no, f"ch{channel:03d}", metrics)
        plt.show()

def main_diagnostics():
    from ihydrocal.analyzer import plot_discharge_diagnostics


    model_dir = r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\america-pecos\Scenarios\Default\TxtInOut_v02"
    model = ihc.create_model(
        "swatplus_gwflow",
        model_dir=model_dir
    )
    sim_flow  = model.io.read_channel_flow_day_wide()
    site_channel_map = {
        "08447300": 447,
        "08412500": 281,
    }
    matched_df = model.io.read_observed_flow_wide(
        obs_file=model_dir + r"\data_dailyvalues_Pecos.csv",
        site_channel_map=site_channel_map,
        sim_flow_wide=sim_flow,
    )
    pcp_df = model.io.read_channel_precip_depth_wide()
    matched_with_pcp = matched_df.merge(
        pcp_df,
        on="date",
        how="left",
    )



    results = plot_discharge_diagnostics(
        matched_with_pcp,
        obs_col="08447300_obs",
        sim_col="ch447_sim",
        pcp_col="ch447_pcp_mm",
        site_name="USGS08447300_ch447",
        save_dir="outputs/diagnostics",
    )
    


if __name__ == "__main__":
    main_diagnostics()