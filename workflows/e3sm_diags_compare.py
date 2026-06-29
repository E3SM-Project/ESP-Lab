#!/usr/bin/env python3
"""
Python script to compare RMSE metrics from 4 new E3SM simulations
against CMIP6 models distribution from pre-compiled CSV files.
"""

import os
from pathlib import Path
import sys
import glob
import argparse
import numpy as np
import numpy.ma as ma
import matplotlib.cbook as cbook
import matplotlib.pyplot as plt

# --- Function to read CMIP6 model metrics ---
def read_cmip6_metrics_from_csv(path, variables, seasons):
    models = []
    if not os.path.exists(path):
        raise FileNotFoundError(f"CMIP6 CSV file not found: {path}")

    with open(path, 'r') as fin:
        lines = fin.readlines()
        # skip 3 header lines and last 2 E3SMv2 composites
        rmse_lines = lines[3:-2]
        nmodels = len(rmse_lines)
        nvariables = len(variables)
        nseasons = len(seasons)
        
        data = ma.array(np.zeros((nmodels, nvariables, nseasons)), mask=True)
        for imodel, line in enumerate(rmse_lines):
            parts = line.strip().split(',')
            if not parts or parts[0] == "":
                continue
            models.append(parts[0])
            for ivariable in range(nvariables):
                rmse_seasons = parts[1 + ivariable * 5 : 6 + ivariable * 5]
                # Pad if shorter than expected
                while len(rmse_seasons) < nseasons:
                    rmse_seasons.append("--")
                
                # Check for excluded values
                exclude_list = variables[ivariable].get('exclude', ())
                if parts[0] in exclude_list:
                    continue

                for iseason in range(nseasons):
                    val_str = rmse_seasons[iseason]
                    if val_str != "--" and val_str.upper() != "NAN" and val_str != "":
                        try:
                            data[imodel, ivariable, iseason] = float(val_str)
                        except ValueError:
                            pass

    return {
        'data': data,
        'models': models,
        'variables': variables,
        'seasons': seasons
    }

# --- Function to read E3SM Diags metrics dynamically from members ---
def read_e3sm_diags_metrics(base_path, simulations, variables, seasons):
    """
    Finds all ENxx directories for each simulation and parses their e3sm_diags CSVs.
    """
    sim_data = {}
    nvariables = len(variables)
    nseasons = len(seasons)

    for sim_name, sim_subdir in simulations.items():
        sim_dir_path = os.path.join(base_path, sim_subdir)
        if not os.path.exists(sim_dir_path):
            print(f"Warning: Directory does not exist for {sim_name}: {sim_dir_path}")
            continue

        # Find all ensemble members (EN00, EN01, etc.)
        en_dirs = sorted(glob.glob(os.path.join(sim_dir_path, "EN*")))
        if not en_dirs:
            print(f"Warning: No ENxx subdirectories found under {sim_dir_path}")
            continue

        nmembers = len(en_dirs)
        data = ma.array(np.zeros((nmembers, nvariables, nseasons)), mask=True)
        members = []

        for imember, en_dir in enumerate(en_dirs):
            member_name = os.path.basename(en_dir)
            members.append(member_name)

            # Discover table-data folder dynamically (handles grid and years pattern variations)
            pattern = os.path.join(en_dir, "e3sm_diags", "*", "*", "viewer", "table-data")
            td_dirs = glob.glob(pattern)
            if not td_dirs:
                # Try fallback without subdirectories if structured differently
                pattern_fallback = os.path.join(en_dir, "e3sm_diags", "viewer", "table-data")
                td_dirs = glob.glob(pattern_fallback)

            if not td_dirs:
                print(f"Warning: Could not find table-data directory for {sim_name} {member_name}")
                continue

            td_dir = td_dirs[0]

            for iseason, season in enumerate(seasons):
                fname = os.path.join(td_dir, f"{season}_metrics_table.csv")
                if not os.path.exists(fname):
                    fname = os.path.join(td_dir, f"{season.lower()}_metrics_table.csv")

                if not os.path.exists(fname):
                    continue

                with open(fname, 'r') as f:
                    content = f.readlines()

                for ivariable, var in enumerate(variables):
                    # Check if simulation is excluded for this variable
                    if sim_name in var.get('exclude', ()):
                        continue

                    # Search line starting with the variable id
                    lines = [l for l in content if l.startswith(var['id'])]
                    if len(lines) == 1:
                        parts = lines[0].split(',')
                        rmse_str = parts[-2].strip()  # second to last item is RMSE
                        if rmse_str.upper() != 'NAN' and rmse_str != '--' and rmse_str != '':
                            try:
                                data[imember, ivariable, iseason] = float(rmse_str)
                            except ValueError:
                                pass

        sim_data[sim_name] = {
            'members': members,
            'data': data
        }

    return sim_data

## --- Plot Comparison Implementation ---
def run_plot_comparison(cmip_path, base_dir, output_dir, simulations, variables, seasons):
    # 1. Load CMIP6 data
    try:
        cmip6 = read_cmip6_metrics_from_csv(cmip_path, variables, seasons)
    except Exception as e:
        print(f"Error loading CMIP6 metrics: {e}", file=sys.stderr)
        return

    print(f"Reading E3SM Diags metrics from base directory: {base_dir}")
    sim_data = read_e3sm_diags_metrics(base_dir, simulations, variables, seasons)

    # 3. Plotting Configuration
    fig = plt.figure(figsize=[14, 11])
    plt.rcParams.update({'font.size': 10})
    
    nsx = 3
    nsy = 3
    nseasons = len(seasons)

    # Define plotting styles dynamically based on simulations
    colors = ['#10b981', '#f59e0b', '#3b82f6', '#ef4444', '#8b5cf6', '#ec4899']
    markers = ['o', '*', 's', '^', 'D', 'v']
    
    plot_styles = {}
    x_offsets = {}
    
    nsims = len(simulations)
    if nsims > 1:
        offsets = np.linspace(-0.25, 0.25, nsims)
    else:
        offsets = [0.0]
        
    for isim, sim_name in enumerate(simulations.keys()):
        color = colors[isim % len(colors)]
        marker = markers[isim % len(markers)]
        plot_styles[sim_name] = {'color': color, 'marker': marker, 'label': f"{sim_name}"}
        x_offsets[sim_name] = offsets[isim]

    for ivariable in range(len(variables)):
        # Calculate box and whisker stats from CMIP6 data
        cmip_seasons_data = []
        labels = []
        for iseason in range(nseasons):
            # Extract valid values
            valid_cmip = cmip6['data'][:, ivariable, iseason].compressed()
            cmip_seasons_data.append(valid_cmip)
            labels.append(seasons[iseason])
            
        cmip6_stats = cbook.boxplot_stats(cmip_seasons_data, whis=[0, 100], labels=labels)

        # Plot subpanel
        ax = plt.subplot(nsy, nsx, ivariable + 1)
        ax.set_box_aspect(1)

        # Draw CMIP6 box plots
        ax.bxp(cmip6_stats, positions=np.arange(nseasons) + 1, widths=0.25)

        # Draw E3SM simulations
        for sim_name, style in plot_styles.items():
            if sim_name not in sim_data:
                continue

            sim_d = sim_data[sim_name]['data']
            nmembers = sim_d.shape[0]
            offset = x_offsets[sim_name]
            x_pos = np.arange(nseasons) + 1 + offset

            # Plot individual members as small, semi-transparent points
            if nmembers > 1:
                for imem in range(nmembers):
                    member_data = sim_d[imem, ivariable, :]
                    ax.scatter(
                        x_pos, member_data,
                        color=style['color'], marker=style['marker'],
                        s=15, alpha=0.35, edgecolors='none', label='_nolegend_'
                    )
                # Plot ensemble mean as a larger solid marker
                mean_data = np.ma.mean(sim_d[:, ivariable, :], axis=0)
                ax.scatter(
                    x_pos, mean_data,
                    color=style['color'], marker=style['marker'],
                    s=75, alpha=1.0, edgecolors='black', linewidths=1.0,
                    label=f"{style['label']} ({nmembers} mem)"
                )
            else:
                # Single member: plot directly as a larger solid marker
                member_data = sim_d[0, ivariable, :]
                ax.scatter(
                    x_pos, member_data,
                    color=style['color'], marker=style['marker'],
                    s=75, alpha=1.0, edgecolors='black', linewidths=1.0,
                    label=f"{style['label']} (1 mem)"
                )

        # Customize axes and labels
        ax.set_title('(' + chr(97 + ivariable) + ')', loc="left", fontweight='bold')
        ax.set_title(variables[ivariable]['name'] + ' (' + variables[ivariable]['units'] + ')', loc="right")
        ax.set_xlim([0.4, nseasons + 0.6])
        ax.set_xticks(np.arange(nseasons) + 1)
        ax.set_xticklabels(seasons)
        ax.grid(axis='y', linestyle='--', alpha=0.3)

    plt.tight_layout()
    fig.subplots_adjust(bottom=0.15, hspace=0.35, wspace=0.3)

    # Place unique legend entries in the bottom margin centered
    handles, labels = ax.get_legend_handles_labels()
    # Add a custom handle for CMIP6 box plots
    cmip_handle = plt.Line2D([0], [0], color='black', lw=1.5, label='CMIP6 models distribution')
    handles.insert(0, cmip_handle)
    labels.insert(0, 'CMIP6 models distribution')
    
    fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(0.5, 0.02), ncol=3, frameon=True)

    # Save outputs
    suffix = "amip" if "amip" in cmip_path.lower() else "historical"
    output_pdf = os.path.join(output_dir, f"cmip6_{suffix}_comparison.pdf")
    output_png = os.path.join(output_dir, f"cmip6_{suffix}_comparison.png")
    
    fig.savefig(output_pdf, bbox_inches='tight')
    fig.savefig(output_png, bbox_inches='tight', dpi=150)
    print(f"Success! Comparison PDF created at: {output_pdf}")
    print(f"Success! Comparison PNG created at: {output_png}")
    plt.close(fig)

# --- Main Script ---
def main():
    parser = argparse.ArgumentParser(
        description="Compare RMSE from 4 E3SM simulations with CMIP6 model distributions."
    )
    parser.add_argument(
        "--cmip-file",
        type=str,
        default="external/cmip6_amip_seasonal_rmse_202206.csv",
        help="Path to CMIP6 seasonal RMSE CSV file (relative to project root)."
    )
    parser.add_argument(
        "--base-dir",
        type=str,
        default="/global/cfs/cdirs/e3sm/www/zhan391/E3SMv3_S2D",
        help="Base directory containing the 4 simulations."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/global/cfs/cdirs/e3sm/www/zhan391/E3SMv3_S2D",
        help="Directory to save comparison plot (defaults to base-dir)."
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1] if '__file__' in globals() else Path(os.getcwd())
    cmip_path = os.path.join(project_root, args.cmip_file)
    print(f"Reading CMIP6 metrics from: {cmip_path}")

    # Standard Variables List
    variables = [
        {'name': 'Net TOA', 'units': 'W m$^{-2}$', 'id': 'RESTOM global ceres_ebaf_toa_v4.1', 'exclude': ()},
        {'name': 'SW CRE', 'units': 'W m$^{-2}$', 'id': 'SWCF global ceres_ebaf_toa_v4.1', 'exclude': ()},
        {'name': 'LW CRE', 'units': 'W m$^{-2}$', 'id': 'LWCF global ceres_ebaf_toa_v4.1', 'exclude': ()},
        {'name': 'prec', 'units': 'mm day$^{-1}$', 'id': 'PRECT global GPCP_v2.3', 'exclude': ('CIESM',)},
        {'name': 'tas land', 'units': 'K', 'id': 'TREFHT land ERA5', 'exclude': ()},
        {'name': 'SLP', 'units': 'hPa', 'id': 'PSL global ERA5', 'exclude': ()},
        {'name': 'u-200', 'units': 'm s$^{-1}$', 'id': 'U-200mb global ERA5', 'exclude': ()},
        {'name': 'u-850', 'units': 'm s$^{-1}$', 'id': 'U-850mb global ERA5', 'exclude': ()},
        {'name': 'Zg-500', 'units': 'hm', 'id': 'Z3-500mb global ERA5', 'exclude': ('KIOST-ESM',)},
    ]

    seasons = ['ANN', 'DJF', 'MAM', 'JJA', 'SON']

    simulations = {
        '4DEnVar_branch': 'test_WCYCL20TR_ne30pg2_r05_IcoswISC30E3r5_4DEnVar_branch',
        '4DEnVar_hybrid': 'test_WCYCL20TR_ne30pg2_r05_IcoswISC30E3r5_4DEnVar_hybrid',
        'BruteForce': 'WCYCL20TR_ne30pg2_r05_IcoswISC30E3r5_BruteForce_1980050100',
        'JRA55_FOSIRL': 'WCYCL20TR_ne30pg2_r05_IcoswISC30E3r5_JRA55_FOSIRL_1980050100'
    }

    run_plot_comparison(cmip_path, args.base_dir, args.output_dir, simulations, variables, seasons)

if __name__ == '__main__':
    main()
