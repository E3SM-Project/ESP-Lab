import xarray as xr
import pandas as pd
import numpy as np
from esp_lab.data_access_obs import preprocessor_monthly

time_pd = pd.date_range("1999-01-01", periods=24, freq="MS")
ds1 = xr.Dataset({"obs_var": ("time", np.random.rand(24))}, coords={"time": time_pd})
res1 = preprocessor_monthly(ds1, field="obs_var", start_year=2000, end_year=2000, harmonize_time=True)
print(res1)
