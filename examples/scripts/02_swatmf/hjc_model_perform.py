from ihydrocal.analyzer.swat_modflow import plot_swatmf_case_study_dashboard
from ihydrocal.models.swat_modflow import SWATModflowIO
from ihydrocal.analyzer import (
    plot_swatmf_streamflow,
    plot_swatmf_fdc,
    plot_swatmf_dtw,
    plot_swatmf_water_balance,
    plot_swatmf_performance_dashboard,
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

    fig, axes, results = plot_swatmf_case_study_dashboard(
        streamflow_df=stf,
        streamflow_obs_col="sub001",
        water_balance_df=wb,
        gw_sim_df=gw_sim,
        gw_obs_df=gw_obs,
        gw_sim_col="sim_g11733lyr1",
        gw_obs_col="dtw11733",
        aggregate="monthly",
        water_balance_timestep="month",
        figsize=(10, 10),
        title=None,
        # title="Hwanjeon River SWAT-MODFLOW Model Performance",
        save_path=model_dir / "figs01" / "performance_dashboard.png"
    )

    plt.show()


