import xarray as xr
import pandas as pd
import numpy as np

def crop_time(ds: xr.Dataset, start_year=None, end_year=None) -> xr.Dataset:
    time_slice = slice(
        str(start_year) if start_year is not None else None,
        str(end_year) if end_year is not None else None
    )
    return ds.sel(time=time_slice)

time_pd = pd.date_range("1999-01-01", periods=24, freq="MS")
ds1 = xr.Dataset({"obs_var": ("time", np.random.rand(24))}, coords={"time": time_pd})
print(len(crop_time(ds1, 2000, 2000).time))
