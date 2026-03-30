from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

import cftime
import xarray as xr


DEFAULT_OBS_DIR = "/global/cfs/cdirs/e3sm/e3sm_diags/obs_for_e3sm_diags/time-series/"


# Default mapping from common E3SM model variable names to CMIP6 CMOR names
# used by the observational archive.
#
# Notes
# -----
# - Observational files under obs_for_e3sm_diags/time-series generally follow
#   CMIP6 CMOR naming conventions, e.g. tas, pr, psl, ua, va.
# - Some flux variables may require definition/sign checks depending on the
#   exact diagnostic use case.
DEFAULT_E3SM_TO_CMOR = {
    "TREFHT": "tas",
    "TS": "ts",
    "PRECT": "pr",
    "PSL": "psl",
    "PS": "ps",
    "TMQ": "prw",
    "U": "ua",
    "V": "va",
    "UBOT": "uas",
    "VBOT": "vas",
    "Q": "hus",
    "T": "ta",
    "OMEGA": "wap",
    "Z3": "zg",
    "LHFLX": "hfls",
    "SHFLX": "hfss",
    "FLDS": "rlds",
    "FLNS": "rlus",
    "FLUT": "rlut",
    "FLUTC": "rlutcs",
    "FSDS": "rsds",
    "FSNS": "rsus",
    "FSNTOA": "rsut",
    "SOLIN": "rsdt",
    "PRECL": "prl",
    "PRECC": "prc",
    "PRECSL": "prsn",
}


def _validate_path_arg(name: str, value: str) -> None:
    """
    Validate that a path-related argument is a string.

    This mainly guards against accidental tuple creation from notebook code like:
        product = "HadISST",
    """
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string, got {type(value).__name__}: {value!r}")


def resolve_obs_dir(obs_dir: Optional[str] = None) -> Path:
    """
    Resolve the observation directory to a valid Path object.
    """
    if obs_dir is None:
        obs_dir = DEFAULT_OBS_DIR

    _validate_path_arg("obs_dir", obs_dir)
    obs_path = Path(obs_dir).expanduser().resolve()

    if not obs_path.exists():
        raise FileNotFoundError(f"Observation directory does not exist: {obs_path}")

    return obs_path


def list_products(obs_dir: Optional[str] = None) -> List[str]:
    """
    List available observational product subdirectories.

    Parameters
    ----------
    obs_dir : str, optional
        Base observation directory. If None, use DEFAULT_OBS_DIR.

    Returns
    -------
    products : list of str
        Sorted list of available product names.
    """
    obs_path = resolve_obs_dir(obs_dir)
    return sorted([p.name for p in obs_path.iterdir() if p.is_dir()])


def resolve_obs_field(
    field: Optional[str],
    use_cmor_map: bool = True,
    field_map: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """
    Resolve an input field name to the CMOR variable name used by the
    observational archive.

    Parameters
    ----------
    field : str or None
        Input field name. This may be either:
        - a native E3SM model variable name, e.g. 'TREFHT'
        - a CMIP6 CMOR variable name, e.g. 'tas'
    use_cmor_map : bool, optional
        If True, map E3SM variable names to CMOR names when possible.
    field_map : dict or None, optional
        Custom mapping dictionary. If None, use DEFAULT_E3SM_TO_CMOR.

    Returns
    -------
    field_out : str or None
        Resolved CMOR-compatible field name, or None if field is None.
    """
    if field is None:
        return None

    if not isinstance(field, str):
        raise TypeError(f"field must be a string or None, got {type(field).__name__}: {field!r}")

    if not use_cmor_map:
        return field

    mapping = DEFAULT_E3SM_TO_CMOR if field_map is None else field_map
    return mapping.get(field, field)


def parse_obs_filename(filename: str) -> Dict[str, str]:
    """
    Parse an observational filename of the form:

        {field}_{start_yyyymm}_{end_yyyymm}.nc

    where `field` follows CMIP6 CMOR naming conventions.
    """
    fname = Path(filename).name

    if not fname.endswith(".nc"):
        raise ValueError(f"Not a netCDF filename: {filename}")

    stem = fname[:-3]
    parts = stem.rsplit("_", 2)

    if len(parts) != 3:
        raise ValueError(f"Unrecognized observational filename format: {filename}")

    field, start_yyyymm, end_yyyymm = parts

    if not (start_yyyymm.isdigit() and len(start_yyyymm) == 6):
        raise ValueError(f"Invalid start YYYYMM in filename: {filename}")
    if not (end_yyyymm.isdigit() and len(end_yyyymm) == 6):
        raise ValueError(f"Invalid end YYYYMM in filename: {filename}")

    return {
        "field": field,
        "start_yyyymm": start_yyyymm,
        "end_yyyymm": end_yyyymm,
    }


def standardize_latlon(ds: xr.Dataset) -> xr.Dataset:
    """
    Standardize latitude/longitude coordinate names to lat/lon and
    enforce monotonic coordinate ordering.

    Notes
    -----
    - Renames latitude -> lat and longitude -> lon when needed.
    - Sorts lat and lon if present.
    - Converts longitude to [0, 360) if negative longitudes are detected.
    """
    rename_dict = {}

    if "latitude" in ds.dims or "latitude" in ds.coords:
        rename_dict["latitude"] = "lat"
    if "longitude" in ds.dims or "longitude" in ds.coords:
        rename_dict["longitude"] = "lon"

    if rename_dict:
        ds = ds.rename(rename_dict)

    if "lat" in ds.coords:
        ds = ds.sortby("lat")

    if "lon" in ds.coords:
        try:
            if (ds["lon"] < 0).any():
                ds = ds.assign_coords(lon=(ds["lon"] % 360))
        except Exception:
            pass
        ds = ds.sortby("lon")

    return ds


def _build_monthly_noleap_time(base_year: int, ntime: int):
    """
    Construct monthly cftime.DatetimeNoLeap timestamps at mid-month.

    Parameters
    ----------
    base_year : int
        Starting year corresponding to the first monthly record.
    ntime : int
        Number of time steps. Must be divisible by 12.

    Returns
    -------
    time_vals : list of cftime.DatetimeNoLeap
        Mid-month monthly noleap timestamps.
    """
    if ntime % 12 != 0:
        raise ValueError(
            f"time dimension size ({ntime}) is not divisible by 12; "
            "cannot safely build monthly noleap timestamps."
        )

    nyears = ntime // 12
    return [
        cftime.DatetimeNoLeap(base_year + y, m + 1, 15)
        for y in range(nyears)
        for m in range(12)
    ]


def transform_to_mid_month(ds: xr.Dataset, time_name: str = "time") -> xr.Dataset:
    """
    Safely force time values to the 15th of the month.
    
    Notes
    -----
    Some datasets store monthly averages with a timestamp corresponding 
    to the FIRST day of the FOLLOWING month (e.g. 1980-02-01 00:00:00 
    for Jan 1980). A naïve shift to `day=15` for this record results 
    in mid-Feb instead of mid-Jan.
    
    This function dynamically steps backward a few hours to ensure
    it anchors to the correct month before forcing to day 15.
    """
    if time_name not in ds.coords:
        return ds

    try:
        from datetime import timedelta
        
        # We try to extract the first element to ensure we have scalar time objects.
        # Fall back if it's already an index that doesn't iterate well.
        times = ds[time_name].values
        if not hasattr(times[0], 'year'):
            return ds

        new_times = []
        for t in times:
            # If the timestamp is right on the 1st of the month (often 00:00:00), 
            # we subtract 12 hours. This pushes it into the last day of the previous
            # month (the ACTUAL month the temporal average usually represents).
            if t.day == 1:
                t = t - timedelta(hours=12)
                
            new_times.append(cftime.DatetimeNoLeap(t.year, t.month, 15))

        ds = ds.assign_coords({time_name: new_times})
    except Exception:
        pass

    return ds

def ensure_time_coordinate(
    ds: xr.Dataset,
    *,
    decode_times: bool = True,
    force_noleap: bool = False,
    base_year: Optional[int] = None,
    time_name: str = "time",
) -> xr.Dataset:
    """
    Robustly ensure dataset has a usable time coordinate.

    Strategy
    --------
    1. If time is already decoded, keep it.
    2. If time is numeric with CF metadata, try xr.decode_cf().
    3. If requested, convert decoded time to noleap calendar.
    4. If still unresolved and base_year is provided, rebuild as monthly
       DatetimeNoLeap timestamps.
    """
    if time_name not in ds.coords:
        return ds

    out = ds

    # Case 1: already decoded
    try:
        if hasattr(out[time_name], "dt"):
            if force_noleap:
                try:
                    out = out.convert_calendar("noleap")
                except Exception:
                    pass
            return transform_to_mid_month(out, time_name=time_name)
    except Exception:
        pass

    # Case 2: try CF decoding from units/calendar metadata
    if decode_times:
        try:
            out = xr.decode_cf(out)
            if hasattr(out[time_name], "dt"):
                if force_noleap:
                    try:
                        out = out.convert_calendar("noleap")
                    except Exception:
                        pass
                return transform_to_mid_month(out, time_name=time_name)
        except Exception:
            pass

    # Case 3: fallback manual reconstruction
    if base_year is not None:
        ntime = out.sizes[time_name]
        out = out.copy()
        # _build_monthly_noleap_time already generates mid-month (day=15)
        out = out.assign_coords(
            {time_name: _build_monthly_noleap_time(base_year, ntime)}
        )
        return out

    raise ValueError(
        f"Could not decode time coordinate '{time_name}'. "
        "Provide a valid base_year for manual monthly reconstruction."
    )


def crop_time(
    ds: xr.Dataset,
    start_year: Optional[str] = None,
    end_year: Optional[str] = None,
) -> xr.Dataset:
    """
    Crop dataset by time if a time coordinate exists.
    """
    if "time" not in ds.coords:
        return ds

    if start_year is None and end_year is None:
        return ds

    return ds.sel(time=slice(start_year, end_year))


def preprocessor_monthly(
    ds: xr.Dataset,
    field: Optional[str] = None,
    start_year: Optional[str] = None,
    end_year: Optional[str] = None,
    harmonize_time: bool = True,
    calendar: str = "noleap",
    decode_times: bool = True,
    base_year: Optional[int] = None,
) -> xr.Dataset:
    """
    Standard preprocessing for observational monthly time-series data.

    This function:
    - standardizes lat/lon names
    - robustly ensures a usable time coordinate
    - optionally harmonizes to noleap calendar
    - crops to the requested time range
    - optionally retains only the requested field
    """
    ds = standardize_latlon(ds)

    ds = ensure_time_coordinate(
        ds,
        decode_times=decode_times,
        force_noleap=harmonize_time and calendar == "noleap",
        base_year=base_year,
        time_name="time",
    )

    ds = crop_time(ds, start_year=start_year, end_year=end_year)

    if field is not None:
        if field not in ds.data_vars:
            raise ValueError(
                f"Field {field!r} not found in dataset. "
                f"Available variables: {list(ds.data_vars)}"
            )
        ds = ds[[field]]

    return ds


def find_obs_file(
    obs_dir: Optional[str] = None,
    product: Optional[str] = None,
    field: Optional[str] = None,
    filename: Optional[str] = None,
) -> str:
    """
    Find an observational file inside a product subdirectory.

    Parameters
    ----------
    obs_dir : str, optional
        Base observation directory. If None, use DEFAULT_OBS_DIR.
    product : str, optional
        Product subdirectory name.
    field : str, optional
        CMIP6 CMOR variable name used to identify the file, e.g.
        'tas', 'pr', 'psl', 'ua', 'va'.
    filename : str, optional
        Exact filename to load.

    Returns
    -------
    filepath : str
        Path to the matched file.
    """
    obs_root = resolve_obs_dir(obs_dir)

    if product is None:
        raise ValueError("product must be provided")

    _validate_path_arg("product", product)

    obs_path = obs_root / product
    if not obs_path.exists():
        raise FileNotFoundError(f"Product directory does not exist: {obs_path}")

    if filename is not None:
        _validate_path_arg("filename", filename)
        path = obs_path / filename
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return str(path)

    matches = sorted(obs_path.glob("*.nc"))

    if field is not None:
        _validate_path_arg("field", field)
        field_lower = field.lower()

        parsed_matches = []
        for p in matches:
            try:
                info = parse_obs_filename(p.name)
            except ValueError:
                continue
            if info["field"].lower() == field_lower:
                parsed_matches.append(p)

        matches = parsed_matches

    if len(matches) == 0:
        raise FileNotFoundError(
            f"No matching files found in {obs_path} "
            f"for field={field!r}, filename={filename!r}"
        )

    if len(matches) > 1:
        raise ValueError(
            f"Multiple matching files found in {obs_path}: "
            f"{[m.name for m in matches]}. "
            "Please specify filename explicitly."
        )

    return str(matches[0])


def get_monthly_data(
    obs_dir: Optional[str] = None,
    product: Optional[str] = None,
    field: Optional[str] = None,
    filename: Optional[str] = None,
    chunks: Optional[Dict[str, int]] = None,
    preproc: Union[str, Callable] = "default",
    start_year: Optional[str] = None,
    end_year: Optional[str] = None,
    harmonize_time: bool = True,
    calendar: str = "noleap",
    decode_times: bool = True,
    base_year: Optional[int] = None,
    use_cmor_map: bool = True,
    field_map: Optional[Dict[str, str]] = None,
    verbose: bool = False,
) -> xr.Dataset:
    """
    Load a preprocessed observational monthly time-series dataset.

    Parameters
    ----------
    obs_dir : str, optional
        Base observation directory. If None, use DEFAULT_OBS_DIR.
    product : str, optional
        Product subdirectory name.
    field : str, optional
        Requested variable name. This may be either:
        - an E3SM native variable name, e.g. 'TREFHT'
        - a CMIP6 CMOR variable name, e.g. 'tas'

        If `use_cmor_map=True`, known E3SM names are mapped internally to
        CMOR variable names for file lookup and variable selection.
    filename : str, optional
        Exact filename to load.
    chunks : dict, optional
        Chunk settings for xarray open_dataset.
    preproc : {"default"} or callable, optional
        - "default": use built-in monthly preprocessor
        - callable: custom preprocessing function with signature
          preproc(ds, field=None, start_year=None, end_year=None, **kwargs)
    start_year : str, optional
        Start year for cropping.
    end_year : str, optional
        End year for cropping.
    harmonize_time : bool, optional
        If True, attempt to harmonize to the requested calendar.
    calendar : str, optional
        Target calendar for time harmonization.
    decode_times : bool, optional
        Passed to xarray.open_dataset and also used in robust time handling.
    base_year : int, optional
        Fallback base year for manual monthly noleap time reconstruction when
        time cannot be decoded automatically. Use only for raw datasets that
        lack a usable decoded time coordinate.
    use_cmor_map : bool, optional
        If True, resolve native model field names to CMOR names.
    field_map : dict or None, optional
        Custom field mapping dictionary. If None, use DEFAULT_E3SM_TO_CMOR.
    verbose : bool, optional
        If True, print the filepath being loaded and any field mapping used.

    Returns
    -------
    ds : xr.Dataset
        Loaded and preprocessed observational dataset.
    """
    field_resolved = resolve_obs_field(
        field,
        use_cmor_map=use_cmor_map,
        field_map=field_map,
    )

    if verbose and field is not None and field_resolved != field:
        print(f"[OBS] Mapping field '{field}' -> '{field_resolved}'")

    filepath = find_obs_file(
        obs_dir=obs_dir,
        product=product,
        field=field_resolved,
        filename=filename,
    )

    if chunks is None:
        chunks = {}

    if verbose:
        print(f"[OBS] Loading: {filepath}")

    ds = xr.open_dataset(filepath, chunks=chunks, decode_times=decode_times)

    if preproc == "default":
        return preprocessor_monthly(
            ds,
            field=field_resolved,
            start_year=start_year,
            end_year=end_year,
            harmonize_time=harmonize_time,
            calendar=calendar,
            decode_times=decode_times,
            base_year=base_year,
        )

    if callable(preproc):
        return preproc(
            ds,
            field=field_resolved,
            start_year=start_year,
            end_year=end_year,
            harmonize_time=harmonize_time,
            calendar=calendar,
            decode_times=decode_times,
            base_year=base_year,
        )

    raise TypeError(
        "preproc must be 'default' or a callable with signature "
        "preproc(ds, field=None, start_year=None, end_year=None, **kwargs)"
    )


def merge_obs(primary: xr.DataArray, secondary: xr.DataArray) -> xr.DataArray:
    """
    Fill missing values in the primary observational field using values
    from the secondary field.
    """
    if not isinstance(primary, xr.DataArray) or not isinstance(secondary, xr.DataArray):
        raise TypeError("Inputs to merge_obs must be xarray.DataArray instances")

    if "time" in primary.dims and "time" in secondary.dims:
        if primary.sizes.get("time") != secondary.sizes.get("time"):
            raise ValueError(
                f"Cannot merge! Time sizes do not match. "
                f"primary ({primary.name}) time length: {primary.sizes.get('time')}, "
                f"secondary ({secondary.name}) time length: {secondary.sizes.get('time')}"
            )

    return primary.fillna(secondary)
    return primary.fillna(secondary)


def mon_to_seas_obs(
    ds: xr.Dataset,
    var: str,
    time_name: str = "time",
    field_map: Optional[Dict[str, str]] = None,
) -> xr.DataArray:
    """
    Apply CRU-style centered 3-month rolling mean and return DataArray
    with optional renaming back to E3SM convention.

    Parameters
    ----------
    ds : xr.Dataset
        Input dataset.
    var : str
        Variable name in dataset (CMOR name, e.g. "tas").
    time_name : str, optional
        Time dimension name.
    field_map : dict, optional
        Mapping from E3SM -> CMOR (e.g., {"TREFHT": "tas"}).
        Used here to rename output back to E3SM naming.

    Returns
    -------
    xr.DataArray
    """
    if var not in ds:
        raise ValueError(f"{var!r} not found in dataset")

    da = (
        ds[var]
        .rolling({time_name: 3}, min_periods=3, center=True)
        .mean()
        .dropna(time_name, how="all")
    )

    # Reverse mapping: CMOR -> E3SM
    if field_map is not None:
        reverse_map = {v: k for k, v in field_map.items()}
        if var in reverse_map:
            da = da.rename(reverse_map[var])

    return da
