"""
Utilities for accessing post-processed E3SM S2D hindcast data.

This module mirrors the overall workflow style of the CESM/SMYLE
data_access utility, but is adapted to E3SM directory-driven data
organization, where data are stored under top-level initialization
directories and ensemble subdirectories.

Expected directory structure
----------------------------
<data_dir>/
  <case_prefix>_<init_tag>/
    EN00/
      post/atm/180x360_aave/ts/monthly/2yr/{FIELD}_{start_yyyymm}_{end_yyyymm}.nc
    EN01/
      post/atm/180x360_aave/ts/monthly/2yr/{FIELD}_{start_yyyymm}_{end_yyyymm}.nc
    ...

Example top-level case directory
--------------------------------
WCYCL20TR_ne30pg2_r05_IcoswISC30E3r5_JRA55_FOSIRL_1980050100

Example file
------------
TREFHT_198005_198204.nc

Notes
-----
1. Monthly timestamp convention
   E3SM monthly means are often written with timestamps at the beginning
   of the following month. For example, for a simulation initialized on

       1980-05-01-00000

   the first monthly mean may be stored with timestamp

       1980-06-01-00000

   even though it represents the mean over May 1980.

   This module accounts for that convention by shifting timestamps back
   by one month and placing them on the 15th of the represented month.

2. Calendar convention
   E3SM commonly uses a noleap (365_day) calendar. This module preserves
   the native E3SM calendar and typically returns cftime.DatetimeNoLeap
   coordinates. Calendar harmonization with Gregorian observational
   datasets should be handled downstream, depending on the analysis.

3. Recommended workflow
   For initialized hindcast analysis, lead-based alignment is usually
   safer than relying on exact absolute timestamps when comparing with
   observational datasets.

Typical use
-----------
from esp_lab import data_access_e3sm as data_access

field = "TREFHT"
data_dir = "/pscratch/sd/z/zhan391/e3sm_project/E3SMv3_S2D"
case_prefix = "WCYCL20TR_ne30pg2_r05_IcoswISC30E3r5_JRA55_FOSIRL"
members = [f"EN{i:02d}" for i in range(10)]
init_tags = data_access.build_init_tags(np.arange(1980, 2015), [5, 11])

ds = data_access.get_monthly_data(
    data_dir=data_dir,
    case_prefix=case_prefix,
    members=members,
    init_tags=init_tags,
    field=field,
    nlead=24,
    realm="atm",
    grid="180x360_aave",
    freq="monthly",
    ts_split="2yr",
)
"""

import re
import warnings
from functools import partial
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

import cftime
import numpy as np
import xarray as xr


def _validate_path_arg(name: str, value: str) -> None:
    """
    Validate that a path-related argument is a string.

    This mainly guards against accidental tuple creation from notebook code like:
        realm = "atm",
    """
    if not isinstance(value, str):
        raise TypeError(
            f"{name} must be a string, got {type(value).__name__}: {value!r}"
        )


def build_init_tags(
    years: Iterable[int],
    month: Union[int, Iterable[int]],
    init_day: int = 1,
    init_hour: int = 0,
) -> List[str]:
    """
    Build E3SM initialization tags like YYYYMMDDHH.

    Parameters
    ----------
    years : iterable of int
        Initialization years.
    month : int or iterable of int
        Initialization month(s), e.g. 5 or [5, 11].
    init_day : int, optional
        Initialization day, default 1.
    init_hour : int, optional
        Initialization hour, default 0.

    Returns
    -------
    init_tags : list of str
        List of initialization tags like '1980050100'.
    """
    if isinstance(month, int):
        months = [month]
    else:
        months = month

    init_tags = []
    for year in years:
        for month in months:
            init_tags.append(f"{year:04d}{month:02d}{init_day:02d}{init_hour:02d}")
    return init_tags


FILENAME_PATTERN = re.compile(
    r"^(?P<field>.+)_(?P<start_yyyymm>\d{6})_(?P<end_yyyymm>\d{6})\.nc$"
)


def parse_ts_filename(filename: str) -> Dict[str, str]:
    """
    Parse a post-processed E3SM filename of the form:

        {FIELD}_{start_yyyymm}_{end_yyyymm}.nc

    Parameters
    ----------
    filename : str
        Filename or full path.

    Returns
    -------
    info : dict
        Dictionary with keys:
            - field
            - start_yyyymm
            - end_yyyymm

    Raises
    ------
    ValueError
        If filename does not match the expected format.
    """
    fname = Path(filename).name
    match = FILENAME_PATTERN.match(fname)
    if match is None:
        raise ValueError(f"Unrecognized filename format: {filename}")
    return match.groupdict()


def expected_yyyymm_from_init_tag(init_tag: str, nlead: int) -> Tuple[str, str]:
    """
    Compute expected start and end YYYYMM strings from an init tag and nlead.

    This refers to the represented monthly means, not the raw file timestamps.
    For example, if init_tag='1980050100' and nlead=24, the expected file range is

        198005 -> 198204

    even if the first raw timestamp in the NetCDF file is 1980-06-01.

    Parameters
    ----------
    init_tag : str
        Initialization tag like '1980050100'.
    nlead : int
        Number of lead months.

    Returns
    -------
    start_yyyymm : str
        Start YYYYMM string.
    end_yyyymm : str
        End YYYYMM string.
    """
    year = int(init_tag[:4])
    month = int(init_tag[4:6])

    start_yyyymm = f"{year:04d}{month:02d}"

    end_index = month - 1 + (nlead - 1)
    end_year = year + end_index // 12
    end_month = end_index % 12 + 1
    end_yyyymm = f"{end_year:04d}{end_month:02d}"

    return start_yyyymm, end_yyyymm


def time_set_midmonth(ds: xr.Dataset, time_name: str) -> xr.Dataset:
    """
    Return a copy of ds with time coordinate shifted to the represented month.

    E3SM monthly output is often timestamped at the beginning of the following
    month. For example:

        1980-06-01 -> represents May 1980 monthly mean

    This function shifts each timestamp back by one month and sets the day
    to the 15th, so that:

        1980-06-01 -> 1980-05-15
        1980-07-01 -> 1980-06-15

    Notes
    -----
    - This function preserves the noleap calendar convention used by E3SM.
    - Returned timestamps are cftime.DatetimeNoLeap.

    Parameters
    ----------
    ds : xarray.Dataset
        Input dataset.
    time_name : str
        Name of time coordinate.

    Returns
    -------
    ds : xarray.Dataset
        Dataset with adjusted time coordinate.
    """
    ds = ds.copy()

    year = ds[time_name].dt.year
    month = ds[time_name].dt.month

    year = xr.where(month == 1, year - 1, year)
    month = xr.where(month == 1, 12, month - 1)

    nmonths = len(month)
    newtime = [
        cftime.DatetimeNoLeap(int(year[i]), int(month[i]), 15)
        for i in range(nmonths)
    ]
    ds[time_name] = newtime

    return ds


def preprocessor_monthly(ds0: xr.Dataset, nlead: int, field: str) -> xr.Dataset:
    """
    Standard E3SM monthly preprocessor.

    This function:
    - shifts time to the represented month midpoint
    - selects the first nlead months
    - defines a lead coordinate
    - preserves the requested field and time coordinate

    Notes
    -----
    - E3SM monthly means are assumed to use the end-of-period convention,
      where the raw timestamp is written at the beginning of the next month.
    - This function preserves the native E3SM noleap calendar.
    - Calendar harmonization with Gregorian observational datasets should
      be handled downstream.

    Parameters
    ----------
    ds0 : xarray.Dataset
        Input dataset for one file.
    nlead : int
        Number of lead months to retain.
    field : str
        Requested field name.

    Returns
    -------
    d0 : xarray.Dataset
        Preprocessed dataset with dimensions using L instead of time.
    """
    ds0 = time_set_midmonth(ds0, 'time')
    d0 = ds0[field].isel(time=slice(0, nlead))
    
    if 'lon' in ds0.coords and 'lat' in ds0.coords:
        d0 = d0.assign_coords({"lon": ds0.lon, "lat": ds0.lat})
        
    d0 = d0.assign_coords(L=("time", np.arange(d0.sizes["time"]) + 1))
    d0 = d0.swap_dims({"time": "L"})
    d0 = d0.to_dataset(name=field)
    d0 = d0.reset_coords(["time"])
    d0["time"] = d0.time.expand_dims("Y")
    d0 = d0.chunk({"L": -1})
    
    return d0

# Backward-compatible alias
preprocessor = preprocessor_monthly


def file_dict(
    data_dir: str,
    case_prefix: str,
    member: str,
    field: str,
    realm: str = "atm",
    grid: str = "180x360_aave",
    freq: str = "monthly",
    ts_split: str = "2yr",
    verify_field_name: bool = True,
) -> Dict[str, str]:
    """
    Return a dictionary of filepaths keyed by initialization tag for one member.

    Expected filename pattern:
        {FIELD}_{start_yyyymm}_{end_yyyymm}.nc

    Parameters
    ----------
    data_dir : str
        Base directory containing E3SM S2D cases.
    case_prefix : str
        Common prefix of case directories, excluding init tag.
    member : str
        Ensemble member, e.g. 'EN00'.
    field : str
        Variable name to search for, e.g. 'TREFHT'.
    realm : str, optional
        Realm name under post/, default 'atm'.
    grid : str, optional
        Post-processed grid name, default '180x360_aave'.
    freq : str, optional
        Frequency directory, default 'monthly'.
    ts_split : str, optional
        Post-processing split directory, e.g. '1yr', '2yr', '5yr'.
    verify_field_name : bool, optional
        If True, verify parsed field name exactly matches `field`.

        - True (recommended):
            Prevents accidental mismatches such as loading TREFHTMX when
            TREFHT was requested.

        - False:
            Accepts any file matching the filename glob pattern. Faster but less safe.

    Returns
    -------
    filepaths : dict
        Dictionary keyed by init_tag with filepath values.

    Raises
    ------
    ValueError
        If multiple matching files are found for one init/member/field.
    """
    _validate_path_arg("data_dir", data_dir)
    _validate_path_arg("case_prefix", case_prefix)
    _validate_path_arg("member", member)
    _validate_path_arg("field", field)
    _validate_path_arg("realm", realm)
    _validate_path_arg("grid", grid)
    _validate_path_arg("freq", freq)
    _validate_path_arg("ts_split", ts_split)

    data_path = Path(data_dir)
    case_dirs = sorted(data_path.glob(f"{case_prefix}_*"))
    filepaths: Dict[str, str] = {}

    for case_dir in case_dirs:
        init_tag = case_dir.name.split("_")[-1]
        matches = sorted(
            (case_dir / member / "post" / realm / grid / "ts" / freq / ts_split).glob(
                f"{field}_*.nc"
            )
        )
        if not matches:
            continue

        valid_matches = []
        for path in matches:
            try:
                info = parse_ts_filename(str(path))
            except ValueError:
                continue

            if verify_field_name and info["field"] != field:
                continue

            valid_matches.append(str(path))

        if len(valid_matches) == 1:
            filepaths[init_tag] = valid_matches[0]
        elif len(valid_matches) > 1:
            raise ValueError(
                f"Multiple matching files found for field={field}, "
                f"init={init_tag}, member={member}: {valid_matches}"
            )

    return filepaths


def nested_file_list_by_init(
    data_dir: str,
    case_prefix: str,
    members: List[str],
    init_tags: List[str],
    field: str,
    realm: str = "atm",
    grid: str = "180x360_aave",
    freq: str = "monthly",
    ts_split: str = "2yr",
    require_all_members: bool = True,
    verify_field_name: bool = True,
    verify_coverage: bool = False,
    nlead: Optional[int] = None,
) -> Tuple[List[List[str]], List[str]]:
    """
    Retrieve a nested list of files for requested init tags and members.

    Parameters
    ----------
    data_dir : str
        Base directory containing E3SM S2D cases.
    case_prefix : str
        Common prefix of case directories, excluding init tag.
    members : list of str
        Ensemble members, e.g. ['EN00', 'EN01', ...].
    init_tags : list of str
        Initialization tags like ['1980050100', '1980110100', ...].
    field : str
        Variable name to search for.
    realm : str, optional
        Realm name under post/, default 'atm'.
    grid : str, optional
        Post-processed grid name, default '180x360_aave'.
    freq : str, optional
        Frequency directory, default 'monthly'.
    ts_split : str, optional
        Post-processing split directory, e.g. '1yr', '2yr', '5yr'.
    require_all_members : bool, optional
        Controls whether all ensemble members must be present for an init.

        - True (recommended for production):
            Only keep init tags where all requested members exist.
            This ensures a consistent (init, member, ...) structure and avoids
            member misalignment across initializations.

        - False:
            Keep init tags even if some members are missing.
            Useful for quick inspection of incomplete datasets, but downstream
            code must be careful about consistency assumptions.

    verify_field_name : bool, optional
        If True, verify parsed field name exactly matches `field`.

    verify_coverage : bool, optional
        If True, verify that filename date coverage matches init_tag and nlead.

        Example:
            init_tag = '1980050100'
            nlead    = 24

        Expected represented range:
            198005 -> 198204

        Notes
        -----
        This checks the represented monthly coverage encoded in the filename,
        not the raw file timestamps. Raw monthly timestamps in E3SM may begin
        one month later, e.g. 1980-06-01 for the May 1980 mean.

        - True (recommended for strict reproducibility):
            Enforce exact coverage match.

        - False:
            Allow mismatched longer files and let the preprocessor slice the
            first nlead months.

    nlead : int, optional
        Number of lead months. Required if verify_coverage=True.

    Returns
    -------
    nested_files : list of list of str
        Nested list ordered as [init][member].
    valid_inits : list of str
        Initialization tags retained in output.

    Raises
    ------
    ValueError
        If verify_coverage=True and nlead is not provided.
    """
    if verify_coverage and nlead is None:
        raise ValueError("nlead must be provided when verify_coverage=True")

    member_file_dicts = {
        member: file_dict(
            data_dir=data_dir,
            case_prefix=case_prefix,
            member=member,
            field=field,
            realm=realm,
            grid=grid,
            freq=freq,
            ts_split=ts_split,
            verify_field_name=verify_field_name,
        )
        for member in members
    }

    nested_files: List[List[str]] = []
    valid_inits: List[str] = []

    for init_tag in init_tags:
        files_this_init: List[str] = []

        for member in members:
            member_files = member_file_dicts[member]
            if init_tag not in member_files:
                continue

            path = member_files[init_tag]

            if verify_coverage:
                info = parse_ts_filename(path)
                exp_start, exp_end = expected_yyyymm_from_init_tag(init_tag, nlead)
                if info["start_yyyymm"] != exp_start or info["end_yyyymm"] != exp_end:
                    continue

            files_this_init.append(path)

        if require_all_members:
            if len(files_this_init) == len(members):
                nested_files.append(files_this_init)
                valid_inits.append(init_tag)
        else:
            if len(files_this_init) > 0:
                nested_files.append(files_this_init)
                valid_inits.append(init_tag)

    return nested_files, valid_inits


def get_monthly_data(
    data_dir: str,
    case_prefix: str,
    members: List[str],
    init_tags: List[str],
    field: str,
    nlead: int,
    preproc: Union[str, Callable] = "default",
    chunks: Optional[Dict[str, int]] = None,
    realm: str = "atm",
    grid: str = "180x360_aave",
    freq: str = "monthly",
    ts_split: str = "2yr",
    require_all_members: bool = True,
    verify_field_name: bool = True,
    verify_coverage: bool = False,
    engine: str = "netcdf4",
) -> xr.Dataset:
    """
    Return a dask-backed xarray dataset arranged as (init, lead, member, ...).

    Parameters
    ----------
    data_dir : str
        Base directory containing E3SM S2D cases.
    case_prefix : str
        Common prefix of case directories, excluding init tag.
    members : list of str
        Ensemble members, e.g. ['EN00', 'EN01', ...].
    init_tags : list of str
        Initialization tags like ['1980050100', '1980110100', ...].
    field : str
        Variable name to be loaded.
    nlead : int
        Number of lead months to retain.
    preproc : {"default"} or callable, optional
        - "default": use built-in monthly E3SM preprocessor
        - callable: custom preprocessing function with signature
          preproc(ds0, nlead, field)
    chunks : dict, optional
        Chunk settings for open_mfdataset.
    realm : str, optional
        Realm name under post/, default 'atm'.
    grid : str, optional
        Post-processed grid name, default '180x360_aave'.
    freq : str, optional
        Frequency directory, default 'monthly'.
    ts_split : str, optional
        Post-processing split directory, e.g. '1yr', '2yr', '5yr'.
    require_all_members : bool, optional
        See nested_file_list_by_init().
    verify_field_name : bool, optional
        See nested_file_list_by_init().
    verify_coverage : bool, optional
        See nested_file_list_by_init().
    engine : str, optional
        Backend to use for xarray (default is "netcdf4").

    Returns
    -------
    ds : xarray.Dataset
        Dataset arranged as (init, lead, member, ...).

    Raises
    ------
    ValueError
        If no matching files are found.
    TypeError
        If `preproc` is neither "default" nor a callable.
    """
    _validate_path_arg("data_dir", data_dir)
    _validate_path_arg("case_prefix", case_prefix)
    _validate_path_arg("realm", realm)
    _validate_path_arg("grid", grid)
    _validate_path_arg("freq", freq)
    _validate_path_arg("ts_split", ts_split)
    _validate_path_arg("field", field)

    if chunks is None:
        chunks = {}

    if preproc == "default":
        preproc_func = preprocessor_monthly
    elif callable(preproc):
        preproc_func = preproc
    else:
        raise TypeError(
            "preproc must be 'default' or a callable with signature "
            "preproc(ds0, nlead, field)"
        )

    file_list, valid_inits = nested_file_list_by_init(
        data_dir=data_dir,
        case_prefix=case_prefix,
        members=members,
        init_tags=init_tags,
        field=field,
        realm=realm,
        grid=grid,
        freq=freq,
        ts_split=ts_split,
        require_all_members=require_all_members,
        verify_field_name=verify_field_name,
        verify_coverage=verify_coverage,
        nlead=nlead,
    )

    if not file_list:
        raise ValueError(
            f"No files found for field={field}, case_prefix={case_prefix}, "
            f"realm={realm}, grid={grid}, freq={freq}, ts_split={ts_split}"
        )

    # Check for bad data by doing a quick open of each file before open_mfdataset
    for init_files in file_list:
        _sub_list = init_files if isinstance(init_files, list) else [init_files]
        for f in _sub_list:
            try:
                # Open with parallel=False context explicitly inside standard open
                with xr.open_dataset(f, engine=engine) as _temp:
                    pass
            except Exception as e:
                warnings.warn(f"Warning: Bad data or unreadable file found: {f}. Error: {e}")

    try:
        ds = xr.open_mfdataset(
            file_list,
            combine="nested",
            concat_dim=["Y", "M"],
            parallel=True,
            data_vars=[field],
            coords="minimal",
            compat="override",
            engine=engine,
            preprocess=partial(preproc_func, nlead=nlead, field=field),
            chunks=chunks,
        )
    except OSError as e:
        if "-51" in str(e) or "Unknown file format" in str(e):
            warnings.warn("NetCDF HDF5 read collision detected with parallel=True. Retrying with parallel=False...")
            ds = xr.open_mfdataset(
                file_list,
                combine="nested",
                concat_dim=["Y", "M"],
                parallel=False,
                data_vars=[field],
                coords="minimal",
                compat="override",
                engine=engine,
                preprocess=partial(preproc_func, nlead=nlead, field=field),
                chunks=chunks,
            )
        else:
            raise

    ds = ds.assign_coords(Y=("Y", valid_inits))
    ds = ds.assign_coords(M=("M", members[: ds.sizes["M"]]))
    ds = ds.transpose("Y", "L", "M", ...)

    return ds