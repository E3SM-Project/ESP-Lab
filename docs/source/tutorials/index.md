# Analysis Notebooks

The primary analysis suite for this fork lives in the `jupyter/` directory of the repository.
These notebooks cover the full E3SM S2D diagnostic workflow from data preprocessing through
skill evaluation, modes-of-variability analysis, and interactive diagnostics viewing.

## Active Notebook Suite

| Notebook | Description |
|---|---|
| `0_run_cesm_smyle_benchmark.ipynb` | Run CESM-SMYLE benchmark preprocessing |
| `1a_refactor_atm_leadtime_acc_skill_map.ipynb` | Atmospheric lead-time ACC skill maps |
| `1b_refactor_lnd_leadtime_acc_skill_map.ipynb` | Land lead-time ACC skill maps |
| `2a_refactor_leadtime_rmse_skill_map.ipynb` | Lead-time RMSE skill maps |
| `2b_refactor_leadtime_rmse_compare.ipynb` | Multi-model lead-time RMSE comparison |
| `3a_refactor_sst_skill_ts.ipynb` | SST skill time series (E3SM, CESM-SMYLE, NMME) |
| `3b_refactor_sst_telecon.ipynb` | SST teleconnection diagnostics |
| `4a_refactor_mov_analysis.ipynb` | Modes-of-variability EOF projection and analysis |
| `4b_refactor_mov_telecon.ipynb` | Modes-of-variability teleconnections |
| `5a_refactor_eli_skill_ts.ipynb` | ELI skill time series |
| `5b_refactor_eli_diagnostics.ipynb` | ELI diagnostic figures |
| `5c_refactor_eli_telecon.ipynb` | ELI teleconnection diagnostics |
| `6a_refactor_shock_ts.ipynb` | Initial shock time series |
| `6b_refactor_shock_index.ipynb` | Initial shock index diagnostics |
| `7_run_viewer_webpage.ipynb` | Generate interactive diagnostics viewer webpage |

## How to Run

1. Clone the repository: `git clone https://github.com/CESM-ESPWG/ESP-Lab.git`
2. Create and activate the conda environment (see [Installation](../how-to/install-esp-lab.md)).
3. Launch JupyterLab or JupyterHub and navigate to the `jupyter/` directory.
4. Run notebooks in order (0 → 7), configuring data paths in the first cell of each notebook.
