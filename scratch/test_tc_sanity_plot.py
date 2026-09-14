import sys
from pathlib import Path
repo_root = Path.cwd()
sys.path.insert(0, str(repo_root))

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.util import add_cyclic_point
from global_land_mask import globe

from workflows.tropical_cyclones.track_density import read_stitch_nodes_tracks

QUICK_SANITY_PARSETS = ['set1', 'set2', 'set3', 'set4', 'set5']
PSET_DISPLAY_NAMES = {
    'set1': 'Z200-Z500 (Height Anomaly)',
    'set2': 'T200-T500 (Temp Anomaly)',
    'set3': 'Z300-Z500 (Height Anomaly)',
    'set4': 'T300-T500 (Temp Anomaly)',
    'set5': 'T400 (Upper-level Temp)',
}
TRACK_DIR = Path('/global/cfs/cdirs/e3sm/S2S2D/post_process')
case = 'WCYCL20TR_ne30pg2_r05_IcoswISC30E3r5_JRA55_FOSIRL_1980050100'
member = 'EN00'

quick_panels = []
for pset in QUICK_SANITY_PARSETS:
    analysis_dir = TRACK_DIR / case / member / 'post' / 'atm' / 'tc-analysis'
    hist_file = analysis_dir / f'{case}_{member}_{pset}_TCS_hist.nc'
    track_file = analysis_dir / f'{case}_{member}_{pset}_TCS_track.txt'
    
    with xr.open_dataset(hist_file) as ds_hist:
        density = ds_hist['density'].sum(
            dim=[d for d in ds_hist['density'].dims if d not in ('lat', 'lon')]
        ).load()
    
    lon2d, lat2d = np.meshgrid(density['lon'].values, density['lat'].values)
    land_mask = xr.DataArray(
        globe.is_land(lat2d, ((lon2d + 180.0) % 360.0) - 180.0),
        coords=density.coords,
        dims=density.dims,
    )
    plot_density = density.where((density > 0) & (~land_mask))
    max_density = float(plot_density.max(skipna=True))
    norm_density = plot_density / max_density if (np.isfinite(max_density) and max_density > 0) else plot_density
    tracks = read_stitch_nodes_tracks([track_file]) if track_file.is_file() else pd.DataFrame()
    
    quick_panels.append({
        'pset': pset,
        'case': case,
        'member': member,
        'plot_density': norm_density,
        'max_density': max_density,
        'tracks': tracks,
    })

# Refined styling constants
QUICK_SANITY_EXTENT = [0, 360, -70, 70]
QUICK_SANITY_CENTRAL_LONGITUDE = 180
QUICK_SANITY_FIG_TITLE = "Tropical Cyclone Tracks and Genesis Density across Tracking Parameter Sets"

QUICK_SANITY_FIG_WIDTH = 13.5
QUICK_SANITY_ROW_HEIGHT = 2.45
QUICK_SANITY_EXTRA_HEIGHT = 1.1

QUICK_SANITY_CMAP_NAME = "YlOrRd"
QUICK_SANITY_CMAP_START = 0.20
QUICK_SANITY_COLOR_LEVELS = np.arange(0, 1.01, 0.2)
QUICK_SANITY_COLORBAR_TICKS = np.arange(0, 1.01, 0.2)
QUICK_SANITY_COLORBAR_LABEL = "Normalized TC genesis density"

QUICK_SANITY_COASTLINE_KW = dict(linewidth=0.6, color="0.25", zorder=3)
QUICK_SANITY_BORDER_KW = dict(linewidth=0.3, edgecolor="0.5", alpha=0.5, zorder=3)
QUICK_SANITY_GRIDLINE_KW = dict(linewidth=0.3, color="0.75", alpha=0.5, linestyle="--", zorder=3)
QUICK_SANITY_TRACK_KW = dict(colors="#0f172a", linewidths=0.65, alpha=0.65)
QUICK_SANITY_GENESIS_KW = dict(
    s=13, marker="o", color="#2563eb", edgecolor="white", linewidth=0.4, alpha=0.9
)

levels = np.asarray(QUICK_SANITY_COLOR_LEVELS)
base_cmap = plt.get_cmap(QUICK_SANITY_CMAP_NAME)
cmap = ListedColormap(base_cmap(np.linspace(QUICK_SANITY_CMAP_START, 1.0, len(levels) - 1)))
cmap.set_bad((1, 1, 1, 0))
cmap.set_over(base_cmap(1.0))
norm = BoundaryNorm(levels, cmap.N)

def _setup_map_axis(ax, title, show_bottom_labels=False, show_left_labels=True):
    ax.set_extent(QUICK_SANITY_EXTENT, crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.OCEAN, facecolor="#f8fafc", zorder=0)
    ax.add_feature(cfeature.LAND, facecolor="#e2e8f0", zorder=0)
    ax.coastlines(**QUICK_SANITY_COASTLINE_KW)
    ax.add_feature(cfeature.BORDERS, **QUICK_SANITY_BORDER_KW)
    ax.set_title(title, fontsize=10.5, fontweight="bold", pad=6, loc="left")
    
    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, **QUICK_SANITY_GRIDLINE_KW)
    gl.top_labels = False
    gl.right_labels = False
    gl.bottom_labels = show_bottom_labels
    gl.left_labels = show_left_labels
    gl.xlabel_style = {"size": 8.5, "color": ".3"}
    gl.ylabel_style = {"size": 8.5, "color": ".3"}
    return gl

def _plot_tracks(ax, tracks, track_kw=QUICK_SANITY_TRACK_KW, genesis_kw=QUICK_SANITY_GENESIS_KW):
    if tracks.empty:
        ax.text(0.5, 0.5, "no tracks", transform=ax.transAxes, ha="center", va="center", fontsize=11, color="0.4")
        return 0, 0

    segments = []
    starts = []
    group_cols = [c for c in ["case", "member", "storm_id"] if c in tracks.columns]
    for _, storm in tracks.sort_values("time").groupby(group_cols):
        points = storm[["lon", "lat"]].to_numpy()
        if len(points) < 2:
            continue
        starts.append(points[0])
        split_at = np.where(np.abs(np.diff(points[:, 0])) > 180.0)[0] + 1
        for segment in np.split(points, split_at):
            if len(segment) >= 2:
                segments.append(segment)

    if segments:
        track_lines = LineCollection(segments, transform=ccrs.PlateCarree(), zorder=4, **track_kw)
        ax.add_collection(track_lines)

    if starts:
        starts = np.asarray(starts)
        ax.scatter(starts[:, 0], starts[:, 1], transform=ccrs.PlateCarree(), zorder=5, **genesis_kw)

    n_storms = len(starts)
    n_points = len(tracks)
    return n_storms, n_points

nrows = len(quick_panels)
fig, axes = plt.subplots(
    nrows, 2,
    figsize=(QUICK_SANITY_FIG_WIDTH, QUICK_SANITY_ROW_HEIGHT * nrows + QUICK_SANITY_EXTRA_HEIGHT),
    subplot_kw={"projection": ccrs.PlateCarree(central_longitude=QUICK_SANITY_CENTRAL_LONGITUDE)},
    squeeze=False,
)

im = None
for row, panel in enumerate(quick_panels):
    pset = panel["pset"]
    pset_display = PSET_DISPLAY_NAMES.get(pset, pset)
    label = f"{pset_display} | {panel['member']}"
    is_last_row = (row == nrows - 1)

    track_ax = axes[row, 0]
    density_ax = axes[row, 1]

    # Tracks
    n_storms, n_points = _plot_tracks(track_ax, panel["tracks"])
    track_title = f"{label} - tracks ({n_storms} storms)"
    _setup_map_axis(track_ax, track_title, show_bottom_labels=is_last_row, show_left_labels=True)

    # Density
    density_da = panel["plot_density"]
    max_d = panel["max_density"]
    has_density = np.isfinite(max_d) and max_d > 0 and np.isfinite(density_da.values).any()
    density_title = f"{label} - genesis density (peak={int(max_d)})"
    _setup_map_axis(density_ax, density_title, show_bottom_labels=is_last_row, show_left_labels=False)

    if has_density:
        density_values, density_lon = add_cyclic_point(density_da.values, coord=density_da["lon"].values, axis=1)
        lon2d, lat2d = np.meshgrid(density_lon, density_da["lat"].values)
        im = density_ax.pcolormesh(
            lon2d, lat2d, density_values,
            transform=ccrs.PlateCarree(), cmap=cmap, norm=norm,
            shading="auto", alpha=1.0, zorder=1, rasterized=True,
        )
        lon_vals = density_da["lon"].values
        lat_vals = density_da["lat"].values
        lon_grid, lat_grid = np.meshgrid(lon_vals, lat_vals)
        vals = density_da.values
        finite_mask = np.isfinite(vals)
        if finite_mask.any():
            density_ax.scatter(
                lon_grid[finite_mask], lat_grid[finite_mask],
                c=vals[finite_mask], cmap=cmap, norm=norm,
                transform=ccrs.PlateCarree(), s=18, marker="s", linewidths=0, zorder=2,
            )
    else:
        density_ax.text(0.5, 0.5, "no density data", transform=density_ax.transAxes,
                        ha="center", va="center", fontsize=10, color="0.4")

fig.subplots_adjust(left=0.05, right=0.98, top=0.93, bottom=0.09, wspace=0.06, hspace=0.22)

# Add track legend under tracks column (left bottom)
legend_elements = [
    Line2D([0], [0], color=QUICK_SANITY_TRACK_KW["colors"], lw=1.2, label="TC Track"),
    Line2D([0], [0], marker=QUICK_SANITY_GENESIS_KW["marker"], color="none",
           markerfacecolor=QUICK_SANITY_GENESIS_KW["color"], markeredgecolor="white",
           markeredgewidth=0.5, markersize=7, label="Genesis Point"),
]
fig.legend(
    handles=legend_elements,
    loc="lower left",
    bbox_to_anchor=(0.08, 0.035),
    ncol=2,
    frameon=True,
    framealpha=0.9,
    edgecolor="0.7",
    fontsize=9.5,
)

# Add colorbar under density column (right bottom)
if im is not None:
    cbar_ax = fig.add_axes([0.56, 0.042, 0.38, 0.015])
    cbar = fig.colorbar(im, cax=cbar_ax, orientation="horizontal", ticks=QUICK_SANITY_COLORBAR_TICKS,
                        boundaries=levels, extend="max")
    cbar.set_label(QUICK_SANITY_COLORBAR_LABEL, fontsize=9.5)
    cbar.ax.tick_params(labelsize=8.5)

fig.suptitle(QUICK_SANITY_FIG_TITLE, fontsize=13.5, fontweight="bold", y=0.975)

out_fig = Path("/global/homes/z/zhan391/.gemini/antigravity/brain/936fdfa1-1229-4e83-af37-29f772d5986a/test_refined_tc_tracks_density.png")
fig.savefig(out_fig, dpi=180, bbox_inches="tight")
print("Saved refined figure:", out_fig)

