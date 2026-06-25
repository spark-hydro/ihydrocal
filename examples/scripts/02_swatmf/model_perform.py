from ihydrocal.models.swat_modflow import SWATModflowIO
from ihydrocal.analyzer import (
    plot_swatmf_streamflow,
    plot_swatmf_fdc,
    plot_swatmf_dtw,
    plot_swatmf_water_balance,
    plot_swatmf_performance_dashboard
)
from pathlib import Path
from matplotlib import pyplot as plt

if __name__ == "__main__":
    model_dir = Path(r"C:\Users\spark\Documents\projects\watersheds\kangwei\calibration\calibration\ys_zon_rw_glm") 
    save_path_fdc= model_dir / "figs01" /"fdc.png"
    save_path_water_balance= model_dir / "figs01" / "water_balance.png"
    save_path_stf = model_dir / "figs01" / "stf.png"
    save_path_dtw = model_dir / "figs01" / "dtw.png"
    m = SWATModflowIO(model_dir)

    stf = m.get_streamflow_sim_obs(
        "stf_day.obd.csv", obs_col="sub001", 
        subbasin=1, 
        )
    pcp = m.get_precip(subbasin=1)
    gw_sim = m.get_dtw_sim()
    print(gw_sim.head())
    gw_obs = m.get_dtw_obs()
    print(gw_obs.head())
    wb = m.get_water_balance()

    plot_swatmf_streamflow(stf, obs_col="sub001", 
                           precip_df=pcp, 
                        save_path=save_path_stf,
                        # aggregate="monthly",
                        obs_line=False,)
    plot_swatmf_fdc(stf, obs_col="sub001", save_path=save_path_fdc)
    plot_swatmf_dtw(
        gw_sim, "sim_g11733lyr1", 
        gw_obs, "dtw11733", precip_df=pcp, aggregate="monthly", 
        save_path=save_path_dtw)
    plot_swatmf_water_balance(wb, timestep="month", save_path=save_path_water_balance)
    plot_swatmf_performance_dashboard(
        streamflow_df=stf,
        streamflow_obs_col="sub001",
        water_balance_df=wb,
        gw_sim_df=gw_sim,
        gw_obs_df=gw_obs,
        gw_pairs=[("sim_g11733lyr1", "dtw11733")],
        precip_df=pcp,
        figsize=(14, 10),
        save_path=model_dir / "figs01" / "performance_dashboard.png"
    )

    from ihydrocal.analyzer import plot_swatmf_performance_dashboard_subfigures

    fig, axes, results = plot_swatmf_performance_dashboard_subfigures(
        streamflow_df=stf,
        streamflow_obs_col="sub001",
        water_balance_df=wb,
        gw_sim_df=gw_sim,
        gw_obs_df=gw_obs,
        gw_pairs=[("sim_g11733lyr1", "dtw11733")],
        aggregate="monthly",              # optional
        water_balance_timestep="month",
        figsize=(10, 10),
        title="SWAT-MODFLOW Model Performance",
        save_path=model_dir / "figs01" / "performance_dashboard02.png"
    )

    plt.show()