"""Shared lead-time ACC skill-map helpers for the atmosphere and ocean realms.

``jupyter/1a_atm_leadtime_acc_skill_map.ipynb`` and
``jupyter/1a_ocn_leadtime_acc_skill_map.ipynb`` are, apart from their
``VAR_CONFIG``/``E3SM_CASES`` data and a handful of labels, the same workflow:
both build provenance-tracked, drift-removed E3SM and CESM-SMYLE anomaly
bundles from :func:`esp_lab.stats.remove_drift`, then compute and cache ACC
skill with :func:`esp_lab.leadtime_workflow.compute_skill_lead_range`. Before
this module existed, that orchestration was duplicated verbatim in both
notebooks (and duplicated again between the "E3SM case" and "CESM-SMYLE
benchmark" loops within each notebook) -- exactly the kind of duplication
that risks a silently wrong drift-removal formula or skill computation in one
copy but not the others.

This module factors out only the two steps where that risk concentrates:

* :func:`prepare_drift_removed_anomaly` -- the "load a compatible cached
  anomaly bundle, or remove drift and build/write/reopen one" step used for
  both the E3SM hindcast and the CESM-SMYLE benchmark.
* :func:`compute_and_cache_skill` -- the "load a compatible cached skill
  Dataset, or compute it over an inclusive seasonal lead range and cache it"
  step used for every case/month (and the CESM-SMYLE full-record and
  E3SM-overlap variants).
* :func:`common_finite_ocean_mask` -- the small "common all-finite domain
  across several unmasked prepared bundles" helper used by ocean-only fields
  (e.g. SST) to build one shared ocean mask before scoring.

These mirror the ``land_input_cache.prepare_model_cache`` /
``land_skill.compute_land_acc_skill`` split used by the already-refactored
land notebooks, adapted to the atm/ocn workflow's existing
``leadtime_prepared_cache`` / ``leadtime_skill_cache`` / ``leadtime_workflow``
cache-contract infrastructure (which the land modules do not use, since land
has its own simpler two-source-kind -- reference vs. model -- cache
contract).

Scope note
----------
This module intentionally does **not** yet cover the rest of the 1a
notebooks (raw E3SM/CESM-SMYLE loading and regridding, observation
preparation, prepared-input source-identity/cache-spec planning, the finite-
ensemble CESM-SMYLE-vs-E3SM significance comparison, or any of the
multi-panel plotting cells), nor the 1b (RMSE skill map) or 1c (RMSE
compare) notebooks or their ocean counterparts. Those remain inline and
duplicated between the atm and ocn notebooks. See the migration notes in
this repository's refactor history for why: the remaining cells are each
tens of thousands of characters of bespoke multi-panel plotting layout or
large, mostly self-contained statistical-resampling blocks, and porting them
faithfully needs the same careful, dedicated attention given here to the
drift-removal and skill-computation steps, which is why they were left for a
follow-up pass instead of being rushed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import xarray as xr

from . import stats
from .leadtime_prepared_cache import (
    build_prepared_skill_dataset,
    cache_status,
    open_prepared_skill_dataset,
    prepared_skill_cache_status,
    write_prepared_skill_dataset,
)
from .leadtime_workflow import compute_skill_lead_range
from .utils.netcdf_utils import atomic_to_netcdf, load_netcdf


ACC_SKILL_REQUIRED_VARIABLES = (
    "corr",
    "pval",
    "rmse",
    "msss",
    "rpc",
    "sig_obs",
    "sig_sig",
    "sig_tot",
    "s2t",
)


def prepare_drift_removed_anomaly(
    da: xr.DataArray,
    valid_time: xr.DataArray,
    *,
    prepared_path: str | Path,
    expected_attrs: Mapping,
    source: str,
    component: str,
    field: str,
    init_month: int,
    climatology_years: tuple[int, int],
    requested_years: Sequence[int],
    prepared_chunks: Mapping[str, int],
    reuse: bool = True,
    force_recompute: bool = False,
) -> xr.Dataset:
    """Load or build one provenance-tracked, drift-removed anomaly bundle.

    On a compatible cache hit (``reuse`` and not ``force_recompute``), the
    prepared bundle is opened and validated against ``expected_attrs``. On a
    miss, :func:`esp_lab.stats.remove_drift` is applied over
    ``climatology_years`` and the result is atomically written then reopened
    from disk, so downstream cells operate on a small graph instead of the
    full upstream lazy-processing chain.

    This is the exact "load-or-build" step used, identically, for both the
    E3SM hindcast anomaly and the CESM-SMYLE benchmark anomaly in the atm and
    ocn lead-time ACC notebooks; calling it from a per-case/month loop in the
    notebook (as :func:`esp_lab.land_input_cache.prepare_model_cache` is
    called from land's per-case/month loop) keeps the orchestration visible
    while sharing the drift-removal and cache-write/read logic itself.
    """
    climy0, climy1 = map(int, climatology_years)
    cache_compatible, _ = prepared_skill_cache_status(
        prepared_path, expected_attrs=expected_attrs
    )
    if reuse and cache_compatible and not force_recompute:
        print(f"Loading prepared input: {prepared_path}")
        return open_prepared_skill_dataset(
            prepared_path, expected_attrs=expected_attrs, chunks=prepared_chunks
        )

    print(f"Creating prepared input: {prepared_path}")
    anomaly, climatology = stats.remove_drift(da, valid_time, climy0, climy1)
    prepared = build_prepared_skill_dataset(
        anomaly,
        climatology,
        valid_time,
        source=source,
        component=component,
        variable=field,
        init_month=init_month,
        climatology_years=(climy0, climy1),
        source_data_identity=expected_attrs["source_data_identity"],
        case_prefix=expected_attrs["case_prefix"],
        requested_years=requested_years,
        target_grid=expected_attrs["target_grid"],
        regridding_method=expected_attrs["regridding_method"],
        ensemble_member_count=expected_attrs["ensemble_member_count"],
        lead_count=expected_attrs["lead_count"],
        unit_conversion_version=expected_attrs["unit_conversion_version"],
    )
    write_prepared_skill_dataset(prepared, prepared_path)
    return open_prepared_skill_dataset(
        prepared_path, expected_attrs=expected_attrs, chunks=prepared_chunks
    )


def compute_and_cache_skill(
    model_anom: xr.DataArray,
    model_time: xr.DataArray,
    observations: xr.DataArray,
    clim_start,
    clim_end,
    lead_start: int,
    lead_end: int,
    *,
    outfile: str | Path,
    expected_attrs: Mapping,
    netcdf_write_options: Mapping,
    detrend: bool,
    force_compute: bool = False,
    required_variables: Sequence[str] = ACC_SKILL_REQUIRED_VARIABLES,
) -> xr.Dataset:
    """Load a compatible cached skill Dataset, or compute and cache one.

    Wraps :func:`esp_lab.leadtime_workflow.compute_skill_lead_range` (an
    inclusive, one-based seasonal lead range, no multi-year averaging) with
    the same "check compatibility, reuse or recompute, write atomically"
    contract used identically for the E3SM per-case/month skill, the
    CESM-SMYLE full-record skill, and the CESM-SMYLE E3SM-overlap skill in
    the atm and ocn lead-time ACC notebooks.
    """
    outfile = Path(outfile)
    compatible, reason = cache_status(
        outfile, expected_attrs=expected_attrs, required_variables=required_variables
    )
    if compatible and not force_compute:
        return load_netcdf(outfile)

    if outfile.exists() and not force_compute:
        print(f"Ignoring incompatible skill cache {outfile}: {reason}")

    skill = compute_skill_lead_range(
        model_anom,
        model_time,
        observations,
        clim_start,
        clim_end,
        lead_start,
        lead_end,
        resamp=0,
        detrend=detrend,
    )
    skill_ds = skill.assign_attrs(expected_attrs).compute()
    atomic_to_netcdf(skill_ds, outfile, **dict(netcdf_write_options))
    return skill_ds


def common_finite_ocean_mask(samples: Sequence[xr.DataArray]) -> xr.DataArray:
    """Return the common all-finite domain across several unmasked samples.

    Each entry of ``samples`` should be one representative (e.g. a single
    ``Y``/``M``/``L`` slice) finite/non-finite mask sharing identical
    coordinates; the result keeps only cells finite in every sample. Used by
    ocean-only fields (e.g. SST) to build one common ocean mask across every
    configured E3SM case and the CESM-SMYLE benchmark before applying it to
    every prepared anomaly bundle and the observations, so every downstream
    skill product shares an identical spatial domain.
    """
    if not samples:
        raise ValueError("samples must contain at least one mask")
    aligned = xr.align(*samples, join="exact")
    return xr.concat(aligned, dim="mask_source").all("mask_source").compute()


__all__ = [
    "ACC_SKILL_REQUIRED_VARIABLES",
    "common_finite_ocean_mask",
    "compute_and_cache_skill",
    "prepare_drift_removed_anomaly",
]
