# Monthly standardized forecast-error RMSE and MAE

Open [`jupyter/6b_refactor_shock_index.ipynb`](../jupyter/6b_refactor_shock_index.ipynb).

This workflow is the error-metric companion to
[`6a_refactor_shock_ts.ipynb`](../jupyter/6a_refactor_shock_ts.ipynb). It reuses
6a's exact-period caches, archive discovery, strict ensemble checks,
verification-time validation, unit conversion, conservative regridding, area
weighting, and global monthly indices.

## Shared observed climatology

One reference-observation climatology is calculated by calendar month over the
configured climatology years. The same monthly mean and standard deviation are
used for every case, initialization month, ensemble member, and verification
lead:

\[
m'_t=\frac{m_t-C_{\mathrm{obs},month(t)}}
           {\sigma_{\mathrm{obs},month(t)}},\qquad
o'_t=\frac{o_t-C_{\mathrm{obs},month(t)}}
           {\sigma_{\mathrm{obs},month(t)}}.
\]

Their difference is the standardized forecast error

\[
e_t=m'_t-o'_t=\frac{m_t-o_t}{\sigma_{\mathrm{obs},month(t)}}.
\]

The shared observed mean removes the reference seasonal cycle from each anomaly,
and the month-specific observed scale puts anomalies in comparable variability
units. The mean cancels from their paired difference, so systematic—including
season-dependent—model error is retained. Independently centering the model
would instead remove part of that error.

## Primary and seasonal metrics

For each initialization, the primary metrics reduce the 24 monthly errors:

\[
\operatorname{NRMSE}=\sqrt{\frac{1}{n}\sum_t e_t^2},\qquad
\operatorname{NMAE}=\frac{1}{n}\sum_t |e_t|.
\]

Raw RMSE and MAE are also calculated from \(m_t-o_t\) and retain the physical
units of the field. The same normalized calculations are stored for the first
ensemble member and the ensemble mean. Seasonal metrics retain forecast lead
year and verification season and reduce the three monthly errors belonging to
each season.

The primary figure compares first-member and ensemble-mean NRMSE, with May and
November initialization cohorts in separate rows. Supplementary figures show
ensemble-mean seasonal NRMSE for each forecast lead year. NMAE remains in the
tables and caches as a robustness measure without duplicating the primary
heatmap.

## Cache behavior and legacy compatibility

Set the notebook's top-level `FORCE_COMPUTE=True` to rebuild the selected
exact-period 6a and 6b caches. With the default `False`, compatible products are
reused and only missing or stale products are computed. Table and figure names
include both initialization and climatology periods.

The former independently centered annual-block calculation is available as
`compute_legacy_initial_shock_error_index` for explicit comparisons with
the legacy NCL calculation (`Compute_RMSE_With_MAE_Index_share.ncl`).
It is not the default 6b metric because a 24-month forecast supplies only two
annual-block samples and hides seasonal error evolution.
