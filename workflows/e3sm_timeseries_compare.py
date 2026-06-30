import os
import glob
import argparse
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
from pathlib import Path

# Variables configuration and conversions
VARIABLES_INFO = {
    'TREFHT': {
        'file_var': 'TREFHT',
        'units': '°C',
        'title': 'Reference Height Temperature (2m)',
        'conversion': lambda x: x - 273.15,
        'use_land_mask': True
    },
    'PRECT': {
        'file_var': 'PRECT',
        'units': 'mm/day',
        'title': 'Total Precipitation Rate',
        'conversion': lambda x: x * 8.64e7,
        'use_land_mask': False
    },
    'PSL': {
        'file_var': 'PSL',
        'units': 'hPa',
        'title': 'Sea Level Pressure',
        'conversion': lambda x: x / 100.0,
        'use_land_mask': False
    },
    'SWCF': {
        'file_var': 'SWCF',
        'units': 'W/m²',
        'title': 'Shortwave Cloud Forcing',
        'conversion': lambda x: x,
        'use_land_mask': False
    },
    'LWCF': {
        'file_var': 'LWCF',
        'units': 'W/m²',
        'title': 'Longwave Cloud Forcing',
        'conversion': lambda x: x,
        'use_land_mask': False
    }
}

def load_simulation_timeseries(base_dir, simulations, variable, init_tag="1980050100", nlead=24):
    """
    Loads netcdf timeseries files for the selected variable and calculates spatial means.
    """
    if variable not in VARIABLES_INFO:
        raise ValueError(f"Variable {variable} not configured in VARIABLES_INFO")
    
    var_cfg = VARIABLES_INFO[variable]
    file_var = var_cfg['file_var']
    
    sim_data = {}
    
    for sim_name, sim_val in simulations.items():
        if isinstance(sim_val, dict):
            sim_subdir = sim_val.get('run_name')
            ens_filter = sim_val.get('ens')
        else:
            sim_subdir = sim_val
            ens_filter = None
            
        # Robustly locate simulation directory by checking base_dir, CFS, and scratch,
        # ensuring either the 180x360_aave/ts/monthly/2yr or glb/ts/monthly/2yr directory exists.
        sim_dir_path = None
        for b_dir in [base_dir, "/global/cfs/cdirs/e3sm/S2S2D/post_process", "/pscratch/sd/z/zhan391/e3sm_project/E3SMv3_S2D"]:
            test_path = os.path.join(b_dir, sim_subdir)
            if os.path.exists(test_path):
                # Verify that the ts directory exists for at least one candidate member
                all_en = sorted(glob.glob(os.path.join(test_path, "EN*")))
                if all_en:
                    ts_check_aave = os.path.join(all_en[0], "post/atm/180x360_aave/ts/monthly/2yr")
                    ts_check_glb = os.path.join(all_en[0], "post/atm/glb/ts/monthly/2yr")
                else:
                    ts_check_aave = os.path.join(test_path, "post/atm/180x360_aave/ts/monthly/2yr")
                    ts_check_glb = os.path.join(test_path, "post/atm/glb/ts/monthly/2yr")
                if os.path.exists(ts_check_aave) or os.path.exists(ts_check_glb):
                    sim_dir_path = test_path
                    break
                
        if sim_dir_path is None:
            print(f"Warning: Directory containing ts data does not exist for {sim_name}: {sim_subdir}")
            continue
            
        # Check if there are ENxx subdirectories
        all_en_dirs = sorted(glob.glob(os.path.join(sim_dir_path, "EN*")))
        
        # Decide if this is a single-member direct case or a multi-member case
        if all_en_dirs:
            # Filter ensemble members
            en_dirs = []
            if ens_filter is not None:
                if isinstance(ens_filter, int):
                    en_dirs = all_en_dirs[:ens_filter]
                elif isinstance(ens_filter, (list, tuple)):
                    for item in ens_filter:
                        if isinstance(item, int):
                            if 0 <= item < len(all_en_dirs):
                                en_dirs.append(all_en_dirs[item])
                        elif isinstance(item, str):
                            matching = [d for d in all_en_dirs if os.path.basename(d) == item]
                            if matching:
                                en_dirs.extend(matching)
                else:
                    en_dirs = all_en_dirs
            else:
                en_dirs = all_en_dirs
        else:
            # No ENxx subdirectories; treat the simulation directory itself as a single member
            en_dirs = [sim_dir_path]
            
        nmembers = len(en_dirs)
        if nmembers == 0:
            print(f"Warning: No matching ensemble members found for {sim_name}")
            continue
            
        member_timeseries = []
        time_values = None
        
        for en_dir in en_dirs:
            # Check 180x360_aave grid first, fallback to glb
            ts_dir = os.path.join(en_dir, "post/atm/180x360_aave/ts/monthly/2yr")
            is_glb = False
            
            if not os.path.exists(ts_dir):
                ts_dir = os.path.join(en_dir, "post/atm/glb/ts/monthly/2yr")
                is_glb = True
                
            if not os.path.exists(ts_dir):
                print(f"Warning: ts directory does not exist: {ts_dir}")
                continue
                
            # Locate file matching the variable
            pattern = os.path.join(ts_dir, f"{file_var}_*.nc")
            matching_files = glob.glob(pattern)
            if not matching_files:
                print(f"Warning: No files found matching pattern: {pattern}")
                continue
                
            file_path = sorted(matching_files)[0]
            
            try:
                with xr.open_dataset(file_path) as ds:
                    da = ds[file_var]
                    # Subset to nlead
                    if da.sizes.get('time', 0) > nlead:
                        da = da.isel(time=slice(0, nlead))
                    
                    # Capture time values from first valid file
                    if time_values is None:
                        time_values = ds['time'].values[:nlead]
                        
                    # Calculate spatial mean or use pre-computed global mean
                    if is_glb:
                        # glb files are already global means, index 0 of rgn dimension
                        # is the 'Global' region
                        if 'rgn' in da.dims:
                            spatial_mean = da.isel(rgn=0)
                        else:
                            spatial_mean = da
                    else:
                        # Compute area-weighted mean over the grid
                        lat = da['lat']
                        weights = np.cos(np.deg2rad(lat))
                        
                        if var_cfg['use_land_mask']:
                            landfrac_pattern = os.path.join(ts_dir, "LANDFRAC_*.nc")
                            lf_files = glob.glob(landfrac_pattern)
                            if lf_files:
                                lf_path = sorted(lf_files)[0]
                                with xr.open_dataset(lf_path) as ds_lf:
                                    lf = ds_lf['LANDFRAC']
                                    if lf.sizes.get('time', 0) > nlead:
                                        lf = lf.isel(time=slice(0, nlead))
                                    # Weight by both latitude cosine and land fraction
                                    weights = weights * lf
                                    
                        weighted_da = da.weighted(weights)
                        spatial_dims = [dim for dim in ['lat', 'lon'] if dim in da.dims]
                        spatial_mean = weighted_da.mean(dim=spatial_dims, skipna=True)
                    
                    # Apply variable-specific conversion/scaling
                    spatial_mean = var_cfg['conversion'](spatial_mean)
                    member_timeseries.append(spatial_mean.values)
                    
            except Exception as e:
                print(f"Error reading/processing file {file_path}: {e}")
                continue
                
        if not member_timeseries:
            continue
            
        # Convert to numpy array of shape (nmembers, nlead)
        member_timeseries = np.array(member_timeseries)
        
        # Calculate ensemble stats
        ens_mean = np.nanmean(member_timeseries, axis=0)
        ens_std = np.nanstd(member_timeseries, axis=0)
        
        sim_data[sim_name] = {
            'members': member_timeseries,
            'mean': ens_mean,
            'std': ens_std,
            'time': time_values
        }
        
    return sim_data

def plot_timeseries_comparison(sim_data, variable, output_dir, figsize=[10, 6], colors=None, fontz=14):
    """
    Plots time series comparison across the simulations.
    """
    if not sim_data:
        print("No simulation data loaded to plot.")
        return
        
    var_cfg = VARIABLES_INFO[variable]
    
    if colors is None:
        colors = {
            'BruteForce': '#10b981',       # Vibrant Emerald Green
            'JRA55_FOSIRL': '#f59e0b',     # Amber Yellow
            '4DEnVar_branch': '#3b82f6',   # Bright Blue
            '4DEnVar_hybrid': '#ef4444'    # Bright Red
        }
        
    plt.figure(figsize=figsize)
    plt.rc('font', size=fontz)
    plt.rc('axes', labelsize=fontz)
    plt.rc('xtick', labelsize=fontz - 2)
    plt.rc('ytick', labelsize=fontz - 2)
    plt.rc('legend', fontsize=fontz - 2)
    
    time_labels = None
    
    for sim_name, data in sim_data.items():
        color = colors.get(sim_name, '#6b7280')
        nlead = len(data['mean'])
        x = np.arange(1, nlead + 1)
        
        if time_labels is None and data['time'] is not None:
            time_labels = [f"{t.year:04d}-{t.month:02d}" for t in data['time']]
            
        nmembers = data['members'].shape[0]
        
        # Plot individual members for ensemble runs
        if nmembers > 1:
            for i in range(nmembers):
                plt.plot(x, data['members'][i], color=color, alpha=0.25, linewidth=1.0)
            label = f"{sim_name} Mean ({nmembers} mem)"
        else:
            label = f"{sim_name} (1 mem)"
            
        # Plot ensemble mean
        plt.plot(x, data['mean'], color=color, linewidth=2.5, label=label)
        
        # Plot ensemble spread (mean +/- 1 std) for ensemble runs
        if nmembers > 1:
            plt.fill_between(x, data['mean'] - data['std'], data['mean'] + data['std'], 
                             color=color, alpha=0.1)
            
    plt.title(f"{var_cfg['title']} ({variable})", fontsize=fontz + 2, fontweight='bold', pad=15)
    plt.xlabel("Lead Month (date)", fontsize=fontz, labelpad=10)
    plt.ylabel(f"Global Mean ({var_cfg['units']})", fontsize=fontz, labelpad=10)
    plt.grid(True, linestyle='--', alpha=0.5)
    
    if time_labels is not None:
        # Show ticks every 2 months
        tick_indices = np.arange(0, len(time_labels), 2)
        plt.xticks(tick_indices + 1, [time_labels[i] for i in tick_indices], rotation=45)
    else:
        plt.xticks(np.arange(1, nlead + 1, 2))
        
    plt.xlim(1, nlead)
    plt.legend(loc='best', frameon=True, facecolor='white', edgecolor='lightgray')
    plt.tight_layout()
    
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"e3sm_timeseries_{variable}.png")
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Success! Saved time series comparison to: {out_path}")

def main():
    parser = argparse.ArgumentParser(description="Plot area-weighted monthly time series comparisons across E3SM simulations.")
    parser.add_argument("--base-dir", type=str, default="/pscratch/sd/z/zhan391/e3sm_project/E3SMv3_S2D", help="Base directory of E3SM S2D runs")
    parser.add_argument("--output-dir", type=str, default="/global/cfs/cdirs/e3sm/www/zhan391/E3SMv3_S2D", help="Output directory for comparison plots")
    parser.add_argument("--variable", type=str, required=True, choices=list(VARIABLES_INFO.keys()), help="Variable to process and plot")
    parser.add_argument("--nlead", type=int, default=24, help="Number of lead months")
    parser.add_argument("--fontz", type=int, default=14, help="Font size scaling")
    
    args = parser.parse_args()
    
    simulations = {
        'BruteForce': {'run_name': 'WCYCL20TR_ne30pg2_r05_IcoswISC30E3r5_BruteForce_1980050100', 'ens': 10},
        'JRA55_FOSIRL': {'run_name': 'WCYCL20TR_ne30pg2_r05_IcoswISC30E3r5_JRA55_FOSIRL_1980050100', 'ens': 10},
        '4DEnVar_branch': {'run_name': 'test_WCYCL20TR_ne30pg2_r05_IcoswISC30E3r5_4DEnVar_branch', 'ens': 1},
        '4DEnVar_hybrid': {'run_name': 'test_WCYCL20TR_ne30pg2_r05_IcoswISC30E3r5_4DEnVar_hybrid', 'ens': 1},
    }
    
    print(f"--- Processing variable: {args.variable} ---")
    data = load_simulation_timeseries(args.base_dir, simulations, args.variable, nlead=args.nlead)
    plot_timeseries_comparison(data, args.variable, args.output_dir, fontz=args.fontz)

if __name__ == '__main__':
    main()
