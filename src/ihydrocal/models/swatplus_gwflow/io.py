from pathlib import Path
import datetime as dt

import pandas as pd


class SWATPlusGwflowIO:
    """Reader utilities for SWAT+ and SWAT+gwflow model files."""

    def __init__(self, txtinout_dir):
        self.txtinout_dir = Path(txtinout_dir)

    def _path(self, filename):
        return self.txtinout_dir / filename

    def read_table(self, filename, skiprows=None, **kwargs):
        """Read a whitespace-delimited SWAT+ text table."""
        path = self._path(filename)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        return pd.read_csv(
            path,
            sep=r"\s+",
            skiprows=skiprows,
            **kwargs,
        )

    def read_time_sim(self):
        return self.read_table("time.sim", skiprows=1)

    def read_print_prt(self):
        return self.read_table("print.prt", skiprows=1)

    def define_sim_period(self):
        df_time = self.read_time_sim()
        df_prt = self.read_print_prt()

        skipyear = int(df_prt.loc[0, "nyskip"])
        yrc_start = int(df_time.loc[0, "yrc_start"])
        yrc_st_warmup = yrc_start + skipyear
        yrc_end = int(df_time.loc[0, "yrc_end"])
        start_day = int(df_time.loc[0, "day_start"])
        end_day = int(df_time.loc[0, "day_end"])

        stdate = dt.datetime(yrc_start, 1, 1) + dt.timedelta(start_day - 1)
        eddate = dt.datetime(yrc_end, 1, 1) + dt.timedelta(end_day - 1)
        stdate_warmup = dt.datetime(yrc_st_warmup, 1, 1) + dt.timedelta(start_day - 1)

        return {
            "start_date": stdate,
            "end_date": eddate,
            "warmup_start_date": stdate_warmup,
        }

    def read_channel_sd_day(self, flow_col="flo_out"):
        return self.read_table(
            "channel_sd_day.txt",
            skiprows=[0, 2],
            usecols=["gis_id", flow_col],
        )

    def read_channel_sdmorph_day(self, flow_col="flo_out"):
        return self.read_table(
            "channel_sdmorph_day.txt",
            skiprows=[0, 2],
            usecols=["gis_id", flow_col],
        )

    def read_channel_sd_mon(self, flow_col="flo_out"):
        return self.read_table(
            "channel_sd_mon.txt",
            skiprows=[0, 2],
            usecols=["gis_id", flow_col],
        )

    def read_channel_sdmorph_mon(self, flow_col="flo_out"):
        return self.read_table(
            "channel_sdmorph_mon.txt",
            skiprows=[0, 2],
            usecols=["gis_id", flow_col],
        )

    def read_basin_wb_mon(self):
        return self.read_table("basin_wb_mon.txt", skiprows=[0, 2])

    def read_basin_wb_yr(self):
        return self.read_table("basin_wb_yr.txt", skiprows=[0, 2])

    def read_gwflow_state_obs_head(self):
        path = self._path("gwflow_state_obs_head")

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        with open(path, "r") as f:
            lines = f.readlines()

        grid_ids = lines[1].split()[1:]

        df = pd.read_csv(
            path,
            skiprows=3,
            sep=r"\s+",
            header=None,
        )

        df = df.iloc[:, 2:]
        df.columns = grid_ids

        return df


    def read_channel_flow_day_wide(
        self,
        filename="channel_sdmorph_day.txt",
        flow_col="flo_out",
        id_col="gis_id",
        prefix="ch",
    ):
        """Read channel flow output and return wide dataframe.

        Output format:
            date        ch001     ch002     ch003 ...
            2011-01-01  0.03729   0.01930   ...
        """
        df = self.read_table(
            filename,
            skiprows=[0, 2],
            usecols=["yr", "mon", "day", id_col, flow_col],
        )
        df["date"] = pd.to_datetime(
            {
                "year": df["yr"],
                "month": df["mon"],
                "day": df["day"],
            }
        )
        wide = df.pivot(
            index="date",
            columns=id_col,
            values=flow_col,
        )
        wide.columns = [f"{prefix}{int(c):03d}" for c in wide.columns]
        wide = wide.reset_index()
        return wide
    
    def read_observed_flow_wide(
        self,
        obs_file,
        site_channel_map,
        date_col="Date",
        site_col="site_no",
        flow_col="Q_cms",
        sim_flow_wide=None,
    ):
        """Read observed flow and optionally match with simulated channel flow.

        Parameters
        ----------
        obs_file : str or Path
            Observed flow CSV file.
        site_channel_map : dict
            Mapping between USGS site number and SWAT+ channel number.
            Example: {"08379500": 1, "08380000": 25}
        date_col : str
            Date column in observed data.
        site_col : str
            Site number column in observed data.
        flow_col : str
            Observed flow column.
        sim_flow_wide : pandas.DataFrame, optional
            Simulated flow dataframe from read_channel_flow().
            Must have columns like date, ch001, ch002, ...

        Returns
        -------
        pandas.DataFrame
            Wide dataframe with date, observed flow, and optionally simulated flow.
        """

        obs = pd.read_csv(
            obs_file,
            na_values=["NA", "", -999],
            dtype={site_col: str},
        )

        obs[date_col] = pd.to_datetime(obs[date_col])

        site_ids = [str(site) for site in site_channel_map.keys()]

        obs = obs.loc[obs[site_col].isin(site_ids), [date_col, site_col, flow_col]]

        obs_wide = obs.pivot(
            index=date_col,
            columns=site_col,
            values=flow_col,
        )

        obs_wide.columns = [f"{site}_obs" for site in obs_wide.columns]
        obs_wide = obs_wide.reset_index()
        obs_wide = obs_wide.rename(columns={date_col: "date"})

        if sim_flow_wide is None:
            return obs_wide

        sim = sim_flow_wide.copy()
        sim["date"] = pd.to_datetime(sim["date"])

        sim_cols = ["date"]
        rename_cols = {}

        for site, channel in site_channel_map.items():
            ch_col = f"ch{int(channel):03d}"

            if ch_col in sim.columns:
                sim_cols.append(ch_col)
                rename_cols[ch_col] = f"ch{int(channel):03d}_sim"

        sim = sim[sim_cols].rename(columns=rename_cols)

        matched = pd.merge(
            obs_wide,
            sim,
            on="date",
            how="inner",
        )

        return matched
    

    def read_pcp_file(self, pcp_file, missing_value=-99):
        """Read one SWAT+ precipitation input file.

        Parameters
        ----------
        pcp_file : str or Path
            Path to a SWAT+ precipitation file (*.pcp).

        missing_value : int or float, default -99
            Missing data value used in the precipitation file.

        Returns
        -------
        pandas.DataFrame
            DataFrame with columns:
            date, precip

        Notes
        -----
        Expected SWAT+ pcp format:

            station_name: description
            nbyr  tstep  lat  lon  elev
            16      0  ...
            2010    1  0.000
            2010    2  0.000

        The second column is day of year.
        """

        pcp_file = Path(pcp_file)

        if not pcp_file.exists():
            raise FileNotFoundError(f"File not found: {pcp_file}")

        df = pd.read_csv(
            pcp_file,
            sep=r"\s+",
            skiprows=3,
            names=["year", "jday", "precip"],
            na_values=[missing_value],
        )

        df["date"] = pd.to_datetime(
            df["year"].astype(str),
            format="%Y",
        ) + pd.to_timedelta(df["jday"] - 1, unit="D")

        df = df[["date", "precip"]]

        return df


    def read_pcp_files_wide(
        self,
        pcp_dir=None,
        pattern="*.pcp",
        missing_value=-99,
    ):
        """Read multiple SWAT+ precipitation files and return a wide dataframe.

        Parameters
        ----------
        pcp_dir : str or Path, optional
            Directory containing *.pcp files.
            If None, use the model output/input directory assigned to this IO object.

        pattern : str, default "*.pcp"
            File pattern to search.

        missing_value : int or float, default -99
            Missing data value.

        Returns
        -------
        pandas.DataFrame
            Wide dataframe:

                date        station1    station2    station3
                2010-01-01  0.0         1.2         0.0

        Notes
        -----
        Column names are based on the pcp file names.
        """

        if pcp_dir is None:
            pcp_dir = self.txtinout_dir

        pcp_dir = Path(pcp_dir)

        files = sorted(pcp_dir.glob(pattern))

        if len(files) == 0:
            raise FileNotFoundError(f"No precipitation files found in: {pcp_dir}")

        wide_df = None

        for file in files:
            df = self.read_pcp_file(file, missing_value=missing_value)

            station_name = file.stem
            df = df.rename(columns={"precip": station_name})

            if wide_df is None:
                wide_df = df
            else:
                wide_df = pd.merge(
                    wide_df,
                    df,
                    on="date",
                    how="outer",
                )

        wide_df = wide_df.sort_values("date").reset_index(drop=True)

        return wide_df
    

    def read_channel_precip_depth_wide(
        self,
        filename="channel_sd_day.txt",
        id_col="gis_id",
        area_col="area",
        precip_col="precip",
        prefix="ch",
    ):
        """Read channel precipitation volume and convert m3 to mm.

        SWAT+ channel_sd_day.txt reports:
            area   : channel area, ha
            precip : precipitation volume on channel surface, m3

        Unit conversion:
            1 ha = 10,000 m2

            depth_m  = precip_m3 / (area_ha * 10000)
            depth_mm = depth_m * 1000

        Therefore:
            depth_mm = precip_m3 / area_ha * 0.1

        Returns
        -------
        pandas.DataFrame
            Wide dataframe:

            date        ch001_pcp_mm   ch002_pcp_mm   ch003_pcp_mm
            2011-01-01  4.03           4.03           4.03
        """

        df = self.read_table(
            filename,
            skiprows=[0, 2],
            usecols=["yr", "mon", "day", id_col, area_col, precip_col],
        )

        df["date"] = pd.to_datetime(
            {
                "year": df["yr"],
                "month": df["mon"],
                "day": df["day"],
            }
        )

        # Convert precipitation volume from m3 to depth in mm.
        # area is ha, so area_ha * 10000 gives m2.
        # depth_mm = precip_m3 / (area_ha * 10000) * 1000
        #          = precip_m3 / area_ha * 0.1
        df["pcp_mm"] = (df[precip_col] / df[area_col]) * 0.1

        wide = df.pivot(
            index="date",
            columns=id_col,
            values="pcp_mm",
        )

        wide.columns = [f"{prefix}{int(c):03d}_pcp_mm" for c in wide.columns]
        wide = wide.reset_index()

        return wide