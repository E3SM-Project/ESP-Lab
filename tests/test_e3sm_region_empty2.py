import xarray as xr
import numpy as np
from esp_lab.data_access_e3sm import e3sm_regional_mean, e3sm_region_mask

lat = np.linspace(-90, 90, 100)
lon = np.linspace(0, 359, 100)
data = np.ones((100, 100))
da = xr.DataArray(data, coords={"lat": lat, "lon": lon}, dims=["lat", "lon"])
mask = e3sm_region_mask(da, [170, 240, -5, 5])
print("Total cells in Ni\u00f1o3.4 region expected to be > 0: ", mask.sum().values)

# Let's test the negative constraint! If user passes lon = [-170, -120], but data is 0..360!
mask3 = e3sm_region_mask(da, [-170, -120, -5, 5])
print("Total cells in region (-170 to -120) when data is 0-360: ", mask3.sum().values)
