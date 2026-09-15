# Workflow package layout

The `workflows` package contains high-level orchestration modules directly supporting the `jupyter/` analysis suite (0 through 7). Reusable calculations and data access primitives belong in `esp_lab`.

| Package | Supported Notebooks | Purpose |
|---|---|---|
| `leadtime_skill` | `2b` | Lead-time RMSE comparison and multi-model metrics |
| `modes_of_variability` | `4a`, `4b` | Modes-of-variability processing, EOF projection, and teleconnection analysis |
| `diagnostics` | `3b`, `4b`, `5c`, `6a`, `6b` | Teleconnections (`sst_teleconnections`, `mov_teleconnections`, `teleconnection_inputs`) and initial-shock archive runners |

Each workflow package maintains configuration, discovery, preprocessing, diagnostics, and plotting together. Generated data, figures, and notebook checkpoints do not belong under this directory.
