"""Monthly standardized RMSE/MAE derived from initial-shock indices.

The primary metrics use the shared-observation monthly climatology prepared by
``initial_shock.compute_initial_shock_index``.  The former independently
centered annual-block calculation remains available as an explicit legacy
helper for comparisons with the original NCL diagnostic.
"""
from __future__ import annotations

import numpy as np
import xarray as xr

VERSION = "initial_shock_rmse_mae_v3"
NCL_RMSE_RANGES = (0.15, 0.20, 0.25, 0.30, 0.35, 0.40)
NCL_MAE_RANGES = (0.13, 0.16, 0.19, 0.22, 0.25, 0.28)
NCL_COLORS = ("white", "orange", "#cd8500", "orangered", "#ff4500", "#cd3700", "#8b2500")


def compute_legacy_initial_shock_error_index(
    indices: xr.Dataset, *, min_samples: int | None = None,
) -> xr.Dataset:
    """Compute NCL-style anomaly RMSE and MAE for every initialization.

    ``indices`` must contain ``model_index`` and ``observation_index`` on
    ``(Y, block)`` plus any shared outer dimensions such as ``case``. As in the
    NCL script, each series is centered on its own mean over the full Y/block
    cohort. RMSE and MAE are then calculated over paired blocks within each Y.
    """
    required = {"model_index", "observation_index"}
    if not required <= set(indices.data_vars):
        raise ValueError(f"indices must contain {sorted(required)}")
    model, observation = xr.align(
        indices.model_index, indices.observation_index, join="exact"
    )
    if "Y" not in model.dims or "block" not in model.dims:
        raise ValueError("model_index and observation_index must contain Y and block")
    if model.dims != observation.dims:
        raise ValueError("model and observation indices must have identical dimensions")
    nblocks = model.sizes["block"]
    min_samples = nblocks if min_samples is None else min_samples
    if not isinstance(min_samples, (int, np.integer)) or not 1 <= min_samples <= nblocks:
        raise ValueError("min_samples must be between 1 and the number of blocks")
    model = model.where(np.isfinite(model))
    observation = observation.where(np.isfinite(observation))
    baseline_dims = ("Y", "block")
    model_climatology = model.mean(baseline_dims, skipna=True)
    observation_climatology = observation.mean(baseline_dims, skipna=True)
    model_anomaly = model - model_climatology
    observation_anomaly = observation - observation_climatology
    paired = model_anomaly.notnull() & observation_anomaly.notnull()
    error = (model_anomaly - observation_anomaly).where(paired)
    count = paired.sum("block")
    valid = count >= min_samples
    rmse = np.sqrt((error ** 2).sum("block", skipna=True) / count.where(count > 0)).where(valid)
    mae = (abs(error).sum("block", skipna=True) / count.where(count > 0)).where(valid)
    if "observation_climatology_std" in indices:
        observation_scale = indices.observation_climatology_std
    else:
        observation_scale = observation.isel(block=0).std("Y", ddof=1, skipna=True)
    observation_scale = observation_scale.where(
        np.isfinite(observation_scale) & (observation_scale > 0)
    )
    normalized_rmse = rmse / observation_scale
    normalized_mae = mae / observation_scale
    units = model.attrs.get("units", observation.attrs.get("units", ""))
    if model.attrs.get("units") and observation.attrs.get("units") and model.attrs["units"] != observation.attrs["units"]:
        raise ValueError("Model and observation index units differ")
    result = xr.Dataset({
        "rmse": rmse,
        "mae": mae,
        "normalized_rmse": normalized_rmse,
        "normalized_mae": normalized_mae,
        "observation_climatology_std": observation_scale,
        "paired_sample_count": count,
        "valid_metric": valid.astype("int8"),
        "model_climatology": model_climatology,
        "observation_climatology": observation_climatology,
        "model_anomaly": model_anomaly,
        "observation_anomaly": observation_anomaly,
        "error": error,
    })
    for name in ("rmse", "mae", "observation_climatology_std",
                 "model_climatology", "observation_climatology",
                 "model_anomaly", "observation_anomaly", "error"):
        result[name].attrs["units"] = units
    result.rmse.attrs["long_name"] = "Root mean square error of global-index anomalies"
    result.mae.attrs["long_name"] = "Mean absolute error of global-index anomalies"
    result.normalized_rmse.attrs.update(
        units="1",
        long_name="RMSE of global-index anomalies normalized by observed climatological standard deviation",
    )
    result.normalized_mae.attrs.update(
        units="1",
        long_name="MAE of global-index anomalies normalized by observed climatological standard deviation",
    )
    result.attrs.update(
        diagnostic_version=VERSION,
        min_samples=int(min_samples),
        anomaly_baseline="independent model and observation means over Y and block",
        error_reduction="paired blocks within each initialization; population mean",
        interpretation="Error amplitude after removing each series' full-cohort mean",
        normalized_error_denominator="sample std of observed first-block annual means across initialization years",
    )
    return result


def _paired_metrics(error: xr.DataArray, dim, min_samples: int):
    """Return RMSE, MAE, count and validity for finite paired errors."""
    finite = error.where(np.isfinite(error))
    count = finite.notnull().sum(dim)
    valid = count >= min_samples
    denominator = count.where(count > 0)
    rmse = np.sqrt((finite ** 2).sum(dim, skipna=True) / denominator).where(valid)
    mae = (abs(finite).sum(dim, skipna=True) / denominator).where(valid)
    return rmse, mae, count, valid


def compute_initial_shock_error_index(
    indices: xr.Dataset,
    *,
    min_samples: int | None = None,
    seasonal_min_samples: int = 3,
) -> xr.Dataset:
    """Compute monthly standardized forecast errors for every initialization.

    ``indices`` is the output of :func:`compute_initial_shock_index` and must
    contain ensemble-mean and first-member monthly indices, the paired observed
    index, and the ensemble-mean standardized error.  The latter uses one
    shared observed calendar-month climatology and observed monthly standard
    deviation for all cases and initialization cohorts.

    The primary RMSE/MAE reduce all available forecast months within each
    initialization.  Seasonal diagnostics retain lead year and verification
    season and reduce the three constituent standardized monthly errors.
    """
    required = {
        "monthly_model_index",
        "monthly_first_member_index",
        "monthly_observation_index",
        "monthly_observation_climatology_std",
        "monthly_standardized_error",
    }
    if not required <= set(indices.data_vars):
        missing = sorted(required - set(indices.data_vars))
        raise ValueError(f"indices missing monthly shared-climatology variables: {missing}")

    ensemble_error = indices.monthly_standardized_error
    expected_dims = {"Y", "lead_month"}
    if set(ensemble_error.dims) != expected_dims:
        raise ValueError("monthly_standardized_error must have dimensions Y and lead_month")
    nmonths = ensemble_error.sizes["lead_month"]
    if nmonths < 3 or nmonths % 3:
        raise ValueError("monthly error window must contain complete three-month seasons")
    min_samples = nmonths if min_samples is None else min_samples
    if (
        not isinstance(min_samples, (int, np.integer))
        or not 1 <= min_samples <= nmonths
    ):
        raise ValueError("min_samples must be between 1 and the number of lead months")
    if (
        not isinstance(seasonal_min_samples, (int, np.integer))
        or not 1 <= seasonal_min_samples <= 3
    ):
        raise ValueError("seasonal_min_samples must be between 1 and 3")

    model, first_member, observation, ensemble_error = xr.align(
        indices.monthly_model_index,
        indices.monthly_first_member_index,
        indices.monthly_observation_index,
        ensemble_error,
        join="exact",
    )
    for data in (model, first_member, observation):
        if set(data.dims) != expected_dims:
            raise ValueError("monthly indices must have dimensions Y and lead_month")
    units = model.attrs.get("units", observation.attrs.get("units", ""))
    if model.attrs.get("units") and observation.attrs.get("units"):
        if model.attrs["units"] != observation.attrs["units"]:
            raise ValueError("Model and observation index units differ")

    raw_error = (model - observation).where(
        np.isfinite(model) & np.isfinite(observation)
    )
    first_member_raw_error = (first_member - observation).where(
        np.isfinite(first_member) & np.isfinite(observation)
    )

    monthly_scale = indices.monthly_observation_climatology_std
    if set(monthly_scale.dims) != {"month_phase"} or monthly_scale.sizes["month_phase"] != 12:
        raise ValueError(
            "monthly_observation_climatology_std must contain 12 month_phase values"
        )
    if "calendar_month" not in indices.coords:
        raise ValueError("indices must contain calendar_month(lead_month)")
    scale_by_lead = xr.concat(
        [monthly_scale.sel(month_phase=int(month)) for month in indices.calendar_month.values],
        dim=xr.IndexVariable("lead_month", indices.lead_month.values),
    )
    scale_by_lead = scale_by_lead.where(np.isfinite(scale_by_lead) & (scale_by_lead > 0))
    first_member_error = (first_member_raw_error / scale_by_lead).where(
        first_member_raw_error.notnull() & scale_by_lead.notnull()
    )

    normalized_rmse, normalized_mae, count, valid = _paired_metrics(
        ensemble_error, "lead_month", int(min_samples)
    )
    first_rmse, first_mae, first_count, first_valid = _paired_metrics(
        first_member_error, "lead_month", int(min_samples)
    )
    rmse, mae, raw_count, raw_valid = _paired_metrics(
        raw_error, "lead_month", int(min_samples)
    )

    nseasons = nmonths // 3
    if nseasons % 4:
        raise ValueError("monthly error window must contain complete four-season lead years")
    nlead_years = nseasons // 4
    season_coord = np.arange(1, 5)
    lead_year_coord = np.arange(1, nlead_years + 1)

    def reshape_seasons(data):
        values = np.asarray(data.transpose("Y", "lead_month"))
        return xr.DataArray(
            values.reshape(data.sizes["Y"], nlead_years, 4, 3),
            dims=("Y", "lead_year", "season", "season_month"),
            coords={
                "Y": data.Y,
                "lead_year": lead_year_coord,
                "season": season_coord,
                "season_month": np.arange(1, 4),
            },
        )

    seasonal_error = reshape_seasons(ensemble_error)
    seasonal_first_error = reshape_seasons(first_member_error)
    seasonal_rmse, seasonal_mae, seasonal_count, seasonal_valid = _paired_metrics(
        seasonal_error, "season_month", int(seasonal_min_samples)
    )
    seasonal_first_rmse, seasonal_first_mae, seasonal_first_count, seasonal_first_valid = (
        _paired_metrics(seasonal_first_error, "season_month", int(seasonal_min_samples))
    )

    result = xr.Dataset({
        "normalized_rmse": normalized_rmse,
        "normalized_mae": normalized_mae,
        "first_member_normalized_rmse": first_rmse,
        "first_member_normalized_mae": first_mae,
        "rmse": rmse,
        "mae": mae,
        "monthly_standardized_error": ensemble_error,
        "monthly_first_member_standardized_error": first_member_error,
        "monthly_raw_error": raw_error,
        "monthly_first_member_raw_error": first_member_raw_error,
        "paired_sample_count": count,
        "first_member_paired_sample_count": first_count,
        "valid_metric": valid.astype("int8"),
        "first_member_valid_metric": first_valid.astype("int8"),
        "seasonal_normalized_rmse": seasonal_rmse,
        "seasonal_normalized_mae": seasonal_mae,
        "seasonal_first_member_normalized_rmse": seasonal_first_rmse,
        "seasonal_first_member_normalized_mae": seasonal_first_mae,
        "seasonal_paired_sample_count": seasonal_count,
        "seasonal_first_member_paired_sample_count": seasonal_first_count,
        "valid_seasonal_metric": seasonal_valid.astype("int8"),
        "valid_seasonal_first_member_metric": seasonal_first_valid.astype("int8"),
    })
    for name in ("rmse", "mae", "monthly_raw_error", "monthly_first_member_raw_error"):
        result[name].attrs["units"] = units
    for name in (
        "normalized_rmse", "normalized_mae",
        "first_member_normalized_rmse", "first_member_normalized_mae",
        "monthly_standardized_error", "monthly_first_member_standardized_error",
        "seasonal_normalized_rmse", "seasonal_normalized_mae",
        "seasonal_first_member_normalized_rmse",
        "seasonal_first_member_normalized_mae",
    ):
        result[name].attrs["units"] = "1"
    if "season_label" in indices.coords:
        result = result.assign_coords(season_label=indices.season_label)
    result.attrs.update(
        diagnostic_version=VERSION,
        min_samples=int(min_samples),
        seasonal_min_samples=int(seasonal_min_samples),
        anomaly_baseline="shared reference-observation calendar-month climatology",
        normalized_error_denominator="observed calendar-month climatological standard deviation",
        error_reduction="paired standardized monthly errors within each initialization",
        interpretation="forecast error amplitude in observed month-specific variability units",
    )
    return result


def plot_error_heatmap(
    result: xr.Dataset,
    *,
    variable: str,
    levels,
    ax=None,
    add_colorbar: bool = True,
    add_invalid_legend: bool = True,
    title: str | None = None,
):
    """Plot one raw or normalized error metric with explicit color levels."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm
    from matplotlib.patches import Patch

    allowed = {
        "rmse", "mae", "normalized_rmse", "normalized_mae",
        "first_member_normalized_rmse", "first_member_normalized_mae",
    }
    if variable not in allowed:
        raise ValueError(f"variable must be one of {sorted(allowed)}")
    if variable not in result:
        raise ValueError(f"result does not contain {variable!r}")
    bounds = np.asarray(levels, dtype=float)
    if bounds.ndim != 1 or bounds.size < 2:
        raise ValueError("levels must contain at least two one-dimensional boundaries")
    if not np.isfinite(bounds).all() or bounds[0] < 0 or not np.all(np.diff(bounds) > 0):
        raise ValueError("levels must be finite, nonnegative, and strictly increasing")

    values = result[variable]
    if "case" not in values.dims:
        values = values.expand_dims(case=[result.attrs.get("case", "model")])
    values = values.transpose("Y", "case")
    cmap = plt.colormaps["YlOrRd"].resampled(bounds.size - 1).with_extremes(
        bad="#bdbdbd", over="#4a0000"
    )
    owns_figure = ax is None
    if owns_figure:
        fig, ax = plt.subplots(
            figsize=(max(6, values.sizes["case"] * 1.5), max(3, values.sizes["Y"] * .25))
        )
    else:
        fig = ax.figure
    mesh = ax.imshow(
        values.values, aspect="auto", cmap=cmap,
        norm=BoundaryNorm(bounds, cmap.N),
    )
    ax.set_xticks(
        np.arange(values.sizes["case"]), labels=values.case.values,
        rotation=30, ha="right",
    )
    ax.set_yticks(
        np.arange(values.sizes["Y"]), labels=[str(value) for value in values.Y.values]
    )
    ax.set_xticks(np.arange(-.5, values.sizes["case"], 1), minor=True)
    ax.set_yticks(np.arange(-.5, values.sizes["Y"], 1), minor=True)
    ax.grid(which="minor", color="#d9d9d9", linewidth=.6)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.set_ylabel("Initialization year")
    ax.set_title(title if title is not None else values.attrs.get("long_name", variable))
    if add_colorbar:
        units = "1" if variable.startswith("normalized_") else values.attrs.get("units", "")
        label = variable.replace("normalized_", "Normalized ").upper()
        if units and units != "1":
            label += f" ({units})"
        colorbar = fig.colorbar(mesh, ax=ax, ticks=bounds, label=label, extend="max")
        colorbar.ax.set_yticklabels([f"{value:g}" for value in bounds])
    if add_invalid_legend:
        ax.legend(
            handles=[Patch(facecolor=cmap.get_bad(), edgecolor="none", label="Invalid / missing")],
            loc="upper left", bbox_to_anchor=(1.01, 0), frameon=False, fontsize="small",
        )
    if owns_figure:
        fig.tight_layout()
    return fig


def plot_rmse_mae(
    result: xr.Dataset, *, rmse_ranges=NCL_RMSE_RANGES, mae_ranges=NCL_MAE_RANGES,
):
    """Plot RMSE and MAE panels using the color thresholds from the NCL figure."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap

    if not {"rmse", "mae"} <= set(result):
        raise ValueError("result must contain rmse and mae")
    data = result if "case" in result.dims else result.expand_dims(case=["model"])
    if "Y" not in data.dims:
        raise ValueError("result must contain Y")
    checked_ranges = []
    for ranges in (rmse_ranges, mae_ranges):
        ranges = tuple(map(float, ranges))
        if (len(ranges) != len(NCL_COLORS) - 1 or
                not np.isfinite(ranges).all() or
                ranges[0] <= 0 or not np.all(np.diff(ranges) > 0)):
            raise ValueError("Plot ranges must contain six increasing positive finite values")
        checked_ranges.append(ranges)
    cmap = ListedColormap(NCL_COLORS).with_extremes(bad="#d9d9d9")
    fig, axes = plt.subplots(2, 1, figsize=(max(8, data.sizes["case"] * 1.2), 9), sharex=True)
    units = data.rmse.attrs.get("units", "")
    for ax, name, ranges, title in zip(
        axes, ("rmse", "mae"), checked_ranges,
        ("(a) Root Mean Square Error", "(b) Mean Absolute Error"), strict=True,
    ):
        values = data[name].transpose("Y", "case")
        finite = np.asarray(values).astype(float)
        finite = finite[np.isfinite(finite)]
        upper = max(float(ranges[-1]) + np.finfo(float).eps,
                    float(finite.max()) if finite.size else float(ranges[-1]) * 1.01)
        if upper <= ranges[-1]:
            upper = float(ranges[-1]) * 1.01
        boundaries = (0.0, *ranges, upper)
        mesh = ax.pcolormesh(
            np.arange(data.sizes["case"] + 1), np.arange(data.sizes["Y"] + 1), values,
            cmap=cmap, norm=BoundaryNorm(boundaries, cmap.N, clip=True),
            edgecolors="black", linewidth=.7,
        )
        ax.set_yticks(np.arange(data.sizes["Y"]) + .5, labels=[str(v) for v in data.Y.values])
        ax.set_ylabel("Initialization")
        ax.set_title(title, loc="left")
        fig.colorbar(mesh, ax=ax, ticks=ranges, label=f"{name.upper()} ({units})" if units else name.upper())
    axes[-1].set_xticks(
        np.arange(data.sizes["case"]) + .5,
        labels=[str(v) for v in data.case.values], rotation=45, ha="right",
    )
    fig.tight_layout()
    return fig
