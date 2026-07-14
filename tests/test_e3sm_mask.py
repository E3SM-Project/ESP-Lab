import numpy as np
import xarray as xr
from esp_lab.data_access_e3sm import e3sm_regional_weights, e3sm_region_mask


def _make_da():
    lat = np.linspace(-90, 90, 100)
    lon = np.linspace(0, 359, 100)
    data = np.ones((100, 100))
    return xr.DataArray(data, coords={"lat": lat, "lon": lon}, dims=["lat", "lon"])


def test_e3sm_region_mask_shape():
    da = _make_da()
    mask = e3sm_region_mask(da, [-170, -120, -5, 5])
    assert mask.shape == da.shape


def test_e3sm_regional_weights_zero_outside_region():
    da = _make_da()
    mask = e3sm_region_mask(da, [-170, -120, -5, 5])
    weights = e3sm_regional_weights(da, [-170, -120, -5, 5])
    bool_mask = mask.astype(bool)
    assert (weights.where(~bool_mask).fillna(0) == 0).all()


def test_e3sm_regional_weights_nonzero_inside_region():
    da = _make_da()
    mask = e3sm_region_mask(da, [-170, -120, -5, 5])
    weights = e3sm_regional_weights(da, [-170, -120, -5, 5])
    bool_mask = mask.astype(bool)
    assert weights.where(bool_mask).count().values > 0
