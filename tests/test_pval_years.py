import xarray as xr
import numpy as np
import xskillscore as xs

np.random.seed(0)

print("Testing with N=2 years")
a2 = xr.DataArray(np.random.normal(0, 1, 2), dims=['time'])
b2 = xr.DataArray(np.random.normal(0, 1, 2), dims=['time'])
print("  Correlation:", xs.pearson_r(a2, b2, dim='time').values)
print("  Standard p-value:", xs.pearson_r_p_value(a2, b2, dim='time').values)
print("  Effective p-value:", xs.pearson_r_eff_p_value(a2, b2, dim='time').values)

print("\nTesting with N=3 years")
a3 = xr.DataArray(np.random.normal(0, 1, 3), dims=['time'])
b3 = xr.DataArray(np.random.normal(0, 1, 3), dims=['time'])
print("  Correlation:", xs.pearson_r(a3, b3, dim='time').values)
print("  Standard p-value:", xs.pearson_r_p_value(a3, b3, dim='time').values)
print("  Effective p-value:", xs.pearson_r_eff_p_value(a3, b3, dim='time').values)
