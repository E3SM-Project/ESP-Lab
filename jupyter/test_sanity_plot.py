import pandas as pd
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from pathlib import Path
import sys
import os

# Append project root to sys.path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))
from workflows.tc_track_density import read_stitch_nodes_tracks

TRACK_DIR = Path("/global/cfs/cdirs/e3sm/S2S2D/post_process")
test_case = "WCYCL20TR_ne30pg2_r05_IcoswISC30E3r5_JRA55_FOSIRL_1980050100"

print(f"Sanity check for case: {test_case}")

fig = plt.figure(figsize=(12, 6))
ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
ax.coastlines()
ax.set_global()

colors = {'set1': 'blue', 'set2': 'green', 'set3': 'red'}

for pset in ['set1', 'set2', 'set3']:
    t_files = sorted((TRACK_DIR / test_case).glob(f"EN*/post/atm/tc-analysis/*_{pset}_TCS_track.txt"))
    print(f"  {pset}: found {len(t_files)} track files")
    if not t_files:
        continue
    
    # Load tracks using our new function
    df = read_stitch_nodes_tracks(t_files)
    if df.empty:
        continue
        
    # Plot tracks
    for _, group in df.groupby(['member', 'storm_id']):
        ax.plot(group['lon'], group['lat'], transform=ccrs.PlateCarree(), color=colors[pset], alpha=0.5, linewidth=1)

# Create legend
from matplotlib.lines import Line2D
legend_elements = [Line2D([0], [0], color=c, lw=2, label=s) for s, c in colors.items()]
ax.legend(handles=legend_elements, loc='lower left')
ax.set_title(f"TC Tracks for {test_case} (all members)")
save_path = Path(__file__).parent / "sanity_check.png"
plt.savefig(save_path)
print("Saved sanity_check.png")
