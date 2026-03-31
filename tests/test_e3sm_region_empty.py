import xarray as xr
import numpy as np
from esp_lab.data_access_e3sm import e3sm_regional_mean, e3sm_region_mask

lat = np.linspace(-90, 90, 100)
lon = np.linspace(0, 359, 100)
data = np.ones((100, 100))
da = xr.DataArray(data, coords={"lat": lat, "lon": lon}, dims=["lat", "lon"])
# Test region spanning dateline (Niño3.4) but see if the mask actually captured anything
mask = e3sm_region_mask(da, [170, 240, -5, 5])
print("Total cells in Ni\u00f1o3.4 region expected to be > 0: ", mask.sum().values)

# What if user asks for 170 to 240 (Pacific), but data is -180 to 180?
lon2 = np.linspace(-180, 179, 100)
da2 = xr.DataArray(data, coords={"lat": lat, "lon": lon2}, dims=["lat", "lon"])
mask2 = e3sm_region_mask(da2, [170, 240, -5, 5])
print("Total cells in Ni\u00f1o3.4 on -180..180 grid: ", mask2.sum().values)
