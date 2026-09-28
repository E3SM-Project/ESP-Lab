# NMME modes-of-variability Slurm wrappers

These templates run the NMME source adapter and the P6/P7 cross-source
workflows on a Slurm system.  They deliberately retain each NMME model's
native lead availability: never pad leads that are absent from an archive.

Before submission, export these paths or edit the defaults in a local copy:

```bash
export ESP_LAB_ROOT=/path/to/ESP-Lab
export E3SM_ENV_SCRIPT=/path/to/site/environment.sh
export NMME_ROOT=/path/to/NMME-all
export OUTPUT_ROOT=/path/to/durable/output
```

`run_nmme_sst_mov_independent_models.slurm` is an array template.  It writes
one fixed-HadISST2 projected-index product per model; that separation is
required before forming a selected-model or all-model P6 comparison.
`render_p6_common_cohort.slurm` then builds the selected-CMC1 and equal-model
all-NMME P6 products from those independent inputs.  It also needs
`P6_SOURCE_ROOT`, an existing E3SM/SMYLE/HadISST2 source-product root.

The P7 plotting utilities are library functions in
`workflows.modes_of_variability.cross_source`; site-specific jobs should use
the same source-native, no-difference, member/model-spread conventions.
