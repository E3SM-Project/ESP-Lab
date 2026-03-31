import xarray as xr
import numpy as np
from esp_lab.data_access_e3sm import e3sm_regional_weights, e3sm_region_mask

lat = np.linspace(-90, 90, 100)
lon = np.linspace(0, 359, 100)
data = np.ones((100, 100))
da = xr.DataArray(data, coords={"lat": lat, "lon": lon}, dims=["lat", "lon"])
mask3 = e3sm_region_mask(da, [-170, -120, -5, 5])

weights = e3sm_regional_weights(da, [-170, -120, -5, 5])
bool_chk = mask3.astype(bool)

print("Weights outside region are 0?", (weights.where(~bool_chk).fillna(0) == 0).all().values)
print("Weights inside region are > 0?", (weights.where(bool_chk).count().values) > 0)
