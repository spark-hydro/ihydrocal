from pathlib import Path
import datetime as dt

import numpy as np
import pandas as pd


class SWATModflowIO:
    """Reader utilities for SWAT-MODFLOW model output files."""

    def __init__(self, model_dir):
        self.model_dir = Path(model_dir)
        self._period = None

    def _path(self, filename):
        path = self.model_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return path

    def read_file_cio_period(self):
        """Read simulation dates and output interval from SWAT file.cio."""

        path = self._path("file.cio")

        with open(path, "r") as f:
            lines = f.readlines()

        nbyr = int(lines[7][12:16])
        start_year = int(lines[8][12:16])
        start_day = int(lines[9][12:16])
        end_day = int(lines[10][12:16])
        iprint = int(lines[58][12:16])
        skip_years = int(lines[59][12:16])

        warmup_start_year = start_year + skip_years
        end_year = start_year + nbyr - 1
        warmup_end_year = warmup_start_year + nbyr - 1 - skip_years

        if skip_years > 0:
            warmup_start_day = 1
        else:
            warmup_start_day = start_day

        period = {
            "start_date": dt.datetime(start_year, 1, 1) + dt.timedelta(start_day - 1),
            "end_date": dt.datetime(end_year, 1, 1) + dt.timedelta(end_day - 1),
            "warmup_start_date": dt.datetime(warmup_start_year, 1, 1)
            + dt.timedelta(warmup_start_day - 1),
            "warmup_end_date": dt.datetime(warmup_end_year, 1, 1)
            + dt.timedelta(end_day - 1),
            "iprint": iprint,
            "skip_years": skip_years,
        }

        self._period = period
        return period

    @property
    def period(self):
        if self._period is None:
            self._period = self.read_file_cio_period()
        return self._period

    def _date_index(self, nrows, include_warmup=True):
        start = (
            self.period["warmup_start_date"]
            if include_warmup
            else self.period["start_date"]
        )
        iprint = self.period["iprint"]

        if iprint == 1:
            return pd.date_range(start, periods=nrows, freq="D")
        if iprint == 0:
            return pd.date_range(start, periods=nrows, freq="M")
        return pd.date_range(start, periods=nrows, freq="A")

    def read_observed_csv(self, filename):
        """Read an iHydroCal-style observed wide CSV with a date index."""

        return pd.read_csv(
            self._path(filename),
            index_col=0,
            parse_dates=True,
            na_values=[-999, "", "NA", "NaN"],
        )

    def read_output_rch(self, flow_col_num=6):
        """Read SWAT output.rch flow data using the legacy SWAT-MODFLOW layout.

        Parameters
        ----------
        flow_col_num : int, default 6
            Zero-based column number passed to pandas ``usecols``. In the
            legacy workflow, 6 corresponds to the streamflow column used by
            ``SWATMFout.get_stf_sim_obd``.
        """

        return pd.read_csv(
            self._path("output.rch"),
            sep=r"\s+",
            skiprows=9,
            usecols=[1, 3, flow_col_num],
            names=["subbasin", "filter", "stf_sim"],
            index_col="subbasin",
        )

    def get_streamflow_sim(self, subbasin, flow_col_num=6, include_warmup=True):
        """Return simulated streamflow for one subbasin."""

        output_rch = self.read_output_rch(flow_col_num=flow_col_num)
        df = output_rch.loc[int(subbasin)].copy()

        if isinstance(df, pd.Series):
            df = df.to_frame().T

        if self.period["iprint"] == 0:
            df = df.loc[df["filter"] < 13]

        df.index = self._date_index(len(df), include_warmup=include_warmup)
        return df[["stf_sim"]]

    def get_streamflow_sim_obs(
        self,
        obs_file,
        obs_col,
        subbasin,
        flow_col_num=6,
        include_warmup=True,
        dropna=True,
    ):
        """Join simulated and observed streamflow for one subbasin."""

        sim = self.get_streamflow_sim(
            subbasin=subbasin,
            flow_col_num=flow_col_num,
            include_warmup=include_warmup,
        )
        obs = self.read_observed_csv(obs_file)

        if obs_col not in obs.columns:
            raise KeyError(f"Column '{obs_col}' not found in {obs_file}.")

        df = pd.concat([sim, obs[[obs_col]]], axis=1)
        df = df.reset_index().rename(columns={"index": "date"})

        if dropna:
            df = df.dropna(subset=["stf_sim", obs_col])

        return df

    def read_output_sub(self):
        """Read selected precipitation and water balance fields from output.sub.

        This supports the common SWAT-MODFLOW daily ``BIGSUB`` format, e.g.::

            BIGSUB   1        0    1.97038E+01  0.540E+01 ...

        The older workflow used fixed-width slicing for monthly output. The
        daily format is more reliable when parsed with whitespace tokens.
        """

        with open(self._path("output.sub"), "r") as f:
            content = f.readlines()

        records = []
        for line in content[9:]:
            parts = line.split()

            if not parts:
                continue

            if parts[0].upper().startswith("BIGSUB"):
                if len(parts) < 22:
                    continue

                try:
                    records.append(
                        {
                            "subbasin": int(parts[1]),
                            "gis": int(float(parts[2])),
                            "area_km2": float(parts[3]),
                            "precip": float(parts[4]),
                            "snomelt": float(parts[5]),
                            "pet": float(parts[6]),
                            "et": float(parts[7]),
                            "soil_water": float(parts[8]),
                            "perco": float(parts[9]),
                            "surq": float(parts[10]),
                            "gwq": float(parts[11]),
                            "wyld": float(parts[12]),
                            "sed": float(parts[13]),
                            "orgn": float(parts[14]),
                            "orgp": float(parts[15]),
                            "nsurq": float(parts[16]),
                            "solp": float(parts[17]),
                            "sedp": float(parts[18]),
                            "latq": float(parts[19]),
                            "latno3": float(parts[20]),
                            "gwno3": float(parts[21]),
                        }
                    )
                except (ValueError, IndexError):
                    continue

                continue

            try:
                mon = float(line[19:24])
                if mon >= 13:
                    continue
                records.append(
                    {
                        "subbasin": int(line[6:10]),
                        "mon": int(mon),
                        "precip": float(line[34:44]),
                        "et": float(line[64:74]),
                        "soil_water": float(line[74:84]),
                        "perco": float(line[84:94]),
                        "surq": float(line[94:104]),
                        "gwq": float(line[104:114]),
                        "sed": float(line[124:134]),
                        "latq": float(line[184:194]),
                    }
                )
            except (ValueError, IndexError):
                continue

        return pd.DataFrame.from_records(records)

    def get_precip(self, subbasin, col="precip", include_warmup=True):
        """Return precipitation time series from output.sub for one subbasin."""

        df = self.read_output_sub()
        df = df.loc[df["subbasin"] == int(subbasin), [col]].copy()
        df.columns = ["precip"]
        df.index = self._date_index(len(df), include_warmup=include_warmup)
        return df.reset_index().rename(columns={"index": "date"})

    def read_modflow_obs_points(self):
        """Read MODFLOW observation-point metadata from modflow.obs."""

        mf_obs = pd.read_csv(
            self._path("modflow.obs"),
            sep=r"\s+",
            skiprows=2,
            usecols=[2, 3, 4],
            names=["layer", "grid_id", "mf_elev"],
        )
        mf_obs["sim_col"] = (
            "sim_g"
            + mf_obs["grid_id"].astype(str)
            + "lyr"
            + mf_obs["layer"].astype(str)
        )
        return mf_obs

    def get_groundwater_sim(self, dtw_format=True, include_warmup=False):
        """Read simulated groundwater observations.

        If ``dtw_format`` is True, simulated heads are converted with the same
        convention as the legacy workflow: ``head - ground_elevation``.
        """

        mf_obs = self.read_modflow_obs_points()
        sim_cols = mf_obs["sim_col"].tolist()

        output_wt = pd.read_csv(
            self._path("swatmf_out_MF_obs"),
            sep=r"\s+",
            skiprows=1,
            names=sim_cols,
        )

        if dtw_format:
            data = {}
            for _, row in mf_obs.iterrows():
                data[row["sim_col"]] = output_wt[row["sim_col"]] - float(row["mf_elev"])
            df = pd.DataFrame(data)
        else:
            df = output_wt

        df.index = self._date_index(len(df), include_warmup=include_warmup)
        return df.reset_index().rename(columns={"index": "date"})

    def get_dtw_sim(self, dtw_format=True, include_warmup=False):
        """Alias for get_groundwater_sim()."""

        return self.get_groundwater_sim(
            dtw_format=dtw_format,
            include_warmup=include_warmup,
        )

    def get_dtw_obs(self, timestep=None):
        """Read observed depth-to-water CSV."""

        filename = "dtw_mon.obd.csv" if timestep == "month" else "dtw_day.obd.csv"
        df = self.read_observed_csv(filename)
        return df.reset_index().rename(columns={"index": "date"})

    def get_water_balance(self):
        """Read selected basin-scale water balance terms from output.std."""

        start_date = self.period["warmup_start_date"]
        end_year = self.period["warmup_end_date"].strftime("%Y")

        with open(self._path("output.std"), "r") as infile:
            raw_lines = infile.readlines()

        header_prefix = ("TIME", "UNIT", "SWAT", "(mm)")
        lines = []
        for line in raw_lines:
            data = line.strip()
            if len(data) > 100 and not data.startswith(header_prefix):
                lines.append(line)

        records = []
        previous_time = None
        for line in lines:
            parts = line.split()
            if not parts:
                continue

            time_value = parts[0]
            if time_value == end_year:
                break
            if len(time_value) == 4:
                continue

            try:
                t = int(time_value)
                if previous_time is not None:
                    if t == 1 and t - previous_time == -30:
                        previous_time = t
                        continue
                    if t < previous_time and t != 1:
                        previous_time = t
                        continue

                records.append(
                    {
                        "precip": float(parts[1]),
                        "surq": float(parts[2]),
                        "latq": float(parts[3]),
                        "gwq": float(parts[4]),
                        "swgw": float(parts[5]),
                        "perco": float(parts[7]),
                        "tile": float(parts[8]),
                        "sw": float(parts[10]),
                        "gw": float(parts[11]),
                    }
                )
                previous_time = t
            except (ValueError, IndexError):
                continue

        df = pd.DataFrame.from_records(records)
        df.index = pd.date_range(start_date, periods=len(df), freq="D")
        return df.reset_index().rename(columns={"index": "date"})

    def get_std_data(self):
        """Legacy-compatible alias for get_water_balance()."""

        return self.get_water_balance()
