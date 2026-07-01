#!/usr/bin/env python
"""Generate Yeager f03/f04-style NMME Nino3.4 diagnostics.

This workflow reads the member-split NMME hindcast archive produced under
``data_hindcast_by_member/<model>/sst/M###/*.nc``, computes Nino3.4 SST
anomalies using the same broad method as Yeager et al. GMD 2022 f03/f04,
evaluates ACC and nRMSE against HadISST2, and writes f03/f04-style outputs.
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import cftime
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from esp_lab import stats
from esp_lab.utils import calendar_utils as cal


DEFAULT_NMME_ROOT = Path("/global/cfs/cdirs/e3sm/S2S2D/NMME/data_hindcast_by_member")
DEFAULT_OBS_FILE = Path(
    "/global/cfs/cdirs/e3sm/diagnostics/observations/Atm/time-series/"
    "HadISST2/sst_186901_202212.nc"
)
DEFAULT_OUTDIR = Path("/global/cfs/cdirs/e3sm/S2S2D/s2d_diag/NMME")
DEFAULT_FIGDIR = Path("/global/cfs/cdirs/e3sm/www/zhan391/esp-lab_diag")
YEAGER_F03_MODELS = [
    "CMC1-CanCM3",
    "CMC2-CanCM4",
    "COLA-RSMAS-CCSM4",
    "GFDL-CM2p1-aer04",
    "GFDL-CM2p5-FLOR-A06",
    "GFDL-CM2p5-FLOR-B01",
    "NASA-GMAO-062012",
    "NCEP-CFSv2",
]
SPLIT_CLIMO_MODELS = {"COLA-RSMAS-CCSM4", "NCEP-CFSv2"}
INIT_MONTHS = [2, 5, 8, 11]
NINO34_LONLAT = [-170.0, -120.0, -5.0, 5.0]
SEASON_LABELS_BY_MONTH = {
    2: ["MAM", "JJA", "SON", "DJF", "MAM", "JJA", "SON"],
    5: ["JJA", "SON", "DJF", "MAM", "JJA", "SON", "DJF"],
    8: ["SON", "DJF", "MAM", "JJA", "SON", "DJF", "MAM"],
    11: ["DJF", "MAM", "JJA", "SON", "DJF", "MAM", "JJA"],
}


def _decode_cf_time(ds: xr.Dataset, time_var: str = "S") -> xr.Dataset:
    ds = ds.copy()
    if ds[time_var].attrs.get("calendar") == "360":
        ds[time_var].attrs["calendar"] = "360_day"
    return xr.decode_cf(ds, decode_times=True)


def _member_number(member_dir: Path) -> int:
    return int(member_dir.name.removeprefix("M"))


def _sorted_member_dirs(model_dir: Path) -> list[Path]:
    dirs = [p for p in (model_dir / "sst").glob("M*") if p.is_dir()]
    return sorted(dirs, key=_member_number)


def discover_sst_models(root: Path) -> list[str]:
    """Discover downloaded NMME SST models in the member-split archive."""
    models = []
    for model_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if model_dir.name == "logs":
            continue
        if _sorted_member_dirs(model_dir):
            models.append(model_dir.name)
    return models


def _open_member_sst(member_dir: Path, model: str) -> xr.Dataset:
    files = sorted(member_dir.glob(f"sst_{model}_{member_dir.name}_S*.nc"))
    if not files:
        raise FileNotFoundError(f"No SST chunks found under {member_dir}")
    ds = xr.open_mfdataset(
        files,
        combine="by_coords",
        decode_times=False,
        chunks={"S": 12, "L": -1, "Y": 181, "X": 360},
        parallel=False,
    )
    ds = _decode_cf_time(ds, "S")
    ds = ds.sel(S=slice("1982-01-01", "2016-12-30"))
    return ds


def _regional_mean_nino34(ds: xr.Dataset) -> xr.DataArray:
    lon_w, lon_e, lat_s, lat_n = NINO34_LONLAT
    lon1 = lon_w % 360.0
    lon2 = lon_e % 360.0
    tmp = ds["sst"].sel(Y=slice(lat_s, lat_n), X=slice(lon1, lon2))
    weights = np.cos(np.deg2rad(tmp["Y"]))
    return tmp.weighted(weights).mean(("X", "Y"), skipna=True).rename("sst")


def _remove_init_month_climatology(regsst: xr.DataArray, model: str) -> xr.DataArray:
    if model in SPLIT_CLIMO_MODELS:
        parts = []
        for start, end in [("1982-01-01", "1998-12-30"), ("1999-01-01", "2016-12-30")]:
            part = regsst.sel(S=slice(start, end))
            parts.append(part.groupby("S.month") - part.groupby("S.month").mean(("S", "M")))
        return xr.concat(parts, dim="S")
    return regsst.groupby("S.month") - regsst.groupby("S.month").mean(("S", "M"))


def load_or_compute_model_regsst(
    root: Path,
    outdir: Path,
    model: str,
    *,
    force: bool = False,
) -> xr.DataArray:
    cache_file = outdir / "processed" / f"NMME_{model}_Nino34SST_mon_anom_1982_2016.nc"
    if cache_file.exists() and not force:
        return xr.open_dataset(cache_file)["sst"]

    model_dir = root / model
    if not model_dir.is_dir():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")

    members = []
    member_ids = []
    for member_dir in _sorted_member_dirs(model_dir):
        member_id = _member_number(member_dir)
        print(f"[NMME] {model} {member_dir.name}")
        with _open_member_sst(member_dir, model) as ds:
            reg = _regional_mean_nino34(ds).load()
        members.append(reg)
        member_ids.append(member_id)

    if not members:
        raise ValueError(f"No members found for {model}")

    member_coord = xr.DataArray(member_ids, dims="M", name="M")
    regsst = xr.concat(members, dim=member_coord)
    regsst = regsst.assign_coords(L=np.arange(regsst.sizes["L"]) + 1)
    regsst = _remove_init_month_climatology(regsst, model)
    regsst.attrs.update(
        {
            "long_name": f"{model} NMME Nino3.4 SST anomaly",
            "units": "degC",
            "region": "5S-5N, 170W-120W",
            "source": str(model_dir),
        }
    )

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    regsst.to_dataset(name="sst").to_netcdf(
        cache_file,
        encoding={"S": {"units": "days since 1960-01-01", "calendar": "360_day"}},
    )
    print(f"[NMME] wrote {cache_file}")
    return regsst


def _add_months(year: int, month: int, offset: int) -> cftime.DatetimeNoLeap:
    month_index = month - 1 + offset
    return cftime.DatetimeNoLeap(year + month_index // 12, month_index % 12 + 1, 15)


def subset_init_month(da: xr.DataArray, init_month: int) -> tuple[xr.DataArray, xr.DataArray]:
    init_times = da["S"].where(da["S"].dt.month == init_month, drop=True)
    out = da.sel(S=init_times).rename({"S": "Y"}).assign_coords(Y=init_times.dt.year.data)
    out = out.assign_coords(L=np.arange(out.sizes["L"]) + 1)

    years = out["Y"].values.astype(int)
    leads = out["L"].values.astype(int)
    valid_time = xr.DataArray(
        np.array(
            [[_add_months(int(year), init_month, int(lead) - 1) for lead in leads] for year in years],
            dtype=object,
        ),
        dims=("Y", "L"),
        coords={"Y": years, "L": leads},
        name="time",
    )
    return out, valid_time


def _standardize_obs(ds: xr.Dataset, var: str) -> xr.DataArray:
    rename = {}
    if "latitude" in ds.coords:
        rename["latitude"] = "lat"
    if "longitude" in ds.coords:
        rename["longitude"] = "lon"
    ds = ds.rename(rename)
    if ds["lat"][0] > ds["lat"][-1]:
        ds = ds.reindex(lat=ds.lat[::-1])
    if ds["lon"].min() >= 0:
        lon = (((ds["lon"] + 180) % 360) - 180).astype(ds["lon"].dtype)
        ds = ds.assign_coords(lon=lon).sortby("lon")
    sst = ds[var]
    return xr.where(sst < -2.0, -1.8, sst)


def load_obs_nino34(obs_file: Path, obs_var: str) -> tuple[xr.DataArray, xr.DataArray]:
    ds = xr.open_dataset(obs_file)
    sst = _standardize_obs(ds, obs_var).sel(time=slice("1960-01-01", "2022-12-31"))
    lon_w, lon_e, lat_s, lat_n = NINO34_LONLAT
    tmp = sst.sel(lat=slice(lat_s, lat_n), lon=slice(lon_w, lon_e))
    weights = np.cos(np.deg2rad(tmp["lat"]))
    obs_mon = tmp.weighted(weights).mean(("lon", "lat"), skipna=True).rename("sst")
    obs_seas = obs_mon.rolling(time=3, min_periods=3, center=True).mean().dropna("time", how="all")
    return obs_mon.load(), obs_seas.load()


def process_nmme(
    root: Path,
    outdir: Path,
    models: list[str],
    clim_start: int,
    clim_end: int,
    *,
    force: bool = False,
) -> dict[str, dict[int, xr.DataArray] | xr.DataArray]:
    reg_models = []
    loaded_models = []
    for model in models:
        try:
            reg = load_or_compute_model_regsst(root, outdir, model, force=force)
        except Exception as exc:
            warnings.warn(f"[NMME] skipping {model}: {exc}", stacklevel=2)
            continue
        reg_models.append(reg.expand_dims(model=[model]))
        loaded_models.append(model)

    if not reg_models:
        raise ValueError("No NMME models could be loaded")

    nmme_regsst = xr.concat(
        reg_models,
        dim="model",
        join="outer",
        coords="minimal",
        compat="override",
    )
    monthly = {}
    monthly_time = {}
    seasonal = {}
    seasonal_time = {}
    monthly_dd = {}
    seasonal_dd = {}
    monthly_drift = {}
    seasonal_drift = {}

    for init_month in INIT_MONTHS:
        da_mon, time_mon = subset_init_month(nmme_regsst, init_month)
        ds_mon = da_mon.to_dataset(name="sst")
        ds_mon["time"] = time_mon
        da_seas = cal.mon_to_seas_dask(ds_mon)["sst"]
        time_seas = ds_mon["time"].sel(L=da_seas["L"])

        dd_mon, drift_mon = stats.remove_drift(da_mon, time_mon, clim_start, clim_end)
        dd_seas, drift_seas = stats.remove_drift(da_seas, time_seas, clim_start, clim_end)

        monthly[init_month] = da_mon
        monthly_time[init_month] = time_mon
        seasonal[init_month] = da_seas
        seasonal_time[init_month] = time_seas
        monthly_dd[init_month] = dd_mon
        seasonal_dd[init_month] = dd_seas
        monthly_drift[init_month] = drift_mon
        seasonal_drift[init_month] = drift_seas

    return {
        "models": xr.DataArray(loaded_models, dims="model", name="model"),
        "monthly": monthly,
        "monthly_time": monthly_time,
        "seasonal": seasonal,
        "seasonal_time": seasonal_time,
        "monthly_dd": monthly_dd,
        "seasonal_dd": seasonal_dd,
        "monthly_drift": monthly_drift,
        "seasonal_drift": seasonal_drift,
    }


def compute_nmme_skill(
    processed: dict[str, dict[int, xr.DataArray] | xr.DataArray],
    obs_mon: xr.DataArray,
    obs_seas: xr.DataArray,
    clim_start: int,
    clim_end: int,
) -> dict[str, xr.Dataset]:
    seas = {}
    seas_mmm = {}
    mon = {}
    mon_mmm = {}
    for init_month in INIT_MONTHS:
        seas[init_month] = stats.compute_skill_seasonal(
            processed["seasonal_dd"][init_month],
            processed["seasonal_time"][init_month],
            obs_seas,
            str(clim_start),
            str(clim_end),
            1,
            4,
            resamp=0,
            detrend=True,
        )
        seas_mmm[init_month] = stats.compute_skill_seasonal(
            processed["seasonal_dd"][init_month].mean("M").rename({"model": "M"}),
            processed["seasonal_time"][init_month],
            obs_seas,
            str(clim_start),
            str(clim_end),
            1,
            4,
            resamp=0,
            detrend=True,
        )
        mon[init_month] = stats.compute_skill_seasonal(
            processed["monthly_dd"][init_month],
            processed["monthly_time"][init_month],
            obs_mon,
            str(clim_start),
            str(clim_end),
            1,
            12,
            resamp=0,
            detrend=True,
            monthly=True,
        )
        mon_mmm[init_month] = stats.compute_skill_seasonal(
            processed["monthly_dd"][init_month].mean("M").rename({"model": "M"}),
            processed["monthly_time"][init_month],
            obs_mon,
            str(clim_start),
            str(clim_end),
            1,
            12,
            resamp=0,
            detrend=True,
            monthly=True,
        )

    startmonth = xr.DataArray(INIT_MONTHS, name="startmonth", dims="startmonth")
    return {
        "nmme_seas_skill": xr.concat([seas[m] for m in INIT_MONTHS], dim=startmonth),
        "nmme_seas_skill_mmm": xr.concat([seas_mmm[m] for m in INIT_MONTHS], dim=startmonth),
        "nmme_skill": xr.concat([mon[m] for m in INIT_MONTHS], dim=startmonth),
        "nmme_skill_mmm": xr.concat([mon_mmm[m] for m in INIT_MONTHS], dim=startmonth),
    }


def save_outputs(
    outdir: Path,
    processed: dict[str, dict[int, xr.DataArray] | xr.DataArray],
    skill: dict[str, xr.Dataset],
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    skill_ds = xr.Dataset()
    for name, ds in skill.items():
        for var in ds.data_vars:
            skill_ds[f"{name}_{var}"] = ds[var]
    skill_ds.attrs["description"] = "NMME Nino3.4 skill diagnostics following Yeager f03/f04 conventions"
    skill_ds.to_netcdf(outdir / "NMME_Nino34_skill_1982_2016.nc")

    for init_month in INIT_MONTHS:
        ds = xr.Dataset(
            {
                "sst": processed["seasonal_dd"][init_month],
                "time": processed["seasonal_time"][init_month],
            }
        )
        ds.to_netcdf(outdir / f"NMME{init_month:02d}_Nino34SST_seas_dd.nc")


def plot_f03_like(skill: dict[str, xr.Dataset], figdir: Path) -> Path:
    nmme_seas_skill = skill["nmme_seas_skill"]
    nmme_seas_skill_mmm = skill["nmme_seas_skill_mmm"]
    nmme_skill = skill["nmme_skill"]
    nmme_skill_mmm = skill["nmme_skill_mmm"]

    fig = plt.figure(figsize=(18, 20))
    plt.rcParams.update({"font.size": 14})
    leadsea = nmme_seas_skill.L - 2
    hindcasts = ["FEB init", "MAY init", "AUG init", "NOV init", "ALL init average"]
    figlabs = [["a.", "c.", "e.", "g.", "i."], ["b.", "d.", "f.", "h.", "j."]]
    nrow = 5
    ncol = 2

    for j, init_month in enumerate(INIT_MONTHS):
        ax = fig.add_subplot(nrow, ncol, j * 2 + 1)
        ax2 = fig.add_subplot(nrow, ncol, j * 2 + 2)
        ax.set_title(figlabs[0][j] + " " + hindcasts[j], loc="left")
        ax2.set_title(figlabs[1][j] + " " + hindcasts[j], loc="left")
        if j == 0:
            ax.set_title("ACC", loc="center")
            ax2.set_title("nRMSE", loc="center")

        tmp = nmme_seas_skill_mmm.sel(startmonth=init_month)
        ax.plot(tmp.L - 2, tmp.corr, color="r", linewidth=2, linestyle="--", label="NMME (1982-2016)")
        ax.plot(tmp.L - 2, tmp.corr, color="r", marker="o", markersize=8, fillstyle="none", linestyle="none")
        ax.plot(tmp.L - 2, tmp.corr.where(tmp.pval < 0.1), color="r", marker="o", markersize=8, linestyle="none")
        ax2.plot(tmp.L - 2, tmp.rmse, color="r", linewidth=2, marker="o", markersize=8, linestyle="--")

        tmp = nmme_seas_skill.sel(startmonth=init_month)
        ax.fill_between(tmp.L.data - 2, tmp.corr.min("model"), tmp.corr.max("model"), fc="r", alpha=0.2)
        ax2.fill_between(tmp.L.data - 2, tmp.rmse.min("model"), tmp.rmse.max("model"), fc="r", alpha=0.2)

        xticklabs = [f"{int(leadsea[i].data)}:{SEASON_LABELS_BY_MONTH[init_month][i]}" for i in range(leadsea.sizes["L"])]
        for a, ylim, hline in [(ax, [0.1, 1.0], 0.5), (ax2, [0.2, 1.3], 1.0)]:
            a.set_xticks(leadsea)
            a.set_xticklabels(xticklabs)
            a.set_xlim([-0.5, 20])
            a.set_ylim(ylim)
            a.grid(True)
            a.axhline(y=hline, color="black")
        if j == 0:
            ax.legend(loc="lower left")

    ax = fig.add_subplot(nrow, ncol, 4 * 2 + 1)
    ax2 = fig.add_subplot(nrow, ncol, 4 * 2 + 2)
    ax.set_title(figlabs[0][4] + " " + hindcasts[4], loc="left")
    ax2.set_title(figlabs[1][4] + " " + hindcasts[4], loc="left")

    tmp = nmme_skill_mmm.mean("startmonth")
    ax.plot(tmp.L - 1, tmp.corr, color="r", linewidth=2, linestyle="--", label="NMME (1982-2016)")
    ax.plot(tmp.L - 1, tmp.corr, color="r", marker="o", markersize=8, fillstyle="none", linestyle="none")
    ax.plot(tmp.L - 1, tmp.corr.where(tmp.pval < 0.1), color="r", marker="o", markersize=8, linestyle="none")
    ax2.plot(tmp.L - 1, tmp.rmse, color="r", linewidth=2, marker="o", markersize=8, linestyle="--")

    tmp = nmme_skill.mean("startmonth")
    ax.fill_between(tmp.L.data - 1, tmp.corr.min("model", skipna=True), tmp.corr.max("model", skipna=True), fc="r", alpha=0.2)
    ax2.fill_between(tmp.L.data - 1, tmp.rmse.min("model", skipna=True), tmp.rmse.max("model", skipna=True), fc="r", alpha=0.2)

    for a, ylim, hline in [(ax, [0.1, 1.0], 0.5), (ax2, [0.2, 1.3], 1.0)]:
        a.set_xticks(np.arange(12) * 2 + 1)
        a.set_xticks(np.arange(12) * 2, minor=True)
        a.set_xlim([-0.5, 24])
        a.set_ylim(ylim)
        a.grid(True)
        a.axhline(y=hline, color="black")

    fig.tight_layout()
    figdir.mkdir(parents=True, exist_ok=True)
    figpath = figdir / "fig_nmme_nino34_f03_skill.png"
    fig.savefig(figpath, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return figpath


def plot_f04_like(
    processed: dict[str, dict[int, xr.DataArray] | xr.DataArray],
    skill: dict[str, xr.Dataset],
    obs_seas: xr.DataArray,
    clim_start: int,
    clim_end: int,
    figdir: Path,
) -> Path:
    obs_djf = obs_seas.where(obs_seas.time.dt.month == 1, drop=True)
    obs_djf = obs_djf - obs_djf.sel(time=slice(str(clim_start), str(clim_end))).mean("time")

    sm_order = [11, 8, 5, 2]
    hindcasts = {11: "NOV", 8: "AUG", 5: "MAY", 2: "FEB"}
    lead_index = {11: 0, 8: 1, 5: 2, 2: 3}
    colors = {11: "g", 8: "orange", 5: "b", 2: "r"}
    figlabs = [["a.", "c.", "e.", "g."], ["b.", "d.", "f."]]

    fig = plt.figure(figsize=(11, 10))
    plt.rcParams.update({"font.size": 10})
    for i, init_month in enumerate(sm_order):
        panels = [(0, lead_index[init_month])]
        if i < 3:
            panels.append((1, lead_index[init_month] + 4))

        for col, lindex in panels:
            ax = fig.add_subplot(4, 2, i * 2 + col + 1)
            ax.set_ylim([-3.5, 3.5])
            ax.set_yticks([-2, 0, 2])
            ax.set_yticks(np.arange(-3.5, 4, 0.5), minor=True)
            ax.set_xlim([1980, 2022])
            ax.set_xticks(np.arange(1980, 2024, 2), minor=True)
            ax.plot(obs_djf.time.dt.year, obs_djf, color="k", marker=".", markersize=6, label="HadISST2")

            if lindex >= processed["seasonal_dd"][init_month].sizes["L"]:
                ax.set_title(
                    f"{figlabs[col][i]} {hindcasts[init_month]} init: lead unavailable in 12-month NMME",
                    loc="left",
                )
                ax.grid(True)
                continue

            data = processed["seasonal_dd"][init_month].isel(L=lindex).mean("model")
            time = processed["seasonal_time"][init_month].isel(L=lindex)
            data_year = time.dt.year
            skill_row = skill["nmme_seas_skill_mmm"].sel(startmonth=init_month).isel(L=lindex)
            lead = int(data.L.values) - 2
            acc = float(skill_row.corr.values)
            nrmse = float(skill_row.rmse.values)
            figlabel = figlabs[col][i] if col == 0 else figlabs[col][i]
            title = f"{hindcasts[init_month]} init ({lead:d}-mon lead), ACC={acc:3.2f}, nRMSE={nrmse:3.2f}"
            ax.set_title(figlabel + " " + title, loc="left")

            mean = data.mean("M")
            spread = data.std("M")
            ax.plot(data_year, mean, color=colors[init_month], linewidth=2, label="NMME MMM")
            ax.fill_between(data_year, mean - spread, mean + spread, fc=colors[init_month], alpha=0.2)
            ax.grid(True)

    fig.suptitle(r"$DJF\;Ni\tilde{n}o-3.4\;Index$", fontsize=18)
    fig.tight_layout()
    figdir.mkdir(parents=True, exist_ok=True)
    figpath = figdir / "fig_nmme_nino34_f04_djf_timeseries.png"
    fig.savefig(figpath, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return figpath


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nmme-root", type=Path, default=DEFAULT_NMME_ROOT)
    parser.add_argument("--obs-file", type=Path, default=DEFAULT_OBS_FILE)
    parser.add_argument("--obs-var", default="sst")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--figdir", type=Path, default=DEFAULT_FIGDIR)
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help=(
            "Models to process. Defaults to every downloaded SST model under "
            "--nmme-root. Use --model-set yeager-f03 for the eight-model subset "
            "from Yeager f03_f04.ipynb."
        ),
    )
    parser.add_argument(
        "--model-set",
        choices=["all", "yeager-f03"],
        default="all",
        help="Named model set to use when --models is omitted.",
    )
    parser.add_argument("--clim-start", type=int, default=1982)
    parser.add_argument("--clim-end", type=int, default=2016)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    args.figdir.mkdir(parents=True, exist_ok=True)
    if args.models is None:
        if args.model_set == "yeager-f03":
            args.models = YEAGER_F03_MODELS
        else:
            args.models = discover_sst_models(args.nmme_root)

    print("[OBS] loading HadISST2 Nino3.4")
    obs_mon, obs_seas = load_obs_nino34(args.obs_file, args.obs_var)
    print(f"[NMME] processing {len(args.models)} model(s) from member-split archive")
    processed = process_nmme(
        args.nmme_root,
        args.outdir,
        args.models,
        args.clim_start,
        args.clim_end,
        force=args.force,
    )
    print("[NMME] computing skill")
    skill = compute_nmme_skill(processed, obs_mon, obs_seas, args.clim_start, args.clim_end)
    save_outputs(args.outdir, processed, skill)
    f03 = plot_f03_like(skill, args.figdir)
    f04 = plot_f04_like(processed, skill, obs_seas, args.clim_start, args.clim_end, args.figdir)
    print(f"Saved skill dataset: {args.outdir / 'NMME_Nino34_skill_1982_2016.nc'}")
    print(f"Saved figure: {f03}")
    print(f"Saved figure: {f04}")


if __name__ == "__main__":
    main()
