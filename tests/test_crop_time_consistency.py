import xarray as xr
import pandas as pd
import cftime
import numpy as np

# Import the exact function from the module
from esp_lab.data_access_obs import crop_time

def run_tests():
    # Test 1: Standard datetime64
    print("Testing pandas datetime64...")
    ds1 = xr.Dataset(
        {"data": ("time", [1, 2, 3, 4, 5])}, 
        coords={"time": pd.date_range("1999-01-01", periods=5, freq="YS")}
    )
    res1 = crop_time(ds1, start_year=2000, end_year=2002)
    print("  Result times:", res1.time.dt.year.values)
    assert len(res1.time) == 3

    # Test 2: cftime NoLeap (common in climate models like CESM/E3SM)
    print("Testing cftime...")
    time_cftime = [cftime.DatetimeNoLeap(y, 1, 1) for y in [1999, 2000, 2001, 2002, 2003]]
    ds2 = xr.Dataset({"data": ("time", [1, 2, 3, 4, 5])}, coords={"time": time_cftime})
    res2 = crop_time(ds2, start_year="2000", end_year="2002")
    print("  Result times:", [t.year for t in res2.time.values])
    assert len(res2.time) == 3

    # Test 3: Raw integers as time coordinate
    print("Testing raw integers...")
    ds3 = xr.Dataset({"data": ("time", [1, 2, 3, 4, 5])}, coords={"time": [1999, 2000, 2001, 2002, 2003]})
    res3 = crop_time(ds3, start_year=2000, end_year=2002)
    print("  Result times:", res3.time.values)
    assert len(res3.time) == 3
    
    print("\nAll tests passed consistently!")

run_tests()
