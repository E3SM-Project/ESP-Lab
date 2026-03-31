import xarray as xr
import numpy as np
import xskillscore as xs

# Create dummy timeseries data of size 5 with high correlation
# but standard pearson_r will work, while eff_p_value might fail if N is too small
np.random.seed(0)
a = xr.DataArray(np.linspace(0, 10, 10) + np.random.normal(0, 0.1, 10), dims=['time'])
b = xr.DataArray(np.linspace(0, 10, 10) + np.random.normal(0, 0.1, 10), dims=['time'])

r = xs.pearson_r(a, b, dim='time')
pval = xs.pearson_r_p_value(a, b, dim='time') 
pval_eff = xs.pearson_r_eff_p_value(a, b, dim='time')

print("Correlation:", r.values)
print("Standard p-value:", pval.values)
print("Effective p-value:", pval_eff.values)
