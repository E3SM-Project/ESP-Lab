import xarray as xr
import numpy as np
from esp_lab.utils.spatial_utils import compute_regional_average

def test_regional_average_regionmask_only():
    lat = np.linspace(-90, 90, 10)
    lon = np.linspace(0, 360, 20)
    data = np.ones((10, 20))
    da = xr.DataArray(data, coords={"lat": lat, "lon": lon}, dims=["lat", "lon"])
    
    # Test simple average
    res = compute_regional_average(da, (-10, 10), (10, 20))
    assert np.isclose(res.values, 1.0)
    
test_regional_average_regionmask_only()
print("Basic test passed!")
