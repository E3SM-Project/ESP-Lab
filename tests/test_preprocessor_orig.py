import xarray as xr
import pandas as pd
import numpy as np

def crop_time(
    ds: xr.Dataset,
    start_year = None,
    end_year = None,
) -> xr.Dataset:
    if "time" not in ds.coords:
        return ds

    if start_year is None and end_year is None:
        return ds

    return ds.sel(time=slice(start_year, end_year))

time_pd = pd.date_range("1999-01-01", periods=24, freq="MS")
ds1 = xr.Dataset({"obs_var": ("time", np.random.rand(24))}, coords={"time": time_pd})
print(crop_time(ds1, 2000, 2000))
