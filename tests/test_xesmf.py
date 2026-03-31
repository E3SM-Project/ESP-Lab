import xarray as xr
import numpy as np
import xesmf as xe

def _coord_bounds_1d_size_n_plus_1(coord):
    vals = np.asarray(coord.values, dtype=float)
    mid = 0.5 * (vals[1:] + vals[:-1])
    first = vals[0] - 0.5 * (vals[1] - vals[0])
    last = vals[-1] + 0.5 * (vals[-1] - vals[-2])
    return xr.DataArray(
        np.concatenate([[first], mid, [last]]),
        dims=(coord.dims[0] + "_b",)
    )

def _make_grid_ds(lat, lon, lat_name="lat", lon_name="lon"):
    return xr.Dataset(
        coords={
            lat_name: lat,
            lon_name: lon,
            f"{lat_name}_b": _coord_bounds_1d_size_n_plus_1(lat),
            f"{lon_name}_b": _coord_bounds_1d_size_n_plus_1(lon),
        }
    )

lat = xr.DataArray(np.linspace(-90, 90, 10), dims=("lat",), name="lat")
lon = xr.DataArray(np.linspace(0, 360, 20), dims=("lon",), name="lon")
ds1 = _make_grid_ds(lat, lon)

lat2 = xr.DataArray(np.linspace(-90, 90, 5), dims=("lat",), name="lat")
lon2 = xr.DataArray(np.linspace(0, 360, 10), dims=("lon",), name="lon")
ds2 = _make_grid_ds(lat2, lon2)

print("ds1 fields:", list(ds1.variables.keys()))
print("ds1 lat_b shape:", ds1["lat_b"].shape)
regridder = xe.Regridder(ds1, ds2, method="conservative")
print("success")
