"""Tests for centralized modes-of-variability figure configuration."""

import numpy as np

from workflows.modes_of_variability import figure_config


EXPECTED_MODES = {
    "NAM", "NAO", "SAM", "PNA", "NPO", "PDO", "NPGO", "EA", "SCA",
    "AMO", "PSA1", "PSA2",
}


def test_every_supported_plot_mode_has_one_profile():
    assert set(figure_config.MODE_FIGURE_PROFILES) == EXPECTED_MODES


def test_resolved_settings_do_not_mutate_shared_presets():
    first = figure_config.get_eof_pattern_settings("PNA")
    first["preferred_init_by_season"]["DJF"] = 5
    first["levels"][0] = 999

    second = figure_config.get_eof_pattern_settings("PNA")
    assert second["preferred_init_by_season"]["DJF"] == 11
    assert second["levels"][0] == -3.0


def test_pressure_and_temperature_profiles_use_expected_contours():
    np.testing.assert_allclose(
        figure_config.get_eof_pattern_settings("PNA")["levels"],
        np.arange(-3.0, 3.01, 0.5),
    )
    np.testing.assert_allclose(
        figure_config.get_eof_pattern_settings("PDO")["levels"],
        np.arange(-1.0, 1.01, 0.2),
    )


def test_global_teleconnection_overrides_are_shared():
    for mode in EXPECTED_MODES:
        settings = figure_config.get_teleconnection_settings(mode)
        assert settings["figsize_width"] == 16.0
        assert settings["longitude_ticks"].tolist() == [-180, -120, -60, 0, 60, 120, 180]


def test_nao_eof_layout_is_wide_and_npo_profile_stays_unchanged():
    nao = figure_config.get_eof_pattern_settings("NAO")
    npo = figure_config.get_eof_pattern_settings("NPO")

    assert nao["figsize_width"] == 15.5
    assert nao["figsize_row_height"] == 2.0
    assert nao["subplot_wspace"] == 0.08
    assert nao["subplot_hspace"] == 0.18

    assert npo["figsize_width"] == 15.5
    assert npo["figsize_row_height"] == 2.0
    assert npo["subplot_wspace"] == 0.08
    assert npo["subplot_hspace"] == 0.22
    assert npo["panel_title_two_lines"] is False


def test_complete_setup_preserves_public_notebook_sections():
    setup = figure_config.build_figure_setup("PNA", include_nmme=True)
    assert set(setup) == {"common", "eof_patterns", "teleconnections", "skill", "pc_time_series"}
    assert setup["pc_time_series"]["annotation_band_height"] == 4.2
    assert figure_config.metric_specs("PNA")[1][2] == (0.6, 1.3)
