import xarray as xr
import pandas as pd

def crop_time(ds: xr.Dataset, start_year=None, end_year=None) -> xr.Dataset:
    if "time" not in ds.coords:
        return ds
    if start_year is None and end_year is None:
        return ds

    # String-based slicing is the most robust way in xarray
    # and properly supports both cftime and numpy datetimes natively.
    time_slice = slice(
        str(start_year) if start_year is not None else None,
        str(end_year) if end_year is not None else None
    )
    return ds.sel(time=time_slice)

ds = xr.Dataset({"data": ("time", [1, 2, 3])}, coords={"time": pd.date_range("2000-01-01", periods=3, freq="Y")})
print(crop_time(ds, start_year=2000, end_year=2001))
