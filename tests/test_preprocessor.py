import xarray as xr
import pandas as pd
import cftime
import numpy as np
from esp_lab.data_access_obs import preprocessor_monthly

def run_tests():
    # Test dataset 1: standard datetime
    print("Testing preprocessor_monthly on datetime64 dataset...")
    time_pd = pd.date_range("1999-01-01", periods=24, freq="MS")
    ds1 = xr.Dataset({"obs_var": ("time", np.random.rand(24))}, coords={"time": time_pd})
    
    res1 = preprocessor_monthly(ds1, field="obs_var", start_year=2000, end_year=2000, harmonize_time=True)
    print("  Result times type:", type(res1.time.values[0]))
    print("  Result years:", [t.year for t in res1.time.values[:2]])
    assert len(res1.time) == 12 # Cropped exactly to 1 full year 

    # Test dataset 2: cftime
    print("\nTesting preprocessor_monthly on cftime dataset...")
    time_cf = [cftime.DatetimeNoLeap(y, m, 1) for y in [1999, 2000] for m in range(1, 13)]
    ds2 = xr.Dataset({"obs_var": ("time", np.random.rand(24))}, coords={"time": time_cf})
    
    res2 = preprocessor_monthly(ds2, field="obs_var", start_year="2000", end_year="2000", harmonize_time=True)
    print("  Result times type:", type(res2.time.values[0]))
    assert len(res2.time) == 12

    print("\nAll tests passed successfully!")

run_tests()
