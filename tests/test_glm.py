import numpy as np
import xarray as xr
from global_land_mask import globe

lat = np.array([0, 10, 20])
lon = np.array([-180, 0, 180])
lon_grid, lat_grid = np.meshgrid(lon, lat)
mask = globe.is_land(lat_grid, lon_grid)

print(mask)
