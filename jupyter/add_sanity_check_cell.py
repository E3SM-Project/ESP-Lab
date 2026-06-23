import json
import os

notebook_path = "/global/homes/z/zhan391/code/ESP-Lab/jupyter/7_refactor_tc_analysis.ipynb"

with open(notebook_path, "r") as f:
    nb = json.load(f)

# Find the index of Cell 12 (or after the 'Discover Track Files' block)
# Actually we can just append it right after the Configuration and Validation cells.
# Or just put it at the very end of the notebook. Let's put it after the track file listing cell (which is around cell 12).
# Let's find the cell with "print(f\"Track files found: {len(track_files)}  across {len(CASES)} cases\")"

insert_idx = len(nb['cells'])
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        if "Track files found:" in source:
            insert_idx = i + 2 # After the file inspection cell
            break

new_cell = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# Sanity check: Discover and plot available tracks for set1, set2, and set3 for the first case\n",
        "import pandas as pd\n",
        "import cartopy.crs as ccrs\n",
        "import matplotlib.pyplot as plt\n",
        "from workflows.tc_track_density import read_stitch_nodes_tracks\n",
        "\n",
        "test_case = CASES[0]\n",
        "print(f\"Sanity check for case: {test_case}\")\n",
        "\n",
        "fig = plt.figure(figsize=(12, 6))\n",
        "ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())\n",
        "ax.coastlines()\n",
        "ax.set_global()\n",
        "\n",
        "colors = {'set1': 'blue', 'set2': 'green', 'set3': 'red'}\n",
        "\n",
        "for pset in ['set1', 'set2', 'set3']:\n",
        "    t_files = sorted((TRACK_DIR / test_case).glob(f\"EN*/post/atm/tc-analysis/*_{pset}_TCS_track.txt\"))\n",
        "    print(f\"  {pset}: found {len(t_files)} track files\")\n",
        "    if not t_files:\n",
        "        continue\n",
        "    \n",
        "    # Load tracks using our new function\n",
        "    df = read_stitch_nodes_tracks(t_files)\n",
        "    if df.empty:\n",
        "        continue\n",
        "        \n",
        "    # Plot tracks\n",
        "    for _, group in df.groupby(['member', 'storm_id']):\n",
        "        ax.plot(group['lon'], group['lat'], transform=ccrs.PlateCarree(), color=colors[pset], alpha=0.5, linewidth=1)\n",
        "\n",
        "# Create legend\n",
        "from matplotlib.lines import Line2D\n",
        "legend_elements = [Line2D([0], [0], color=c, lw=2, label=s) for s, c in colors.items()]\n",
        "ax.legend(handles=legend_elements, loc='lower left')\n",
        "ax.set_title(f\"TC Tracks for {test_case} (all members)\")\n",
        "plt.show()\n"
    ]
}

nb['cells'].insert(insert_idx, new_cell)

with open(notebook_path, "w") as f:
    json.dump(nb, f, indent=1)
    f.write("\n")

print("Added cell to notebook.")
