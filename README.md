# ESP-Lab

- [ESP-Lab](#esp-lab)
  - [Badges](#badges)
  - [Overview](#overview)
  - [E3SM S2D Extensions](#e3sm-s2d-extensions)
  - [Analysis & Diagnostic Suite (`jupyter/`)](#analysis--diagnostic-suite-jupyter)
  - [Interactive Web Viewer](#interactive-web-viewer)
  - [Data Organization & Output Conventions](#data-organization--output-conventions)
    - [Diagnostic Data Layout (`S2D_DIAG_ROOT`)](#diagnostic-data-layout-s2d_diag_root)
    - [NetCDF File Naming Conventions](#netcdf-file-naming-conventions)
    - [Figure Naming Conventions (`FIGURE_OUTDIR`)](#figure-naming-conventions-figure_outdir)
  - [Installation](#installation)
    - [Developer Installation (Conda Environment)](#developer-installation-conda-environment)
    - [Installation into Existing Conda Environment](#installation-into-existing-conda-environment)
    - [Pip Installation](#pip-installation)
  - [Documentation & Links](#documentation--links)

## Badges
| CI          |                                                               [![Code Coverage Status][codecov-badge]][codecov-link] |
| :---------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: |
| **Docs**    |                                                                     [![Documentation Status][rtd-badge]][rtd-link]                                                                     |
| **Package** |                                                                             [![PyPI][pypi-badge]][pypi-link]                                                                           |
| **License** |                                                                         [![License][license-badge]][repo-link]                                                                         |

## Overview
ESP-Lab is an Earth System Predictions Python package originally designed to enable users to effectively perform I/O operations and statistics on [SMYLE (The Seasonal-to-Multiyear Large Ensemble)](https://doi.org/10.5194/gmd-2022-60) data. It provides a foundational toolkit for analyzing subseasonal-to-multiyear predictions of climate variability and environmental change.

Key capabilities include:
- Efficient lead-time slicing and indexing across hindcast ensembles spanning 1 month to multiple years.
- Dask-distributed data processing and memory-optimized preprocessors.
- Statistical verification metrics (deterministic skill, ACC, RMSE, ensemble distributions, and detrending).

## E3SM S2D Extensions
This fork extends ESP-Lab to fully support analysis and verification of **E3SM (Energy Exascale Earth System Model)** subseasonal-to-decadal (S2D) hindcasts alongside CESM-SMYLE, NMME, and observational reference benchmarks:

- **E3SM Hindcast Workflows**: Native support for E3SM file naming, spatial grids, variable structures, and multi-start initialization cycles (e.g., February, May, August, November).
- **Multi-Model Intercomparisons**: Standardized diagnostic pipelines evaluating E3SM against CESM-SMYLE, NMME models, and observational datasets (e.g., ERA5, GPCP, HadISST).
- **Streamlined Diagnostics Package**: Modular diagnostic workflows under `esp_lab.diagnostics` covering SST indices, ENSO teleconnections, modes of variability (PDO, AMO, NAO), native equatorial Pacific longitudinal index (ELI), and initialization shock.
- **Robust Dask Automation**: Resilient Dask distributed cluster lifecycle, file locking safeguards on network filesystems (GPFS/CFS), and worker memory management.

## Analysis & Diagnostic Suite (`jupyter/`)
The primary evaluation workflows are organized sequentially under the [`jupyter/`](jupyter/) directory:

The refactored `1a_*`, `1b_*`, and `1c_*` families separate ACC, anomaly-based RMSE maps, and direct raw-value RMSE comparisons, respectively, with `atm`, `lnd`, and `ocn` variants. Atmosphere and ocean workflows can compare against CESM-SMYLE; land workflows compare E3SM cases against a configured land reference. Land `1b` reuses or computes the same normalized-RMSE skill caches as land `1a`. Land `1c` requires an absolute-value reference: the default C3S TWSA anomaly product is suitable for `1a`/`1b`, but cannot be compared directly with raw model storage.

| Notebook | Focus Area | Description |
|---|---|---|
| [`0_run_cesm_smyle_benchmark.ipynb`](jupyter/0_run_cesm_smyle_benchmark.ipynb) | Benchmark Data | Dask-distributed preprocessing of CESM-SMYLE hindcasts |
| [`1a_atm_leadtime_acc_skill_map.ipynb`](jupyter/1a_atm_leadtime_acc_skill_map.ipynb) | Atmospheric Skill | Lead-time anomaly correlation coefficient (ACC) maps |
| [`1a_lnd_leadtime_acc_skill_map.ipynb`](jupyter/1a_lnd_leadtime_acc_skill_map.ipynb) | Land Skill | Land surface lead-time ACC maps (soil moisture, runoff, etc.) |
| [`1a_ocn_leadtime_acc_skill_map.ipynb`](jupyter/1a_ocn_leadtime_acc_skill_map.ipynb) | Ocean Skill | Ocean-realm lead-time ACC maps (starting with SST) |
| [`1b_atm_leadtime_rmse_skill_map.ipynb`](jupyter/1b_atm_leadtime_rmse_skill_map.ipynb) | Error Maps | Spatial root mean square error (RMSE) skill maps (atmosphere) |
| [`1b_ocn_leadtime_rmse_skill_map.ipynb`](jupyter/1b_ocn_leadtime_rmse_skill_map.ipynb) | Error Maps | Spatial RMSE skill maps (ocean, starting with SST) |
| [`1b_lnd_leadtime_rmse_skill_map.ipynb`](jupyter/1b_lnd_leadtime_rmse_skill_map.ipynb) | Error Maps | Spatial RMSE skill maps (land: H2OSNO, H2OSOI, TWS) |
| [`1c_atm_leadtime_rmse_compare.ipynb`](jupyter/1c_atm_leadtime_rmse_compare.ipynb) | Model Comparison | Multi-model RMSE comparison and model difference metrics (atmosphere) |
| [`1c_ocn_leadtime_rmse_compare.ipynb`](jupyter/1c_ocn_leadtime_rmse_compare.ipynb) | Model Comparison | Multi-model RMSE comparison and model difference metrics (ocean, starting with SST) |
| [`1c_lnd_leadtime_rmse_compare.ipynb`](jupyter/1c_lnd_leadtime_rmse_compare.ipynb) | Model Comparison | Direct-RMSE comparison between E3SM land cases (absolute-value reference required; no CESM-SMYLE land benchmark) |
| [`2a_regional_acc_skill_ts.ipynb`](jupyter/2a_regional_acc_skill_ts.ipynb) | Regional Skill | Cache-first global and regional ACC-versus-lead summaries from 1a ACC products |
| [`3a_sst_skill_ts.ipynb`](jupyter/3a_sst_skill_ts.ipynb) | Ocean Skill | SST index skill time series (E3SM, CESM-SMYLE, NMME) |
| [`3b_sst_telecon.ipynb`](jupyter/3b_sst_telecon.ipynb) | Teleconnections | Sea surface temperature teleconnection diagnostics |
| [`4a_mov_analysis.ipynb`](jupyter/4a_mov_analysis.ipynb) | Modes of Variability | EOF projection and index calculation (PDO, AMO, NAO) |
| [`4b_mov_telecon.ipynb`](jupyter/4b_mov_telecon.ipynb) | Teleconnections | Modes of variability climate teleconnection patterns |
| [`5a_eli_skill_ts.ipynb`](jupyter/5a_eli_skill_ts.ipynb) | Tropical Pacific | Equatorial Longitude Index (ELI) skill time series |
| [`5b_eli_diagnostics.ipynb`](jupyter/5b_eli_diagnostics.ipynb) | ELI Diagnostics | Native & regridded ELI diagnostics across starts |
| [`5c_eli_telecon.ipynb`](jupyter/5c_eli_telecon.ipynb) | Teleconnections | ELI precipitation and temperature teleconnections |
| [`6a_shock_ts.ipynb`](jupyter/6a_shock_ts.ipynb) | Initialization Shock | Lead-dependent drift and initialization shock time series |
| [`6b_shock_index.ipynb`](jupyter/6b_shock_index.ipynb) | Shock Indices | Initialization shock metrics and multi-model indices |
| [`7a_tc_method_analysis.ipynb`](jupyter/7a_tc_method_analysis.ipynb) | Tropical Cyclones | TempestExtremes tracking method and parameter comparison |
| [`7b_tc_leadtime_analysis.ipynb`](jupyter/7b_tc_leadtime_analysis.ipynb) | Tropical Cyclones | TC lead-time density, IBTrACS comparison, and ENSO regression |
| [`8_run_viewer_webpage.ipynb`](jupyter/8_run_viewer_webpage.ipynb) | Gallery Webpage | Interactive HTML diagnostics viewer generator |

## Interactive Web Viewer
ESP-Lab includes a responsive HTML web generator (`esp_lab.diagnostics.web`) that compiles all evaluation figures into a standalone, browsable diagnostics gallery.

- **Live Web Gallery**: [NERSC CFS ESP-Lab Diagnostics Portal](https://portal.nersc.gov/cfs/e3sm/zhan391/esp-lab_diag/index.html)
- **Features**:
  - **Quick Buttons View**: One-page clickable matrix organized by diagnostic category and figure type.
  - **Driver Mode Filter**: Instant filtering by initialization mode (`init05`, `init11`, `all`, etc.).
  - **Lightbox Modal**: Click any diagnostic button to pop out the full-resolution graphic with caption and download link.

## Data Organization & Output Conventions
Diagnostic outputs are structured in two complementary layers: analysis NetCDF datasets (`S2D_DIAG_ROOT`) and public web figures (`FIGURE_OUTDIR`).

### Diagnostic Data Layout (`S2D_DIAG_ROOT`)
The analysis archive follows an **experiment-first** and **observation-first** canonical structure:

```
<S2D_DIAG_ROOT>/
├── 4DEnVarOcn/          # E3SM S2D with 4DEnVar ocean initial conditions
├── JRA55_FOSIRL/        # E3SM S2D with JRA55/FOSIRL ocean/sea-ice ICs
├── Reanalysis/          # E3SM S2D reanalysis-initialized hindcasts (formerly BruteForce)
├── CESM-SMYLE/          # CESM-SMYLE benchmark hindcasts
├── NMME/                # Multi-model NMME SST benchmark runs
├── observations/        # Observational reference products (ERA5, HadISST, C3S, GPCP)
├── multimodel/          # Cross-experiment combined metrics and teleconnections
└── tmp/                 # File inventories, manifests, and workflow logs
```

### NetCDF File Naming Conventions
Within each experiment or multi-model directory, subdirectories partition datasets by diagnostic type using deterministic naming patterns:

| Diagnostic Area | Directory Path | File Naming Pattern & Example |
|:---|:---|:---|
| **Lead-Time ACC** | `<source>/leadtime_acc/skill/{realm}/{field}/` | `{source}_{field}_{realm}_init{month:02d}_{start}_{end}.nc`<br>*(e.g., `4DEnVarOcn_PRECT_atm_init05_1980_2011.nc`)* |
| **Lead-Time RMSE** | `<source>/leadtime_rmse/inputs/{atm,ocn}/{field}/`<br>`<source>/leadtime_acc/comparison/{realm}/direct_rmse/{field}/` | Inputs: `{source}_{field}_init{month:02d}_years_{start}-{end}_ny{N}.nc`<br>Skill: `{source}_{field}_direct_rmse_init{month:02d}_years_{start}-{end}_ny{N}.nc` |
| **Teleconnections** | `multimodel/leadtime_telec/`<br>`<source>/leadtime_telec/`<br>`observations/leadtime_telec/` | `teleconnection_{index}_{variable}_verify{start}_{end}.nc`<br>*(e.g., `teleconnection_Nino34_TREFHT_verify1981_2011.nc`, `teleconnection_AMO_PSL_verify1981_2011.nc`)* |
| **Modes of Var** | `<source>/modes_variability/` | EOF: `{source}_{mode}_eof_pattern.nc`<br>PC Time Series: `{source}_{mode}_pc_index.nc` |
| **SST & ELI** | `<source>/sst_index/`<br>`<source>/eli/` | Time Series: `{source}_{index}_monthly_ts.nc`<br>Skill: `{source}_{index}_seasonal_acc_rmse.nc` |
| **Initial Shock** | `<source>/initial_shock/` | Shock Metrics: `init{month:02d}_{start}_{end}.nc`<br>*(e.g., `init05_1980_2011.nc`, `init11_1980_2011.nc`)* |

### Figure Naming Conventions (`FIGURE_OUTDIR`)
All diagnostic plots are published into a unified web-accessible root (e.g., `/global/cfs/cdirs/e3sm/www/zhan391/esp-lab_diag/`) with semantic, self-describing scientific naming:

| Diagnostic Group | Notebook | Figure Filename Pattern | Example Figures |
|:---|:---:|:---|:---|
| **Atmospheric ACC** | `1a_atm` | `fig_atm_acc_{field}_{metric}.png` | `fig_atm_acc_prect_acc_compare.png`, `fig_atm_acc_prect_acc_difference.png` |
| **Land ACC** | `1a_lnd` | `fig_lnd_acc_{field}_{metric}.png` | `fig_lnd_acc_tws_acc.png`, `fig_lnd_acc_h2osoi_acc_difference.png` |
| **Spatial RMSE** | `1b_atm` | `fig_atm_rmse_{field}_rmse_{region}.png` | `fig_atm_rmse_prect_rmse_global.png`, `fig_atm_rmse_prect_rmse_conus.png` |
| **Multi-Model RMSE** | `1c_*` | `fig_rmse_compare_{field}_rmse_{type}_{init}.png` | `fig_rmse_compare_prect_rmse_compare_global.png`, `fig_rmse_compare_prect_rmse_difference_compare_init05.png` |
| **Ocean ACC** | `1a_ocn` | `fig_ocn_acc_{field}_{metric}.png` | `fig_ocn_acc_sst_acc_compare.png` |
| **Ocean RMSE** | `1b_ocn` | `fig_ocn_rmse_{field}_rmse_{region}.png` | `fig_ocn_rmse_sst_rmse_global.png` |
| **Land normalized RMSE** | `1b_lnd` | `fig_lnd_rmse_{field}_{metric}.png` | `fig_lnd_rmse_h2osoi_rmse.png` |
| **Regional ACC / nRMSE** | `2a` | `fig_regional_acc_nrmse_{realm}_{field}_{region}.png` | `fig_regional_acc_nrmse_land_tws_global.png` |
| **SST Indices** | `3a` | `fig_sst_index_{index}_{metric}.png` | `fig_sst_index_nino34_acc_skill.png`, `fig_sst_index_nino34_time_series.png` |
| **SST Teleconnections** | `3b` | `fig_teleconnection_{index}_{var}_{metric}.png` | `fig_teleconnection_NINO34_TREFHT_summary.png`, `fig_teleconnection_AMO_H2OSNO_summary.png` |
| **Modes of Var** | `4a` | `fig_mov_{mode}_{metric}.png` | `fig_mov_nam_skill.png`, `fig_mov_pdo_pc_time_series.png` |
| **MOV Teleconnections** | `4b` | `fig_teleconnection_{mode}_{var}_{metric}.png` | `fig_teleconnection_NAO_PRECT_summary.png`, `fig_teleconnection_NAM_PSL_summary.png` |
| **ELI Diagnostics** | `5a`, `5b` | `fig_eli_{metric}.png` | `fig_eli_multimodel_acc_nrmse_skill.png`, `fig_eli_nmme_lead_time_benchmark.png` |
| **ELI Teleconnections** | `5c` | `fig_teleconnection_{index}_{var}_{metric}.png` | `fig_teleconnection_ELI_PRECT_summary.png`, `fig_teleconnection_ELI_TREFHT_summary.png` |
| **Initial Shock Evolution** | `6a` | `fig_shock_ts_{field}_{detail}.png` | `fig_shock_ts_prect_init05-init11_1980_2011_seasonal_absolute_normalized_change.png` |
| **Initial Shock Error** | `6b` | `fig_shock_error_{field}_{detail}.png` | `fig_shock_error_trefht_init1980-2011_clim1981-2010_monthly_normalized_rmse.png` |
| **Tropical Cyclones** | `7a`, `7b` | `fig_tc_{metric}.png` | `fig_tc_genesis_density_method_compare.png`, `fig_tc_tracks_density_sanity_compare.png` |

These figures are automatically cataloged by [`8_run_viewer_webpage.ipynb`](jupyter/8_run_viewer_webpage.ipynb) into `figures.json` and rendered into the interactive web viewer `index.html`.

## Installation

### Developer Installation (Conda Environment)
To install from source and set up a dedicated conda environment:

```bash
git clone -b e3sm-esp https://github.com/zhangshixuan1987/ESP-Lab.git
cd ESP-Lab
conda env create --file environment.yml
conda activate esp-lab
pip install -e .
```

### Installation into Existing Conda Environment
To install ESP-Lab into an existing environment (such as `e3sm_analysis` on NERSC Perlmutter):

```bash
conda activate e3sm_analysis
cd ESP-Lab
pip install -e .
```

### Pip Installation
ESP-Lab can also be installed directly from PyPI:

```bash
pip install esp-lab
```

## Documentation & Links
- **Documentation**: [esp-lab.readthedocs.io](https://esp-lab.readthedocs.io/)
- **Repository**: [github.com/zhangshixuan1987/ESP-Lab](https://github.com/zhangshixuan1987/ESP-Lab)
- **Issue Tracker**: [github.com/zhangshixuan1987/ESP-Lab/issues](https://github.com/zhangshixuan1987/ESP-Lab/issues)
- **Upstream Project**: [CESM-ESPWG/ESP-Lab](https://github.com/CESM-ESPWG/ESP-Lab)

[codecov-badge]: https://img.shields.io/codecov/c/github/zhangshixuan1987/ESP-Lab/e3sm-esp.svg?logo=codecov
[codecov-link]: https://codecov.io/gh/zhangshixuan1987/ESP-Lab
[rtd-badge]: https://img.shields.io/readthedocs/esp-lab/latest.svg
[rtd-link]: https://esp-lab.readthedocs.io/en/latest/?badge=latest
[pypi-badge]: https://img.shields.io/pypi/v/esp-lab?logo=pypi
[pypi-link]: https://pypi.org/project/esp-lab/
[license-badge]: https://img.shields.io/github/license/zhangshixuan1987/ESP-Lab
[repo-link]: https://github.com/zhangshixuan1987/ESP-Lab
