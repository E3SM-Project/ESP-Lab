import os
import sys
import numpy as xarray
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from pathlib import Path
import numpy as np

# Mocking constants just to verify logic doesn't crash on syntax errors
TRACK_DIR = Path("/global/cfs/cdirs/e3sm/S2S2D/post_process")
CASES = ["WCYCL20TR_ne30pg2_r05_IcoswISC30E3r5_JRA55_FOSIRL_1980050100"]

parsets_to_plot = ["set1", "set2", "set3"]
all_hist_files = {}

for pset in parsets_to_plot:
    files_for_pset = []
    for case in CASES:
        files_for_pset += sorted(
            (TRACK_DIR / case).glob(f"EN*/post/atm/tc-analysis/*_{pset}_TCS_hist.nc")
        )
    if files_for_pset:
        # only keep first 2 for quick testing
        all_hist_files[pset] = files_for_pset[:2]
        print(f"[{pset}] Histogram files found: {len(files_for_pset)} across {len(CASES)} cases")

if not all_hist_files:
    print("No histogram files found for any set — run Section 5 first.")
else:
    n_sets = len(all_hist_files)
    fig, axes = plt.subplots(
        1, n_sets, figsize=(6.5 * n_sets, 4.8),
        subplot_kw={"projection": ccrs.PlateCarree(central_longitude=180)},
        squeeze=False
    )
    axes = axes.flatten()
    
    levels = np.arange(1, 21, 1)
    cmap = plt.get_cmap("YlOrRd", len(levels) - 1).copy()
    cmap.set_bad((1, 1, 1, 0))

    for idx, (pset, hist_files) in enumerate(all_hist_files.items()):
        ax = axes[idx]
        
        ds_hist = xr.open_mfdataset(
            hist_files,
            combine="nested",
            concat_dim="hist_file",
            coords="minimal",
            compat="override",
            combine_attrs="override",
        )
        varname = "density" if "density" in ds_hist.data_vars else list(ds_hist.data_vars)[0]
        density = ds_hist[varname].sum(
            dim=[d for d in ds_hist[varname].dims if d not in ("lat", "lon")]
        ).load()
        plot_density = density.where(density > 0)
        print(
            f"[{pset}] Plotting {varname!r}: total={float(density.sum()):.0f}, "
            f"max={float(density.max()):.0f}, nonzero cells={int((density > 0).sum())}"
        )

        ax.set_extent([0, 360, -70, 70], crs=ccrs.PlateCarree())
        ax.set_title(f"E3SM - {pset}", fontsize=20, fontweight="bold", pad=14)

        xticks = np.arange(0, 361, 60)
        xtick_labels = ["0", "60°E", "120°E", "180", "120°W", "60°W", "0"]
        ax.set_xticks(xticks, crs=ccrs.PlateCarree())
        ax.set_xticklabels(xtick_labels, fontsize=11)
        ax.set_yticks([-60, -30, 0, 30, 60], crs=ccrs.PlateCarree())
        if idx == 0:
            ax.set_yticklabels(["60°S", "30°S", "0", "30°N", "60°N"], fontsize=11)
        else:
            ax.set_yticklabels([])

        ax.tick_params(axis="both", which="major", direction="out", length=7, width=1.4,
                       top=True, right=True, labeltop=False, labelright=False)
        for spine in ax.spines.values():
            spine.set_linewidth(1.4)

        im = plot_density.plot(
            ax=ax,
            transform=ccrs.PlateCarree(),
            cmap=cmap,
            levels=levels,
            extend="both",
            add_colorbar=False,
        )
        ax.coastlines(linewidth=0.8, color="black")
        
        # Adding (a), (b), (c)
        letter = chr(ord('a') + idx)
        ax.text(
            0.02, 0.86, f"({letter})", transform=ax.transAxes,
            fontsize=20, ha="left", va="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="lightgray", alpha=0.85, linewidth=0.8),
        )

    # cbar = fig.colorbar(
    #     im, ax=axes, orientation="horizontal", pad=0.15, shrink=0.5,
    #     ticks=np.arange(1, 20, 2), drawedges=True,
    # )
    # cbar.set_label("TC count", fontsize=13)
    # cbar.ax.tick_params(labelsize=13, length=0)
    
    fig.savefig("/global/homes/z/zhan391/code/ESP-Lab/jupyter/test_multi_panel.png", bbox_inches='tight')
    print("Done")
