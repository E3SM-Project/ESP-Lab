import pandas as pd

from workflows.tropical_cyclones.track_density import (
    read_stitch_nodes_tracks,
    read_stitch_nodes_tracks_parallel,
)


class InlineClient:
    """Minimal Client.map/gather implementation for deterministic unit tests."""

    def __init__(self):
        self.map_calls = 0

    def map(self, function, *iterables, **kwargs):
        self.map_calls += 1
        return [function(*arguments) for arguments in zip(*iterables)]

    def gather(self, futures):
        return futures


def _track_file(tmp_path, case, member, longitude):
    path = (
        tmp_path / case / member / "post" / "atm" / "tc-analysis"
        / f"{case}_{member}_set3_TCS_track.txt"
    )
    path.parent.mkdir(parents=True)
    path.write_text(
        f"start\n0 {longitude} 10 99000 20 0 1980 6 1 0\n"
    )
    return path


def test_parallel_track_reader_matches_serial_result(tmp_path):
    case = "example_case_1980050100"
    paths = [
        _track_file(tmp_path, case, "EN00", 150),
        _track_file(tmp_path, case, "EN01", 160),
    ]
    client = InlineClient()

    serial = read_stitch_nodes_tracks(paths).sort_values(["member", "time"])
    parallel = read_stitch_nodes_tracks_parallel(
        paths, client=client
    ).sort_values(["member", "time"])

    assert client.map_calls == 1
    pd.testing.assert_frame_equal(
        parallel.reset_index(drop=True), serial.reset_index(drop=True)
    )
