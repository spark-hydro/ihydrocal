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