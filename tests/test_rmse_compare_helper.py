import numpy as np
import xarray as xr

from workflows.rmse_compare_helper import (
    area_weighted_mask_fraction,
    bootstrap_rmse_diff_matched_ensemble_memorysafe,
    direct_rmse_difference,
    finite_ensemble_rmse_comparison_memorysafe,
    lead_label,
    make_obs_like_model_leads,
    normalize_direct_rmse_leads,
    require_available_lead,
    safe_model_name,
)


def test_shared_direct_rmse_metadata_helpers():
    legacy = xr.Dataset(
        {"rmse": ("L", [1.0, 2.0])},
        coords={"L": [1, 4]},
    )

    normalized = normalize_direct_rmse_leads(legacy)

    np.testing.assert_array_equal(normalized["L"], [3, 6])
    assert require_available_lead(normalized, 3) == 3
    assert lead_label(5, 3, {5: "MAY"}) == "Lead-1 JJA (May init)"
    assert safe_model_name("E3SM / FOSIRL") == "E3SM___FOSIRL"


def test_direct_rmse_difference_and_weighted_fraction():
    coords = {"L": [3], "lat": [0.0, 60.0], "lon": [0.0]}
    left = xr.Dataset(
        {"rmse": (("L", "lat", "lon"), [[[1.0], [3.0]]])},
        coords=coords,
    )
    right = xr.Dataset(
        {"rmse": (("L", "lat", "lon"), [[[2.0], [2.0]]])},
        coords=coords,
    )

    result = direct_rmse_difference(left, right)
    mask = result["rmse_diff"].sel(L=3) < 0

    np.testing.assert_array_equal(result["rmse_diff"], [[[-1.0], [1.0]]])
    np.testing.assert_array_equal(result["rmse_ratio"], [[[0.5], [1.5]]])
    assert np.isclose(area_weighted_mask_fraction(mask), 2.0 / 3.0)


def test_make_obs_like_model_leads_uses_season_verification_month():
    time = np.arange(
        np.datetime64("1980-01"),
        np.datetime64("1982-01"),
        dtype="datetime64[M]",
    )
    obs = xr.DataArray(
        np.arange(time.size, dtype=float)[:, None, None],
        dims=("time", "lat", "lon"),
        coords={"time": time, "lat": [30.0], "lon": [250.0]},
    )
    template = xr.DataArray(
        np.zeros((1, 2, 1, 1, 1)),
        dims=("Y", "L", "M", "lat", "lon"),
        coords={
            "Y": [1980],
            "L": [3, 15],
            "M": [0],
            "lat": [30.0],
            "lon": [250.0],
        },
    )

    result = make_obs_like_model_leads(
        obs_da=obs,
        template_da=template,
        init_month=5,
        years=[1980],
        leads=[3, 15],
    )

    expected = obs.sel(time=[np.datetime64("1980-07"), np.datetime64("1981-07")])
    np.testing.assert_array_equal(result.sel(Y=1980).values[:, 0, 0], expected.values[:, 0, 0])


def test_matched_ensemble_bootstrap_identifies_lower_rmse():
    coords = {
        "Y": [1980, 1981, 1982, 1983],
        "L": [3],
        "lat": [30.0],
        "lon": [250.0],
    }
    left = xr.DataArray(
        np.full((4, 1, 2, 1, 1), 1.0),
        dims=("Y", "L", "M", "lat", "lon"),
        coords={**coords, "M": [0, 1]},
    )
    right = xr.DataArray(
        np.full((4, 1, 4, 1, 1), 2.0),
        dims=("Y", "L", "M", "lat", "lon"),
        coords={**coords, "M": [0, 1, 2, 3]},
    )

    result = bootstrap_rmse_diff_matched_ensemble_memorysafe(
        left,
        right,
        nboot=20,
        seed=7,
        alpha=0.1,
    )

    assert result.attrs["matched_ensemble_size"] == 2
    assert result["rmse_diff"].item() == -1.0
    assert result["prob_left_lower_rmse"].item() == 1.0
    assert result["left_better"].item() == 1
    assert result["right_better"].item() == 0


def test_finite_ensemble_comparison_resamples_only_larger_ensemble():
    coords = {
        "Y": [1980, 1981, 1982, 1983],
        "L": [3],
        "lat": [30.0],
        "lon": [250.0],
    }
    left = xr.DataArray(
        np.full((4, 1, 2, 1, 1), 1.0),
        dims=("Y", "L", "M", "lat", "lon"),
        coords={**coords, "M": [0, 1]},
    )
    right = xr.DataArray(
        np.full((4, 1, 4, 1, 1), 2.0),
        dims=("Y", "L", "M", "lat", "lon"),
        coords={**coords, "M": [0, 1, 2, 3]},
    )

    result = finite_ensemble_rmse_comparison_memorysafe(
        left,
        right,
        n_iterations=20,
        seed=7,
        alpha=0.1,
    )

    assert result.attrs["larger_ensemble_side"] == "right"
    assert result.attrs["right_ensemble_size"] == 4
    assert result.attrs["matched_ensemble_size"] == 2
    assert result["rmse_diff"].item() == -1.0
    assert result["prob_left_lower_rmse"].item() == 1.0
