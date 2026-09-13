import cftime
import numpy as np
import pandas as pd
import xarray as xr
from dask.base import is_dask_collection

from esp_lab import eli_diagnostics
from esp_lab.utils.resource_utils import ResourceTracker


def _hindcast(years, missing=None):
    leads = [1, 2]
    values = np.arange(len(years) * 2 * 2, dtype=float).reshape(len(years), 2, 2)
    data = xr.DataArray(
        values,
        dims=("Y", "L", "M"),
        coords={"Y": years, "L": leads, "M": [0, 1]},
    )
    if missing is not None:
        data.loc[missing] = np.nan
    time = xr.DataArray(
        [[cftime.DatetimeNoLeap(year, lead, 15) for lead in leads] for year in years],
        dims=("Y", "L"),
        coords={"Y": years, "L": leads},
    )
    return data, time


def test_initialization_years_supports_numeric_and_tagged_coordinates():
    np.testing.assert_array_equal(eli_diagnostics.initialization_years([1980, 1981]), [1980, 1981])
    np.testing.assert_array_equal(
        eli_diagnostics.initialization_years(["1980050100", "1981050100"]), [1980, 1981]
    )


def test_observation_alignment_supports_numpy_and_cftime_dates():
    observation = xr.DataArray(
        [1.0, 2.0],
        dims="time",
        coords={"time": pd.to_datetime(["2000-01-01", "2000-02-01"])},
    )

    result = eli_diagnostics.observations_for_times(
        observation,
        [cftime.DatetimeNoLeap(2000, 2, 15), cftime.DatetimeNoLeap(2000, 1, 15)],
    )

    np.testing.assert_array_equal(result, [2.0, 1.0])


def test_common_target_years_are_intersected_per_lead():
    first, first_time = _hindcast([2000, 2001, 2002, 2003])
    second, second_time = _hindcast(
        [2000, 2001, 2002, 2003], missing={"Y": 2001, "L": 1}
    )
    observation = xr.DataArray(
        np.arange(8, dtype=float),
        dims="time",
        coords={
            "time": [
                cftime.DatetimeNoLeap(year, month, 15)
                for year in [2000, 2001, 2002, 2003]
                for month in [1, 2]
            ]
        },
    )

    cohorts = eli_diagnostics.common_target_years_by_lead(
        {"first": {5: first}, "second": {5: second}},
        {"first": {5: first_time}, "second": {5: second_time}},
        observation,
        5,
    )

    assert cohorts == {1: [2000, 2002, 2003], 2: [2000, 2001, 2002, 2003]}


def test_model_hindcasts_can_remain_dask_backed(tmp_path):
    values, valid_time = _hindcast([2000, 2001, 2002, 2003])
    path = tmp_path / "model_05_2_2.nc"
    xr.Dataset({"eli": values, "time": valid_time}).to_netcdf(path)
    spec = eli_diagnostics.ELIModelSpec(
        key="model",
        label="Model",
        root=tmp_path,
        filename_template="model_{init_month:02d}_{nens}_{nlead}.nc",
        ensemble_size=2,
        color="black",
        marker="o",
    )
    tracker = ResourceTracker()

    data, times, _ = eli_diagnostics.load_model_hindcasts(
        {"model": spec},
        [5],
        nlead=2,
        start_year=2000,
        end_year=2003,
        chunks={"Y": -1, "L": 1, "M": -1},
        resource_tracker=tracker,
    )

    assert is_dask_collection(data["model"][5].data)
    assert not is_dask_collection(times["model"][5].data)
    np.testing.assert_array_equal(data["model"][5].compute(), values)
    tracker.close()
