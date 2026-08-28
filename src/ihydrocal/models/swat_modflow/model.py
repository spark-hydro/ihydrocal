from pathlib import Path

<<<<<<< HEAD
import pandas as pd

from ihydrocal.analyzer.metrics import evaluate_metrics
=======
>>>>>>> 45f1a311d94b5323d5e4865514c164cd01a44fc3
from ihydrocal.core import BaseModel, register_model
from .io import SWATModflowIO


@register_model("swat_modflow")
class SWATModflowModel(BaseModel):
    """Model adapter for SWAT-MODFLOW."""

    def __init__(self, model_dir, output_dir=None, config=None):
        super().__init__(model_dir=model_dir, config=config)

        self.model_dir = Path(model_dir)
        self.output_dir = Path(output_dir) if output_dir is not None else self.model_dir
        self.io = SWATModflowIO(self.output_dir)

    def validate(self):
        """Validate SWAT-MODFLOW model directory."""

        if not self.model_dir.exists():
            return False

        if not self.output_dir.exists():
            return False

        if not (self.output_dir / "file.cio").exists():
            return False

        self.io = SWATModflowIO(self.output_dir)
        return True

    def get_output_file(self, filename):
        return self.output_dir / filename

    def list_output_files(self, pattern="*"):
        if not self.output_dir.exists():
            return []
        return sorted(self.output_dir.glob(pattern))

<<<<<<< HEAD
    def evaluate_streamflow(
        self,
        obs_file,
        reach_id,
        obs_id,
        flow_col_num=6,
        include_warmup=True,
        start_date=None,
        end_date=None,
        aggregate=None,
        aggregate_func="mean",
    ):
        """Evaluate streamflow for one SWAT reach and observation series.

        Parameters
        ----------
        obs_file : str or pathlib.Path
            Wide observed-streamflow CSV located in ``output_dir`` unless an
            absolute path is supplied.
        reach_id : int
            Reach (subbasin) ID selected from ``output.rch``.
        obs_id : str
            Observed-data column selected from ``obs_file``.
        flow_col_num : int, default 6
            Zero-based ``output.rch`` column containing simulated flow.
        include_warmup : bool, default True
            Passed to the SWAT-MODFLOW output reader when constructing dates.
        start_date : str or datetime-like, optional
            First date included in the evaluation period.
        end_date : str or datetime-like, optional
            Last date included in the evaluation period.
        aggregate : {None, "monthly", "annual"}, default None
            Optional temporal aggregation before calculating metrics.
        aggregate_func : str or callable, default "mean"
            Function used to aggregate observed and simulated streamflow.

        Returns
        -------
        matched : pandas.DataFrame
            Aligned ``date``, ``stf_sim``, and observed-data columns.
        metrics : dict
            NSE, KGE, R2, RMSE, and PBIAS calculated from valid pairs.
        """

        matched = self.io.get_streamflow_pair(
            obs_file=obs_file,
            reach_id=reach_id,
            obs_id=obs_id,
            flow_col_num=flow_col_num,
            include_warmup=include_warmup,
            dropna=False,
        )

        matched["date"] = pd.to_datetime(matched["date"])
        matched["stf_sim"] = pd.to_numeric(matched["stf_sim"], errors="coerce")
        matched[obs_id] = pd.to_numeric(matched[obs_id], errors="coerce")

        if start_date is not None:
            start_date = pd.to_datetime(start_date)
            matched = matched.loc[matched["date"] >= start_date]

        if end_date is not None:
            end_date = pd.to_datetime(end_date)
            matched = matched.loc[matched["date"] <= end_date]

        if (
            start_date is not None
            and end_date is not None
            and start_date > end_date
        ):
            raise ValueError("start_date must be earlier than or equal to end_date.")

        # Use identical dates for both series, including before aggregation.
        # Otherwise a monthly simulated mean could include days for which no
        # observed value exists, making the comparison inconsistent.
        matched = matched.dropna(subset=["stf_sim", obs_id])

        if aggregate is not None:
            frequencies = {
                "monthly": "ME",
                "month": "ME",
                "M": "ME",
                "annual": "YE",
                "yearly": "YE",
                "year": "YE",
                "Y": "YE",
                "A": "YE",
            }
            if aggregate not in frequencies:
                raise ValueError(
                    "aggregate must be None, 'monthly', 'month', 'M', "
                    "'annual', 'yearly', 'year', 'Y', or 'A'."
                )

            matched = (
                matched.set_index("date")[["stf_sim", obs_id]]
                .resample(frequencies[aggregate])
                .agg(aggregate_func)
                .reset_index()
            )

        matched = matched.reset_index(drop=True)
        metrics = evaluate_metrics(matched[obs_id], matched["stf_sim"])

        return matched, metrics

=======
>>>>>>> 45f1a311d94b5323d5e4865514c164cd01a44fc3
    def read_outputs(self):
        """Read SWAT-MODFLOW outputs.

        This will be expanded later.
        """
        raise NotImplementedError(
            "SWAT-MODFLOW output reader is not implemented yet."
        )
