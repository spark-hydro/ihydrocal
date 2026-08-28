"""Tests for SWAT-MODFLOW streamflow evaluation."""

import numpy as np
import pandas as pd

from ihydrocal.models.swat_modflow import SWATModflowModel


def test_evaluate_streamflow_selects_pair_and_calculates_metrics(tmp_path, monkeypatch):
    (tmp_path / "file.cio").touch()
    model = SWATModflowModel(tmp_path)

    pair = pd.DataFrame(
        {
            "date": pd.date_range("2001-01-01", periods=4, freq="D"),
            "stf_sim": [1.0, 2.0, 3.0, 4.0],
            "gage_101": [1.0, 2.0, np.nan, 4.0],
        }
    )
    received = {}

    def fake_get_streamflow_pair(**kwargs):
        received.update(kwargs)
        return pair.copy()

    monkeypatch.setattr(model.io, "get_streamflow_pair", fake_get_streamflow_pair)

    matched, metrics = model.evaluate_streamflow(
        obs_file="stf_day.obd.csv",
        reach_id=12,
        obs_id="gage_101",
    )

    assert received["reach_id"] == 12
    assert received["obs_id"] == "gage_101"
    assert len(matched) == 3
    assert metrics["NSE"] == 1.0
    assert metrics["KGE"] == 1.0
    assert metrics["R2"] == 1.0
    assert metrics["RMSE"] == 0.0
    assert metrics["PBIAS"] == 0.0


def test_evaluate_streamflow_monthly_aggregation(tmp_path, monkeypatch):
    (tmp_path / "file.cio").touch()
    model = SWATModflowModel(tmp_path)

    pair = pd.DataFrame(
        {
            "date": pd.to_datetime(["2001-01-01", "2001-01-02", "2001-02-01"]),
            "stf_sim": [1.0, 3.0, 4.0],
            "site_1": [2.0, 2.0, 4.0],
        }
    )
    monkeypatch.setattr(
        model.io,
        "get_streamflow_pair",
        lambda **kwargs: pair.copy(),
    )

    matched, metrics = model.evaluate_streamflow(
        obs_file="stf_day.obd.csv",
        reach_id=1,
        obs_id="site_1",
        aggregate="monthly",
    )

    assert matched["stf_sim"].tolist() == [2.0, 4.0]
    assert matched["site_1"].tolist() == [2.0, 4.0]
    assert metrics["NSE"] == 1.0



if __name__ == "__main__":

    model_dir = r"E:\Projects\Watersheds\Okavango\Analysis\CORB_swatmf_models\BASE"
    from ihydrocal.models.swat_modflow import SWATModflowModel

    model = SWATModflowModel(model_dir)

    matched_df, metrics = model.evaluate_streamflow(
        obs_file="stf_mon.obd.csv",
        reach_id=240,
        obs_id="sub_240_mohembo",
    )
    df = matched_df.set_index('date')
    cal_mohembo = df["2003-01":"2007-12"]




    print(matched_df.head())
    print(metrics)
    print(df["2003-01":"2008-12"])   


    cal_df, cal_metrics = model.evaluate_streamflow(
        obs_file="stf_mon.obd.csv",
        reach_id=225,
        obs_id="sub_225_dirico",
        start_date="2003-01-01",
        end_date="2007-12-31",
    )

    val_df, val_metrics = model.evaluate_streamflow(
        obs_file="stf_mon.obd.csv",
        reach_id=225,
        obs_id="sub_225_dirico",
        start_date="2008-01-01",
        end_date="2010-12-31",
    )
    # print(cal_metrics)
    # print("Calibration metrics:", f"{cal_metrics:.3f}")
    # print("Validation metrics:", f"{val_metrics:.3f}")

    performance = pd.DataFrame(
        {
            "Calibration": cal_metrics,
            "Validation": val_metrics,
        }
    ).T

    print(performance)