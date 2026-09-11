"""Unit tests for SST teleconnections diagnostics workflow."""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from workflows.diagnostics import sst_teleconnections as telecon


def test_downstream_target_grid_supports_independent_and_family_settings():
    config = {
        "selection": {
            "target_grids": {
                "atmosphere": "atm-family-grid",
                "land": "land-family-grid",
                "PRECT": "prect-specific-grid",
            }
        }
    }

    assert telecon.downstream_target_grid(config, "TREFHT") == "atm-family-grid"
    assert telecon.downstream_target_grid(config, "PRECT") == "prect-specific-grid"
    assert telecon.downstream_target_grid(config, "H2OSOI") == "land-family-grid"


def test_downstream_target_grid_builds_cache_identity_from_resolution():
    atmosphere = {
        "selection": {
            "target_grids": {
                "TREFHT": {"dlat": 1.0, "dlon": 2.5, "periodic": True}
            }
        }
    }
    land = {
        "selection": {
            "target_grids": {
                "H2OSOI": {"dlat": 1.0, "dlon": 1.0, "periodic": True}
            }
        }
    }

    assert (
        telecon.downstream_target_grid(atmosphere, "TREFHT")
        == "latlon_1.0x2.5_periodic-True"
    )
    assert telecon.downstream_target_grid(land, "H2OSOI") == "1x1deg_cell_centered"


def test_top_level_regrid_controls_grid_identity_and_method():
    config = {
        "selection": {},
        "regrid": {
            "target_dlat": 5.0,
            "target_dlon": 5.0,
            "method": "conservative",
            "periodic": True,
        },
    }

    assert (
        telecon.downstream_target_grid(config, "TREFHT")
        == "latlon_5.0x5.0_periodic-True"
    )
    assert telecon.downstream_target_grid(config, "H2OSOI") == "5x5deg_cell_centered"
    assert telecon.downstream_regrid_method(config) == "conservative"


def test_top_level_regrid_requires_complete_valid_settings():
    with pytest.raises(ValueError, match="missing required settings"):
        telecon.downstream_target_grid(
            {"selection": {}, "regrid": {"target_dlat": 1.0}}, "TREFHT"
        )
    with pytest.raises(TypeError, match="periodic must be boolean"):
        telecon.downstream_target_grid(
            {
                "selection": {},
                "regrid": {
                    "target_dlat": 1.0,
                    "target_dlon": 1.0,
                    "method": "conservative",
                    "periodic": "yes",
                },
            },
            "TREFHT",
        )


def test_downstream_target_grid_legacy_setting_only_applies_to_atmosphere():
    config = {"selection": {"target_grid": "legacy-atm-grid"}}

    assert telecon.downstream_target_grid(config, "TREFHT") == "legacy-atm-grid"
    assert (
        telecon.downstream_target_grid(config, "H2OSOI")
        == telecon.DEFAULT_DOWNSTREAM_TARGET_GRIDS["land"]
    )


def test_inventory_accepts_one_explicit_teleconnection_pair(tmp_path, monkeypatch):
    paths = [tmp_path / name for name in ("index-model.nc", "index-obs.nc", "field-model.nc", "field-obs.nc")]
    for path in paths:
        path.touch()

    monkeypatch.setattr(telecon, "upstream_sst_paths", lambda *args, **kwargs: tuple(paths[:2]))
    monkeypatch.setattr(telecon, "resolve_downstream_paths", lambda *args, **kwargs: tuple(paths[2:]))
    config = {
        "paths": {"diag_root": str(tmp_path)},
        "selection": {
            "upstream_index": "Nino3.4",
            "downstream_variable": "TREFHT",
            "systems": ["E3SM-FOSIRL"],
            "init_months": [5],
        },
        "regrid": {
            "target_dlat": 1.0,
            "target_dlon": 1.0,
            "method": "conservative",
            "periodic": True,
        },
        "cache": {"allow_ambiguous_matches": False},
    }

    inventory = telecon.build_teleconnection_inventory(config)
    assert inventory[["index", "variable", "status"]].to_dict("records") == [
        {"index": "Nino3.4", "variable": "TREFHT", "status": "ready"}
    ]


def test_ensure_upstream_products_prepares_only_missing_dependencies(tmp_path, monkeypatch):
    index_forecast = tmp_path / "index-model.nc"
    index_observed = tmp_path / "index-obs.nc"
    index_forecast.touch()
    index_observed.touch()
    missing = pd.DataFrame([{
        "system": "E3SM-FOSIRL", "init_month": 5, "index": "Nino3.4",
        "variable": "TREFHT", "index_forecast": str(index_forecast),
        "index_observed": str(index_observed), "field_forecast": None,
        "field_observed": None, "status": "missing", "detail": "missing field",
    }])
    ready = missing.assign(
        field_forecast=str(tmp_path / "field-model.nc"),
        field_observed=str(tmp_path / "field-obs.nc"), status="ready", detail="",
    )
    inventories = iter([missing, ready])
    monkeypatch.setattr(telecon, "build_teleconnection_inventory", lambda config: next(inventories))

    from workflows.diagnostics import teleconnection_inputs as preparation

    calls = []
    monkeypatch.setattr(
        preparation, "ensure_sst_indices",
        lambda *args, **kwargs: calls.append(("sst", args, kwargs)),
    )
    monkeypatch.setattr(
        preparation, "prepare_atmospheric_observation",
        lambda *args, **kwargs: calls.append(("obs", args, kwargs)),
    )
    monkeypatch.setattr(
        preparation, "prepare_atmospheric_model",
        lambda *args, **kwargs: calls.append(("model", args, kwargs)),
    )
    config = {
        "inputs": {"mode": "auto"},
        "selection": {"upstream_index": "Nino3.4"},
    }

    result = telecon.ensure_upstream_products(config)

    assert result.status.tolist() == ["ready"]
    assert [call[0] for call in calls] == ["obs", "model"]


def test_ensure_upstream_products_require_mode_is_read_only(monkeypatch):
    inventory = pd.DataFrame([{"status": "missing"}])
    monkeypatch.setattr(
        telecon, "build_teleconnection_inventory", lambda config: inventory
    )

    assert telecon.ensure_upstream_products(
        {"inputs": {"mode": "require"}}
    ) is inventory


def test_open_dataset_readonly_falls_back_on_hdf_error(monkeypatch):
    sentinel = object()
    calls = []

    def fake_open(path, **kwargs):
        calls.append((path, kwargs))
        if not kwargs:
            raise RuntimeError("NetCDF: HDF error")
        return sentinel

    monkeypatch.setattr(telecon.xr, "open_dataset", fake_open)
    assert telecon.open_dataset_readonly("cache.nc") is sentinel
    assert calls == [("cache.nc", {}), ("cache.nc", {"engine": "h5netcdf"})]


def test_select_cache_uses_resilient_reader(tmp_path, monkeypatch):
    path = tmp_path / "prepared.nc"
    path.touch()
    opened = []

    def fake_open(candidate):
        opened.append(Path(candidate))
        return xr.Dataset({"anomaly": ("sample", [1.0])}, attrs={"target_grid": "grid"})

    monkeypatch.setattr(telecon, "open_dataset_readonly", fake_open)
    selected = telecon.select_cache(
        [path], required_vars=("anomaly",), expected_attrs={"target_grid": "grid"}
    )

    assert selected == path
    assert opened == [path]


def test_parse_init_years():
    raw_strings = ["1980050100", "1981050100", "2011110100", "1995"]
    parsed = telecon.parse_init_years(raw_strings)
    np.testing.assert_array_equal(parsed, [1980, 1981, 2011, 1995])

    raw_ints = [1980, 1985, 2010]
    parsed_ints = telecon.parse_init_years(raw_ints)
    np.testing.assert_array_equal(parsed_ints, [1980, 1985, 2010])

    raw_timestamps = pd.to_datetime(["1980-05-01", "2015-11-01"])
    parsed_ts = telecon.parse_init_years(raw_timestamps)
    np.testing.assert_array_equal(parsed_ts, [1980, 2015])


def test_requested_leads_accepts_readable_all_and_explicit_values():
    assert telecon.requested_leads({"leads": "all"}) is None
    assert telecon.requested_leads({"leads": None}) is None
    assert telecon.requested_leads({"leads": [3, "6"]}) == {3, 6}
    with pytest.raises(ValueError, match="must be 'all'"):
        telecon.requested_leads({"leads": "3,6"})


def test_time_year_month():
    dates = pd.to_datetime(["1980-07-15", "1981-08-15", "1982-01-15"])
    years, months = telecon.time_year_month(dates)
    np.testing.assert_array_equal(years, [1980, 1981, 1982])
    np.testing.assert_array_equal(months, [7, 8, 1])


def test_lead_signature_and_matching():
    # Construct synthetic valid_time for index (39 starts) and field (32 starts)
    idx_starts = np.array([f"{y:04d}050100" for y in range(1980, 2019)])
    fld_starts = np.array([f"{y:04d}050100" for y in range(1980, 2012)])

    leads = [3, 6, 9, 12]
    # L=3 target is July (offset 0), L=6 is Oct (offset 0), L=9 is Jan next year (offset 1), L=12 is Apr next year (offset 1)
    def make_times(starts):
        arrays = []
        for L, (off, m) in zip(leads, [(0, 7), (0, 10), (1, 1), (1, 4)]):
            dates = [pd.Timestamp(f"{int(s[:4]) + off:04d}-{m:02d}-15") for s in starts]
            arrays.append(dates)
        return xr.DataArray(
            np.array(arrays).T,
            dims=("Y", "L"),
            coords={"Y": starts, "L": leads},
        )

    idx_time = make_times(idx_starts)
    fld_time = make_times(fld_starts)

    pairs = telecon.match_leads(idx_time, fld_time, init_dim="Y")
    expected = [(3, 3), (6, 6), (9, 9), (12, 12)]
    assert pairs == expected


def test_corr_and_p():
    n_sample = 25
    x_vals = np.linspace(1.0, 10.0, n_sample)
    y_vals = 2.0 * x_vals + 1.0  # Perfect linear relationship

    x = xr.DataArray(x_vals, dims=("sample",))
    y = xr.DataArray(
        np.tile(y_vals[:, None, None], (1, 2, 2)),
        dims=("sample", "lat", "lon"),
        coords={"lat": [10.0, 20.0], "lon": [100.0, 110.0]},
    )

    r, p, n = telecon.corr_and_p(x, y, minimum_years=10)
    assert np.allclose(r.values, 1.0)
    assert np.all(p.values < 1e-6)
    assert np.all(n.values == n_sample)

    # Test minimum sample threshold
    r_masked, _, _ = telecon.corr_and_p(x, y, minimum_years=30)
    assert np.all(np.isnan(r_masked.values))


def test_weighted_spatial_metrics():
    lat = np.array([-45.0, 0.0, 45.0])
    lon = np.array([0.0, 180.0])

    # Model and obs identical
    model_map = xr.DataArray(np.array([[0.5, 0.5], [1.0, 1.0], [-0.5, -0.5]]), dims=("lat", "lon"), coords={"lat": lat, "lon": lon})
    obs_map = model_map.copy()
    model_p = xr.full_like(model_map, 0.01)
    obs_p = xr.full_like(obs_map, 0.01)

    metrics = telecon.weighted_spatial_metrics(model_map, obs_map, model_p, obs_p, latitude_bounds=(-80.0, 80.0))
    assert np.isclose(float(metrics["pattern_correlation"]), 1.0)
    assert np.isclose(float(metrics["centered_rmse"]), 0.0)
    assert np.isclose(float(metrics["amplitude_ratio"]), 1.0)
    assert np.isclose(float(metrics["sign_agreement_fraction"]), 1.0)
    assert np.isclose(float(metrics["significant_overlap_area_fraction"]), 1.0)


def test_provenance_fingerprint():
    config = {
        "selection": {"upstream_index": "Nino3.4", "systems": ["E3SM-FOSIRL"]},
        "analysis": {"detrend": True},
    }
    with tempfile.NamedTemporaryFile() as tmp:
        p = Path(tmp.name)
        fp1 = telecon.compute_provenance_fingerprint(config, [p])
        fp2 = telecon.compute_provenance_fingerprint(config, [p])
        assert fp1 == fp2
        assert len(fp1) == 16


def test_standardize_spatial_grid_and_assemble():
    target_lat = np.linspace(-90.0, 90.0, 181)
    target_lon = np.linspace(0.0, 359.0, 360)

    # Atmosphere part on node grid with leads 3, 6
    da_atm = xr.DataArray(
        np.ones((1, 1, 1, 2, 181, 360)),
        dims=("system", "init_month", "variable", "L", "lat", "lon"),
        coords={
            "system": ["E3SM-FOSIRL"], "init_month": [5], "variable": ["TREFHT"],
            "L": [3, 6], "lat": target_lat, "lon": target_lon
        }
    )
    ds_atm = xr.Dataset({"model_correlation": da_atm, "pattern_correlation": xr.DataArray([1.0, 1.0], dims="L", coords={"L": [3, 6]}).expand_dims(system=["E3SM-FOSIRL"], init_month=[5], variable=["TREFHT"])})

    # Land part on cell-centered grid with lead 6 only
    land_lat = np.arange(-89.5, 90.0, 1.0)
    land_lon = np.arange(0.5, 360.0, 1.0)
    da_lnd = xr.DataArray(
        np.full((1, 1, 1, 1, 180, 360), 2.0),
        dims=("system", "init_month", "variable", "L", "lat", "lon"),
        coords={
            "system": ["E3SM-FOSIRL"], "init_month": [5], "variable": ["H2OSNO"],
            "L": [6], "lat": land_lat, "lon": land_lon
        }
    )
    ds_lnd = xr.Dataset({"model_correlation": da_lnd, "pattern_correlation": xr.DataArray([0.8], dims="L", coords={"L": [6]}).expand_dims(system=["E3SM-FOSIRL"], init_month=[5], variable=["H2OSNO"])})

    std_lnd = telecon.standardize_spatial_grid(ds_lnd, target_lat, target_lon)
    assert std_lnd["model_correlation"].shape == (1, 1, 1, 1, 181, 360)
    assert np.allclose(std_lnd["model_correlation"].values, 2.0)

    assembled = telecon.assemble_teleconnection_dataset([ds_atm, ds_lnd])
    assert set(assembled.variable.values) == {"TREFHT", "H2OSNO"}
    assert list(assembled.L.values) == [3, 6]
    assert assembled["model_correlation"].shape == (1, 1, 2, 2, 181, 360)
    # At L=3, H2OSNO should be NaN because it was only computed for L=6
    assert np.isnan(assembled["model_correlation"].sel(variable="H2OSNO", L=3).values).all()
    # At L=6, H2OSNO should be 2.0
    assert np.allclose(assembled["model_correlation"].sel(variable="H2OSNO", L=6).values, 2.0)
