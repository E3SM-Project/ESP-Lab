import json
from pathlib import Path

NOTEBOOK_PATH = Path("/global/homes/z/zhan391/code/ESP-Lab/jupyter/8b_refactor_eli_diagnostics.ipynb")

with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
    nb = json.load(f)

# -------------------------------------------------------------
# 1. Update Cell 5: Configurations
# -------------------------------------------------------------
cell5_source = "".join(nb["cells"][5]["source"])

# NMME_BENCHMARK_PLOT_CONFIG updates
cell5_source = cell5_source.replace(
    '"legend_ncol": 3,',
    '"legend_ncol": 6,'
)
cell5_source = cell5_source.replace(
    '"legend_bbox": (0.5, 0.01),',
    '"legend_bbox": (0.5, 0.015),'
)
cell5_source = cell5_source.replace(
    '"layout_rect": [0, 0.07, 1, 0.965],',
    '"layout_rect": [0, 0.065, 1, 0.94],'
)

# ELI_NINO34_PLOT_CONFIG updates
cell5_source = cell5_source.replace(
    '"figure_title_font_scale": 1.0,\n    "figure_title_y": 0.975,\n    "column_header_font_scale": 1.0,\n    "column_header_y": 1.10,\n    "panel_title_font_scale": 0.9,',
    '"figure_title_font_scale": 1.15,\n    "figure_title_y": 0.985,\n    "column_header_font_scale": 1.05,\n    "column_header_y": 1.10,\n    "panel_title_font_scale": 0.95,'
)
cell5_source = cell5_source.replace(
    '"panel_hspace": 0.24,\n    "panel_wspace": 0.10,\n    "legend_ncol": 2,',
    '"panel_hspace": 0.32,\n    "panel_wspace": 0.12,\n    "legend_ncol": 3,'
)
cell5_source = cell5_source.replace(
    '"legend_bbox": (0.5, 0.012),',
    '"legend_bbox": (0.5, 0.015),'
)
cell5_source = cell5_source.replace(
    '"layout_rect": [0.035, 0.075, 0.965, 0.935],\n    "layout_h_pad": 1.2,\n    "layout_w_pad": 0.9,',
    '"layout_rect": [0.035, 0.065, 0.965, 0.94],\n    "layout_h_pad": 1.4,\n    "layout_w_pad": 0.8,'
)

# DRIFT_CLIMATOLOGY_PLOT_CONFIG updates
old_drift_cfg = """DRIFT_CLIMATOLOGY_PLOT_CONFIG = {
    "figsize": (16, 10.5),
    "dpi": 300,
    "font_size": FONTZ,
    "figure_title": "Lead-dependent ELI and Niño3.4 Climatology",
    "figure_title_font_scale": 1.20,
    "figure_title_y": 0.985,
    "panel_title_font_scale": 1.00,
    "axis_label_font_scale": 0.95,
    "tick_font_scale": 0.85,
    "legend_font_scale": 0.80,
    "obs_line_width": 2.8,
    "eli_obs_color": "tab:green",
    "eli_obs_linestyle": "--",
    "nino34_obs_color": "tab:red",
    "nino34_obs_linestyle": ":",
    "model_line_width": 2.4,
    "ensemble_spread_percentiles": (0, 100),
    "ensemble_spread_alpha": 0.18,
    "grid_alpha": 0.25,
    "lead_tick_interval": 3,
    "legend_loc": "best",
    "legend_frame_alpha": 0.85,
    "init_labels": {5: "May initialization", 11: "November initialization"},
    "eli_obs_label": "ERSSTv5",
    "nino34_obs_label": "HadISST2",
    "eli_ylabel": "ELI climatology (°E)",
    "nino34_ylabel": "Niño3.4 SST climatology (°C)",
    "xlabel": "Lead (months)",
    "layout_rect": [0.035, 0.035, 0.985, 0.945],
    "layout_h_pad": 1.5,
    "layout_w_pad": 1.2,
    "filename_parts": ("eli", "nino34", "multimodel", "drift_climatology"),
    "metric": "eli_nino34_multimodel_drift",
}"""

new_drift_cfg = """DRIFT_CLIMATOLOGY_PLOT_CONFIG = {
    "figsize": (16, 10),
    "dpi": 300,
    "font_size": FONTZ,
    "figure_title": "Lead-dependent ELI and Niño3.4 Climatology (1981–2010)",
    "figure_title_font_scale": 1.30,
    "figure_title_y": 0.965,
    "panel_title_font_scale": 1.05,
    "axis_label_font_scale": 1.00,
    "tick_font_scale": 0.90,
    "legend_font_scale": 0.85,
    "obs_line_width": 2.8,
    "eli_obs_color": "tab:green",
    "eli_obs_linestyle": "--",
    "nino34_obs_color": "tab:red",
    "nino34_obs_linestyle": ":",
    "model_line_width": 2.4,
    "ensemble_spread_percentiles": (0, 100),
    "ensemble_spread_alpha": 0.20,
    "grid_alpha": 0.30,
    "lead_tick_interval": 3,
    "init_labels": {5: "May Initialization", 11: "November Initialization"},
    "eli_obs_label": "ERSSTv5 (ELI)",
    "nino34_obs_label": "HadISST2 (Niño3.4)",
    "eli_ylabel": "ELI Climatology (°E)",
    "nino34_ylabel": "Niño3.4 SST Climatology (°C)",
    "xlabel": "Forecast Lead (months)",
    "filename_parts": ("eli", "nino34", "multimodel", "drift_climatology"),
    "metric": "eli_nino34_multimodel_drift",
}"""

assert old_drift_cfg in cell5_source, "Could not find old_drift_cfg in Cell 5"
cell5_source = cell5_source.replace(old_drift_cfg, new_drift_cfg)
nb["cells"][5]["source"] = [line + "\n" for line in cell5_source.split("\n")][:-1]

# -------------------------------------------------------------
# 2. Update Cell 10: NMME ELI Lead-time Benchmark
# -------------------------------------------------------------
cell10_source = "".join(nb["cells"][10]["source"])

old_cell10_plot = """    fig, axes = plt.subplots(
        len(row_specs), 2,
        figsize=plot_cfg["figsize"],
        squeeze=False,
    )
    fig.suptitle(
        plot_cfg["figure_title"],
        fontsize=fontz * plot_cfg["figure_title_font_scale"],
        fontweight="bold",
        y=plot_cfg["figure_title_y"],
    )
    figlabs = [f"({chr(97 + i)})" for i in range(axes.size)]
    q_low, q_high = plot_cfg["spread_quantiles"]

    for row, row_spec in enumerate(row_specs):
        ax_acc, ax_nrmse = axes[row]
        linewidth = (
            plot_cfg["benchmark_line_width"]
            if row_spec["is_all_init"]
            else plot_cfg["line_width"]
        )
        markersize = (
            plot_cfg["benchmark_marker_size"]
            if row_spec["is_all_init"]
            else plot_cfg["marker_size"]
        )

        for col, (axis, values, spread_values, metric_label, ylim, reference) in enumerate((
            (ax_acc, row_spec["acc"], row_spec["spread_acc"], plot_cfg["acc_label"], plot_cfg["acc_ylim"], plot_cfg["acc_reference"]),
            (ax_nrmse, row_spec["nrmse"], row_spec["spread_nrmse"], plot_cfg["nrmse_label"], plot_cfg["nrmse_ylim"], plot_cfg["nrmse_reference"]),
        )):
            axis.fill_between(
                x,
                spread_values.quantile(q_low, "bootstrap"),
                spread_values.quantile(q_high, "bootstrap"),
                color=row_spec["color"],
                alpha=plot_cfg["spread_alpha"],
                linewidth=0,
                label=plot_cfg["spread_label"],
            )
            axis.plot(
                x,
                values,
                color=row_spec["color"],
                linewidth=linewidth,
                marker=row_spec["marker"],
                markersize=markersize,
                label=row_spec["line_label"],
                zorder=5,
            )
            axis.set_title(
                f"{figlabs[row * 2 + col]} {row_spec['label']}: {metric_label}",
                loc="left",
                fontsize=panel_title_fontz,
            )
            axis.set_ylabel(metric_label, fontsize=axis_label_fontz)
            axis.set_xticks(x)
            if plot_cfg["show_model_counts"]:
                count_labels = [
                    f"{int(lead)}\\nN={median:.0f}"
                    for lead, median in zip(x, row_spec["count_median"].values)
                ]
                axis.set_xticklabels(
                    count_labels,
                    fontsize=model_count_fontz,
                )
            if plot_cfg["xlabels_on_all_rows"] or row == len(row_specs) - 1:
                xlabel = (
                    plot_cfg["model_count_axis_label"]
                    if plot_cfg["show_model_counts"]
                    else plot_cfg["lead_axis_label"]
                )
                axis.set_xlabel(xlabel, fontsize=axis_label_fontz)
            axis.set_xlim([
                float(x.min()) - plot_cfg["lead_axis_margin"],
                float(x.max()) + plot_cfg["lead_axis_margin"],
            ])
            axis.set_ylim(ylim)
            axis.grid(True, alpha=plot_cfg["grid_alpha"])
            axis.axhline(
                reference,
                color=plot_cfg["reference_color"],
                linestyle=plot_cfg["reference_linestyle"],
                linewidth=plot_cfg["reference_line_width"],
            )

    legend_handles = [
        Line2D(
            [0], [0],
            color=plot_cfg["startmonth_colors"][month],
            linewidth=plot_cfg["line_width"],
            marker=plot_cfg["startmonth_markers"][month],
            markersize=plot_cfg["marker_size"],
            label=plot_cfg["startmonth_labels"][month],
        )
        for month in startmonths
    ]
    legend_handles.extend([
        Line2D(
            [0], [0],
            color=plot_cfg["benchmark_color"],
            linewidth=plot_cfg["benchmark_line_width"],
            marker=plot_cfg["benchmark_marker"],
            markersize=plot_cfg["benchmark_marker_size"],
            label=plot_cfg["benchmark_label"],
        ),
        Patch(
            facecolor=plot_cfg["legend_spread_color"],
            alpha=plot_cfg["spread_alpha"],
            edgecolor="none",
            label=plot_cfg["spread_label"],
        ),
    ])
    fig.legend(
        handles=legend_handles,
        loc=plot_cfg["legend_loc"],
        ncol=plot_cfg["legend_ncol"],
        bbox_to_anchor=plot_cfg["legend_bbox"],
        fontsize=legend_fontz,
        frameon=True,
    )"""

new_cell10_plot = """    fig, axes = plt.subplots(
        len(row_specs), 2,
        figsize=plot_cfg["figsize"],
        sharex=True,
        squeeze=False,
    )
    fig.suptitle(
        plot_cfg["figure_title"],
        fontsize=fontz * plot_cfg["figure_title_font_scale"],
        fontweight="bold",
        y=plot_cfg["figure_title_y"],
    )
    figlabs = [f"({chr(97 + i)})" for i in range(axes.size)]
    q_low, q_high = plot_cfg["spread_quantiles"]

    for row, row_spec in enumerate(row_specs):
        ax_acc, ax_nrmse = axes[row]
        linewidth = (
            plot_cfg["benchmark_line_width"]
            if row_spec["is_all_init"]
            else plot_cfg["line_width"]
        )
        markersize = (
            plot_cfg["benchmark_marker_size"]
            if row_spec["is_all_init"]
            else plot_cfg["marker_size"]
        )

        for col, (axis, values, spread_values, metric_name, ylim, reference) in enumerate((
            (ax_acc, row_spec["acc"], row_spec["spread_acc"], plot_cfg["acc_label"], plot_cfg["acc_ylim"], plot_cfg["acc_reference"]),
            (ax_nrmse, row_spec["nrmse"], row_spec["spread_nrmse"], plot_cfg["nrmse_label"], plot_cfg["nrmse_ylim"], plot_cfg["nrmse_reference"]),
        )):
            axis.fill_between(
                x,
                spread_values.quantile(q_low, "bootstrap"),
                spread_values.quantile(q_high, "bootstrap"),
                color=row_spec["color"],
                alpha=plot_cfg["spread_alpha"],
                linewidth=0,
                label=plot_cfg["spread_label"],
            )
            axis.plot(
                x,
                values,
                color=row_spec["color"],
                linewidth=linewidth,
                marker=row_spec["marker"],
                markersize=markersize,
                label=row_spec["line_label"],
                zorder=5,
            )
            axis.set_title(
                f"{figlabs[row * 2 + col]} {row_spec['label']}",
                loc="left",
                fontsize=panel_title_fontz,
                fontweight="bold",
                pad=6,
            )
            axis.set_ylabel(metric_name, fontsize=axis_label_fontz, fontweight="bold")
            axis.set_xticks(x)
            axis.set_xlim([
                float(x.min()) - plot_cfg["lead_axis_margin"],
                float(x.max()) + plot_cfg["lead_axis_margin"],
            ])
            axis.set_ylim(ylim)
            axis.grid(True, alpha=plot_cfg["grid_alpha"])
            axis.axhline(
                reference,
                color=plot_cfg["reference_color"],
                linestyle=plot_cfg["reference_linestyle"],
                linewidth=plot_cfg["reference_line_width"],
            )

            if row == len(row_specs) - 1:
                count_labels = [
                    f"{int(lead)}\\nN={median:.0f}"
                    for lead, median in zip(x, row_spec["count_median"].values)
                ]
                axis.set_xticklabels(
                    count_labels,
                    fontsize=model_count_fontz,
                )
                axis.set_xlabel(plot_cfg["model_count_axis_label"], fontsize=axis_label_fontz)
            else:
                axis.tick_params(labelbottom=False)

    fig.tight_layout(
        rect=plot_cfg["layout_rect"],
        h_pad=plot_cfg["layout_h_pad"],
        w_pad=plot_cfg["layout_w_pad"],
    )

    pos_acc = axes[0, 0].get_position()
    pos_nrmse = axes[0, 1].get_position()
    header_y = pos_acc.y1 + 0.016
    fig.text(
        (pos_acc.x0 + pos_acc.x1) / 2, header_y,
        "Anomaly Correlation (ACC)",
        ha="center", va="bottom",
        fontsize=fontz * 1.05, fontweight="bold",
        color="0.15",
    )
    fig.text(
        (pos_nrmse.x0 + pos_nrmse.x1) / 2, header_y,
        "Normalized RMSE (nRMSE)",
        ha="center", va="bottom",
        fontsize=fontz * 1.05, fontweight="bold",
        color="0.15",
    )

    legend_handles = [
        Line2D(
            [0], [0],
            color=plot_cfg["startmonth_colors"][month],
            linewidth=plot_cfg["line_width"],
            marker=plot_cfg["startmonth_markers"][month],
            markersize=plot_cfg["marker_size"],
            label=plot_cfg["startmonth_labels"][month],
        )
        for month in startmonths
    ]
    legend_handles.extend([
        Line2D(
            [0], [0],
            color=plot_cfg["benchmark_color"],
            linewidth=plot_cfg["benchmark_line_width"],
            marker=plot_cfg["benchmark_marker"],
            markersize=plot_cfg["benchmark_marker_size"],
            label=plot_cfg["benchmark_label"],
        ),
        Patch(
            facecolor=plot_cfg["legend_spread_color"],
            alpha=plot_cfg["spread_alpha"],
            edgecolor="none",
            label=plot_cfg["spread_label"],
        ),
    ])
    fig.legend(
        handles=legend_handles,
        loc=plot_cfg["legend_loc"],
        ncol=plot_cfg["legend_ncol"],
        bbox_to_anchor=plot_cfg["legend_bbox"],
        fontsize=legend_fontz,
        frameon=True,
    )"""

assert old_cell10_plot in cell10_source, "Could not find old_cell10_plot in Cell 10"
cell10_source = cell10_source.replace(old_cell10_plot, new_cell10_plot)
nb["cells"][10]["source"] = [line + "\n" for line in cell10_source.split("\n")][:-1]

# -------------------------------------------------------------
# 3. Update Cell 15: Dual-Axis ELI-Niño3.4 Comparison
# -------------------------------------------------------------
cell15_source = "".join(nb["cells"][15]["source"])

old_cell15_plot = """            line_eli, = ax_eli.plot(
                dates, eli_values, color=plot_cfg["eli_color"],
                linewidth=plot_cfg["line_width"], label=plot_cfg["eli_label"],
            )
            line_nino34, = ax_nino34.plot(
                dates, nino34_values, color=plot_cfg["nino34_color"],
                linewidth=plot_cfg["line_width"], label=plot_cfg["nino34_label"],
            )
            ax_eli.set_ylim(plot_cfg["eli_ylim"])
            ax_eli.set_yticks(plot_cfg["eli_yticks"])
            ax_nino34.set_ylim(plot_cfg["nino34_ylim"])
            ax_nino34.set_yticks(plot_cfg["nino34_yticks"])
            ax_eli.tick_params(
                axis="y", colors=plot_cfg["eli_color"],
                labelleft=(col == 0), labelsize=tick_fontz,
            )
            ax_nino34.tick_params(
                axis="y", colors=plot_cfg["nino34_color"],
                labelright=(col == ncols - 1), labelsize=tick_fontz,
            )
            ax_eli.tick_params(axis="x", labelsize=tick_fontz)
            if col == 0:
                ax_eli.set_ylabel(
                    plot_cfg["eli_axis_label"], color=plot_cfg["eli_color"],
                    fontsize=axis_label_fontz,
                )
            if col == ncols - 1:
                ax_nino34.set_ylabel(
                    plot_cfg["nino34_axis_label"], color=plot_cfg["nino34_color"],
                    fontsize=axis_label_fontz,
                )
            ax_nino34.axhline(
                0, color=plot_cfg["zero_line_color"],
                linewidth=plot_cfg["zero_line_width"],
            )
            ax_eli.grid(True, alpha=plot_cfg["grid_alpha"])
            panel_index = row * ncols + col
            stats = result["correlation_stats"][source_label]
            r_label = f"r={stats['mean']:.2f}"
            if stats["std"] is not None:
                r_label += f" ± {stats['std']:.3f}"
            ax_eli.set_title(
                f"({chr(97 + panel_index)}) {source_label} "
                f"({r_label})",
                loc="left", fontsize=panel_title_fontz,
            )
            if row == 0:
                ax_eli.text(
                    0.5, plot_cfg["column_header_y"], result["config"]["label"],
                    transform=ax_eli.transAxes, ha="center", va="bottom",
                    fontsize=column_header_fontz, fontweight="bold",
                )
            if row == nrows - 1:
                ax_eli.set_xlabel(
                    plot_cfg["target_year_label"], fontsize=axis_label_fontz
                )

    fig.legend(
        handles=[line_eli, line_nino34],
        labels=[plot_cfg["eli_label"], plot_cfg["nino34_label"]],
        loc=plot_cfg["legend_loc"],
        ncol=plot_cfg["legend_ncol"],
        bbox_to_anchor=plot_cfg["legend_bbox"],
        fontsize=legend_fontz, frameon=True,
        facecolor=plot_cfg["legend_facecolor"],
        edgecolor=plot_cfg["legend_edgecolor"],
        framealpha=plot_cfg["legend_frame_alpha"],
    )
    fig.suptitle(
        plot_cfg["figure_title_template"].format(
            verification_period=plot_cfg["verification_period"]
        ),
        fontsize=figure_title_fontz, fontweight="bold",
        y=plot_cfg["figure_title_y"],
    )
    fig.tight_layout(
        rect=plot_cfg["layout_rect"],
        h_pad=plot_cfg["layout_h_pad"],
        w_pad=plot_cfg["layout_w_pad"],
    )
    fig.subplots_adjust(
        hspace=plot_cfg["panel_hspace"], wspace=plot_cfg["panel_wspace"]
    )"""

new_cell15_plot = """            line_eli, = ax_eli.plot(
                dates, eli_values, color=plot_cfg["eli_color"],
                linewidth=plot_cfg["line_width"], label=plot_cfg["eli_label"], zorder=4,
            )
            line_nino34, = ax_nino34.plot(
                dates, nino34_values, color=plot_cfg["nino34_color"],
                linewidth=plot_cfg["line_width"], label=plot_cfg["nino34_label"], zorder=4,
            )
            ax_eli.set_ylim(plot_cfg["eli_ylim"])
            ax_eli.set_yticks(plot_cfg["eli_yticks"])
            ax_nino34.set_ylim(plot_cfg["nino34_ylim"])
            ax_nino34.set_yticks(plot_cfg["nino34_yticks"])
            ax_eli.tick_params(
                axis="y", colors=plot_cfg["eli_color"],
                labelleft=(col == 0), labelsize=tick_fontz,
            )
            ax_nino34.tick_params(
                axis="y", colors=plot_cfg["nino34_color"],
                labelright=(col == ncols - 1), labelsize=tick_fontz,
            )
            ax_eli.tick_params(axis="x", labelsize=tick_fontz)
            if col == 0:
                ax_eli.set_ylabel(
                    plot_cfg["eli_axis_label"], color=plot_cfg["eli_color"],
                    fontsize=axis_label_fontz, fontweight="bold",
                )
            if col == ncols - 1:
                ax_nino34.set_ylabel(
                    plot_cfg["nino34_axis_label"], color=plot_cfg["nino34_color"],
                    fontsize=axis_label_fontz, fontweight="bold",
                )
            ax_nino34.axhline(
                0, color=plot_cfg["zero_line_color"],
                linewidth=plot_cfg["zero_line_width"], linestyle="--", alpha=0.7,
            )
            ax_eli.grid(True, alpha=plot_cfg["grid_alpha"])

            panel_index = row * ncols + col
            stats = result["correlation_stats"][source_label]
            r_str = f"r = {stats['mean']:.2f}"
            if stats["std"] is not None:
                r_str += f" ± {stats['std']:.2f}"

            ax_eli.set_title(
                f"({chr(97 + panel_index)}) {source_label}",
                loc="left", fontsize=panel_title_fontz, fontweight="bold", pad=5,
            )
            ax_eli.set_title(
                r_str,
                loc="right", fontsize=panel_title_fontz * 0.95, color="0.25", pad=5,
            )

            if row == nrows - 1:
                ax_eli.set_xlabel(
                    plot_cfg["target_year_label"], fontsize=axis_label_fontz, fontweight="bold",
                )

    fig.tight_layout(
        rect=plot_cfg["layout_rect"],
        h_pad=plot_cfg["layout_h_pad"],
        w_pad=plot_cfg["layout_w_pad"],
    )
    fig.subplots_adjust(
        hspace=plot_cfg["panel_hspace"], wspace=plot_cfg["panel_wspace"]
    )

    for col, result in enumerate(column_results):
        top_ax = axes[0, col]
        pos = top_ax.get_position()
        center_x = (pos.x0 + pos.x1) / 2
        header_y = pos.y1 + 0.024
        line_y = pos.y1 + 0.016
        fig.text(
            center_x, header_y,
            result["config"]["label"].upper(),
            ha="center", va="bottom",
            fontsize=column_header_fontz, fontweight="bold",
            color="0.15",
        )
        fig.add_artist(plt.Line2D(
            [pos.x0, pos.x1], [line_y, line_y],
            transform=fig.transFigure,
            color="0.4", linewidth=1.2,
        ))

    fig.suptitle(
        plot_cfg["figure_title_template"].format(
            verification_period=plot_cfg["verification_period"]
        ),
        fontsize=figure_title_fontz, fontweight="bold",
        y=plot_cfg["figure_title_y"],
    )

    legend_handles = [
        line_eli,
        line_nino34,
        Patch(
            facecolor="0.6",
            alpha=plot_cfg["ensemble_spread_alpha"] * 1.5,
            edgecolor="none",
            label="Ensemble range (min–max)",
        ),
    ]
    legend_labels = [plot_cfg["eli_label"], plot_cfg["nino34_label"], "Ensemble range (min–max)"]

    fig.legend(
        handles=legend_handles,
        labels=legend_labels,
        loc=plot_cfg["legend_loc"],
        ncol=plot_cfg["legend_ncol"],
        bbox_to_anchor=plot_cfg["legend_bbox"],
        fontsize=legend_fontz,
        frameon=True,
        facecolor=plot_cfg["legend_facecolor"],
        edgecolor=plot_cfg["legend_edgecolor"],
        framealpha=plot_cfg["legend_frame_alpha"],
    )"""

assert old_cell15_plot in cell15_source, "Could not find old_cell15_plot in Cell 15"
cell15_source = cell15_source.replace(old_cell15_plot, new_cell15_plot)
nb["cells"][15]["source"] = [line + "\n" for line in cell15_source.split("\n")][:-1]

# -------------------------------------------------------------
# 4. Update Cell 18: Lead-dependent Drift Climatology
# -------------------------------------------------------------
cell18_source = "".join(nb["cells"][18]["source"])

old_cell18_plot = """diagnostic_rows = [
    {
        "name": "ELI", "obs": obs_clim, "models": eli_member_clim,
        "obs_label": plot_cfg["eli_obs_label"],
        "obs_color": plot_cfg["eli_obs_color"],
        "obs_linestyle": plot_cfg["eli_obs_linestyle"],
        "ylabel": plot_cfg["eli_ylabel"],
    },
    {
        "name": "Niño3.4", "obs": nino34_obs_clim,
        "models": nino34_member_clim,
        "obs_label": plot_cfg["nino34_obs_label"],
        "obs_color": plot_cfg["nino34_obs_color"],
        "obs_linestyle": plot_cfg["nino34_obs_linestyle"],
        "ylabel": plot_cfg["nino34_ylabel"],
    },
]

plt.rcParams.update({
    "font.size": fontz,
    "axes.titlesize": panel_title_fontz,
    "axes.labelsize": axis_label_fontz,
    "xtick.labelsize": tick_fontz,
    "ytick.labelsize": tick_fontz,
    "legend.fontsize": legend_fontz,
})
fig, axes = plt.subplots(
    len(diagnostic_rows), len(INIT_MONTHS),
    figsize=plot_cfg["figsize"], sharex=True, sharey="row", squeeze=False,
)

for col, month in enumerate(INIT_MONTHS):
    reference_times = eli_time[next(iter(MODEL_SPECS))][month].isel(Y=0)
    target_months = np.asarray(reference_times.dt.month.values, dtype=int)
    leads = np.asarray(reference_times.L.values, dtype=int)
    lead_axis = leads - 1

    for row, diagnostic in enumerate(diagnostic_rows):
        ax = axes[row, col]
        obs_target_clim = np.asarray([
            float(diagnostic["obs"].sel(month=target_month))
            for target_month in target_months
        ])
        ax.plot(
            lead_axis, obs_target_clim, color=diagnostic["obs_color"],
            linewidth=plot_cfg["obs_line_width"],
            linestyle=diagnostic["obs_linestyle"],
            label=diagnostic["obs_label"], zorder=4,
        )

        for model, spec in MODEL_SPECS.items():
            member_clim = diagnostic["models"][model][month].sel(L=leads)
            model_mean = member_clim.mean("M", skipna=True)
            model_lower = member_clim.quantile(spread_low / 100, dim="M", skipna=True)
            model_upper = member_clim.quantile(spread_high / 100, dim="M", skipna=True)
            ax.fill_between(
                lead_axis, model_lower, model_upper, color=spec.color,
                alpha=plot_cfg["ensemble_spread_alpha"], linewidth=0, zorder=1,
            )
            ax.plot(
                lead_axis, model_mean, color=spec.color,
                linewidth=plot_cfg["model_line_width"],
                label=spec.label, zorder=3,
            )

        panel_index = row * len(INIT_MONTHS) + col
        ax.set_title(
            f"({chr(97 + panel_index)}) {diagnostic['name']} | "
            f"{plot_cfg['init_labels'][month]}",
            loc="left", fontsize=panel_title_fontz,
        )
        if col == 0:
            ax.set_ylabel(diagnostic["ylabel"], fontsize=axis_label_fontz)
        if row == len(diagnostic_rows) - 1:
            ax.set_xlabel(plot_cfg["xlabel"], fontsize=axis_label_fontz)
        ax.grid(True, alpha=plot_cfg["grid_alpha"])
        ax.tick_params(axis="both", labelsize=tick_fontz)
        ax.xaxis.set_major_locator(
            mticker.MultipleLocator(plot_cfg["lead_tick_interval"])
        )
        ax.legend(
            loc=plot_cfg["legend_loc"], fontsize=legend_fontz, frameon=True,
            framealpha=plot_cfg["legend_frame_alpha"],
        )

fig.suptitle(
    plot_cfg["figure_title"], fontsize=figure_title_fontz,
    fontweight="bold", y=plot_cfg["figure_title_y"],
)
fig.tight_layout(
    rect=plot_cfg["layout_rect"],
    h_pad=plot_cfg["layout_h_pad"],
    w_pad=plot_cfg["layout_w_pad"],
)"""

new_cell18_plot = """diagnostic_rows = [
    {
        "name": "ELI", "title": "ELI Climatology", "obs": obs_clim, "models": eli_member_clim,
        "obs_label": plot_cfg["eli_obs_label"],
        "obs_color": plot_cfg["eli_obs_color"],
        "obs_linestyle": plot_cfg["eli_obs_linestyle"],
        "ylabel": plot_cfg["eli_ylabel"],
    },
    {
        "name": "Niño3.4", "title": "Niño3.4 SST Climatology", "obs": nino34_obs_clim,
        "models": nino34_member_clim,
        "obs_label": plot_cfg["nino34_obs_label"],
        "obs_color": plot_cfg["nino34_obs_color"],
        "obs_linestyle": plot_cfg["nino34_obs_linestyle"],
        "ylabel": plot_cfg["nino34_ylabel"],
    },
]

plt.rcParams.update({
    "font.size": fontz,
    "axes.titlesize": panel_title_fontz,
    "axes.titleweight": "bold",
    "axes.labelsize": axis_label_fontz,
    "xtick.labelsize": tick_fontz,
    "ytick.labelsize": tick_fontz,
})
fig, axes = plt.subplots(
    len(diagnostic_rows), len(INIT_MONTHS),
    figsize=plot_cfg["figsize"], sharex=True, sharey="row", squeeze=False,
)

fig.subplots_adjust(top=0.85, bottom=0.11, left=0.08, right=0.96, hspace=0.25, wspace=0.08)

fig.suptitle(
    plot_cfg["figure_title"], fontsize=figure_title_fontz,
    fontweight="bold", y=plot_cfg["figure_title_y"],
)

panel_letters = [["a", "b"], ["c", "d"]]

for col, month in enumerate(INIT_MONTHS):
    reference_times = eli_time[next(iter(MODEL_SPECS))][month].isel(Y=0)
    target_months = np.asarray(reference_times.dt.month.values, dtype=int)
    leads = np.asarray(reference_times.L.values, dtype=int)
    lead_axis = leads - 1

    top_ax = axes[0, col]
    bbox = top_ax.get_position()
    col_center_x = (bbox.x0 + bbox.x1) / 2.0
    fig.text(
        col_center_x, 0.905,
        plot_cfg["init_labels"][month],
        ha="center", va="center",
        fontsize=fontz * 1.15,
        fontweight="bold",
        color="#1f2937",
    )
    col_line = plt.Line2D(
        [bbox.x0 + 0.03, bbox.x1 - 0.03], [0.885, 0.885],
        transform=fig.transFigure, color="#cbd5e1", linewidth=1.5,
    )
    fig.add_artist(col_line)

    for row, diagnostic in enumerate(diagnostic_rows):
        ax = axes[row, col]
        obs_target_clim = np.asarray([
            float(diagnostic["obs"].sel(month=target_month))
            for target_month in target_months
        ])
        ax.plot(
            lead_axis, obs_target_clim, color=diagnostic["obs_color"],
            linewidth=plot_cfg["obs_line_width"],
            linestyle=diagnostic["obs_linestyle"],
            zorder=4,
        )

        for model, spec in MODEL_SPECS.items():
            member_clim = diagnostic["models"][model][month].sel(L=leads)
            model_mean = member_clim.mean("M", skipna=True)
            model_lower = member_clim.quantile(spread_low / 100, dim="M", skipna=True)
            model_upper = member_clim.quantile(spread_high / 100, dim="M", skipna=True)
            ax.fill_between(
                lead_axis, model_lower, model_upper, color=spec.color,
                alpha=plot_cfg["ensemble_spread_alpha"], linewidth=0, zorder=1,
            )
            ax.plot(
                lead_axis, model_mean, color=spec.color,
                linewidth=plot_cfg["model_line_width"],
                zorder=3,
            )

        letter = panel_letters[row][col]
        ax.set_title(
            f"({letter}) {diagnostic['title']}",
            loc="left", pad=8,
        )
        if col == 0:
            ax.set_ylabel(diagnostic["ylabel"], fontsize=axis_label_fontz)
        else:
            ax.tick_params(labelleft=False)

        if row == len(diagnostic_rows) - 1:
            ax.set_xlabel(plot_cfg["xlabel"], fontsize=axis_label_fontz)

        ax.grid(True, linestyle="--", alpha=plot_cfg["grid_alpha"])
        ax.xaxis.set_major_locator(
            mticker.MultipleLocator(plot_cfg["lead_tick_interval"])
        )
        ax.set_xlim(-0.5, 23.5)

legend_elements = [
    Line2D([0], [0], color=plot_cfg["eli_obs_color"], lw=2.8, linestyle=plot_cfg["eli_obs_linestyle"], label=plot_cfg["eli_obs_label"]),
    Line2D([0], [0], color=plot_cfg["nino34_obs_color"], lw=2.8, linestyle=plot_cfg["nino34_obs_linestyle"], label=plot_cfg["nino34_obs_label"]),
]
for model, spec in MODEL_SPECS.items():
    legend_elements.append(
        Line2D([0], [0], color=spec.color, lw=2.4, label=spec.label)
    )
legend_elements.append(
    Patch(facecolor="#6b7280", edgecolor="none", alpha=0.35, label="Ensemble range (min–max)")
)

fig.legend(
    handles=legend_elements,
    loc="lower center",
    bbox_to_anchor=(0.50, 0.02),
    ncol=7,
    frameon=True,
    facecolor="#f9fafb",
    edgecolor="#d1d5db",
    framealpha=0.95,
    fontsize=legend_fontz,
    columnspacing=1.4,
    handlelength=2.0,
    borderpad=0.5,
)"""

assert old_cell18_plot in cell18_source, "Could not find old_cell18_plot in Cell 18"
cell18_source = cell18_source.replace(old_cell18_plot, new_cell18_plot)
nb["cells"][18]["source"] = [line + "\n" for line in cell18_source.split("\n")][:-1]

# Write updated notebook back
with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Successfully updated 8b_refactor_eli_diagnostics.ipynb (Cells 5, 10, 15, 18)!")

