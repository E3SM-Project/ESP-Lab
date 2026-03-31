import xarray as xr
import numpy as np
from esp_lab.data_access_e3sm import e3sm_regional_mean, e3sm_region_mask

lat = np.linspace(-90, 90, 100)
lon = np.linspace(0, 359, 100)
data = np.ones((100, 100))
da = xr.DataArray(data, coords={"lat": lat, "lon": lon}, dims=["lat", "lon"])
# Test region spanning dateline (Niño3.4)
res2 = e3sm_regional_mean(da, [170, 290, -5, 5])
print(res2)
