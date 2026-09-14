import json
from pathlib import Path


REPO_ROOT = Path(__file__).parents[1]


def _source(name):
    notebook = json.loads((REPO_ROOT / "jupyter" / name).read_text())
    return "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])


def test_tc_notebooks_use_bounded_parallel_track_parsing():
    for name in (
        "7a_refactor_tc_method_analysis.ipynb",
        "7b_refactor_tc_leadtime_analysis.ipynb",
    ):
        source = _source(name)
        assert '"workers": 4' in source
        assert '"cores": 1' in source
        assert '"memory_limit": "4GB"' in source
        assert 'os.environ.get("CLUSTER_TYPE", "local")' in source
        assert "restart_notebook_cluster(" in source
        assert "close_notebook_resources(globals())" in source

    method_source = _source("7a_refactor_tc_method_analysis.ipynb")
    assert "read_stitch_nodes_tracks_parallel(paths, client=client)" in method_source
    assert "finally:" in method_source

    leadtime_source = _source("7b_refactor_tc_leadtime_analysis.ipynb")
    assert "dask_client=client" in leadtime_source
    assert "TC_DIAGNOSTIC_MODE != \"require\"" in leadtime_source
    assert "any(not path.is_file()" in leadtime_source


def test_eli_notebooks_use_explicit_bounded_dask_settings():
    for name in (
        "8a_refactor_eli_skill_ts.ipynb",
        "8b_refactor_eli_diagnostics.ipynb",
        "8c_refactor_eli_telecon.ipynb",
    ):
        source = _source(name)
        assert '"workers": 4' in source
        assert '"cores": 1' in source
        assert '"memory_limit": "4GB"' in source
        assert 'os.environ.get("CLUSTER_TYPE", "local")' in source
        assert '"workers": 12' not in source
        assert "restart_notebook_cluster(" in source
        assert "close_notebook_resources(globals())" in source


def test_teleconnection_notebook_skips_cluster_for_exact_cache_hit():
    source = _source("8c_refactor_eli_telecon.ipynb")

    assert "telecon.teleconnection_cache_path(CONFIG, inventory)" in source
    assert 'CONFIG["cache"]["mode"] != "require"' in source
    assert 'CONFIG["cache"]["mode"] == "rebuild"' in source
    assert "not expected_cache.is_file()" in source
    assert "if needs_distributed_compute else (None, None)" in source
    assert "metrics_ds.load()" in source
    assert source.index("metrics_ds.load()") < source.index(
        'print("Closed teleconnection Dask resources after cache preparation.")'
    )
