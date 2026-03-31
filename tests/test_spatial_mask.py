import xarray as xr
import numpy as np
from esp_lab.utils.spatial_utils import compute_regional_average

lat = np.array([0, 10, 20])
lon = np.array([-180, 0, 180])
data = np.ones((3, 3))
da = xr.DataArray(data, coords={"lat": lat, "lon": lon}, dims=["lat", "lon"])
# Land mask average
land_avg = compute_regional_average(da, (-10, 30), (-180, 180), land_mask=True)
print("Land Avg:", land_avg.values)
# Ocean mask average
ocean_avg = compute_regional_average(da, (-10, 30), (-180, 180), ocean_mask=True)
print("Ocean Avg:", ocean_avg.values)
