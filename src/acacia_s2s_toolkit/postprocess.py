# SPDX-FileCopyrightText: 2024 European Centre for Medium-Range Weather Forecasts (ECMWF)
# SPDX-License-Identifier: Apache-2.0

import xarray as xr
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import datetime
import json
import os,sys,glob
#import xesmf as xe
import pooch

import xarray_regrid


#this is for readthedocs to work correctly. These packages cannot be installed by pip, so one has to mock import them
autodoc_mock_imports = ["esmpy", "xesmf", "netCDF4"]

#this determines with functions will be publicly visible in the installed package
__all__=[
         "load_raw_data",
         "read_netcdf",
         "align_grid",
         "align_grid_sparse",
         "set_verbose",
         "_log",
         "aggregate",
         "align_to_nominal_forecast_time",
         "hcst_to_effective_lead_time",
         "fcst_to_effective_lead_time",
         "align_obs_to_model_time",
         "align_obs_to_product",
        ]

#######################################################################################

#
# helper functions
#
#######################################################################################

VERBOSE = True

def set_verbose(v):
    global VERBOSE
    VERBOSE = v
    print("verbosity is {}".format(v))


def _log(msg, force=False):
    if VERBOSE | force:
        print(msg)

def _check_grid_overlap(obs, hindcast, raise_if_missing=True, threshold=0.9):
    """
    Check spatial overlap between two lat/lon grids.

    Parameters
    ----------
    obs : xarray.DataArray or xarray.Dataset
        Observational grid containing `lat` and `lon`.
    hindcast : xarray.DataArray or xarray.Dataset
        Hindcast grid containing `lat` and `lon`.
    raise_if_missing : bool, default True
        If True, raises a ValueError if observations do not fully cover the hindcast/forecast grid.
    threshold : float, optional
        Minimum fraction of overlap relative to the smaller domain
        required to proceed (default: 0.9).

    Raises
    ------
    ValueError
        If overlap fraction is smaller than the threshold.
    """

    obs_lat_min = float(obs.latitude.min())
    obs_lat_max = float(obs.latitude.max())
    obs_lon_min = float(obs.longitude.min())
    obs_lon_max = float(obs.longitude.max())

    hc_lat_min = float(hindcast.latitude.min())
    hc_lat_max = float(hindcast.latitude.max())
    hc_lon_min = float(hindcast.longitude.min())
    hc_lon_max = float(hindcast.longitude.max())

    # intersection box
    lat_min = max(obs_lat_min, hc_lat_min)
    lat_max = min(obs_lat_max, hc_lat_max)
    lon_min = max(obs_lon_min, hc_lon_min)
    lon_max = min(obs_lon_max, hc_lon_max)

    if lat_min >= lat_max or lon_min >= lon_max:
        raise ValueError("Observation and hindcast grids do not overlap.")

    overlap_area = (lat_max - lat_min) * (lon_max - lon_min)

    obs_area = (obs_lat_max - obs_lat_min) * (obs_lon_max - obs_lon_min)
    hc_area  = (hc_lat_max - hc_lat_min) * (hc_lon_max - hc_lon_min)

    smaller_area = min(obs_area, hc_area)
    overlap_fraction = overlap_area / smaller_area

    if overlap_fraction < threshold:
        if raise_if_missing:
            raise ValueError(
                "Grid overlap too small: {} ".format(np.round(overlap_fraction,2)),
                "f(threshold {threshold:.0%})"
            )
        else:
            _log("Grid overlap : {} ".format(np.round(overlap_fraction,2)))
            return True
    else:
        return True


def _harmonize_coords(ds):
    """
    Harmonize coordinate names to standard names: lat, lon, time.

    Parameters
    ----------
    ds : xarray.Dataset or xarray.DataArray
        Dataset with potentially non-standard coordinate names.

    Returns
    -------
    xarray.Dataset or xarray.DataArray
        Dataset with coordinates renamed to `lat`, `lon`, `time`.

    Raises
    ------
    ValueError
        If latitude or longitude coordinate cannot be identified.
    """

    coord_map = {}

    lat_names = ["lat", "latitude", "Latitude", "nav_lat", "y"]
    lon_names = ["lon", "longitude", "Longitude", "nav_lon", "x"]
    time_names = ["time", "Time", "valid_time", "date"]

    for name in ds.coords:
        lname = name.lower()

        if name in lat_names or lname in lat_names:
            coord_map[name] = "latitude"

        elif name in lon_names or lname in lon_names:
            coord_map[name] = "longitude"

#        elif name in time_names or lname in time_names:
#            coord_map[name] = "time"

    if len(coord_map)>0:
        _log("Renaming coordinates: {}".format(coord_map))
    else:
        _log("Nothing to do")

    ds = ds.rename(coord_map)

    if "latitude" not in ds.coords:
        raise ValueError("Latitude coordinate not found.")
    if "longitude" not in ds.coords:
        raise ValueError("Longitude coordinate not found.")

    return ds





#######################################################################################
#
# main functions
#
#######################################################################################


def read_netcdf(file, variable, units=None):
    """
    Read a dataset and return the selected variable.

    The function opens a NetCDF file (or collection of files) using xarray,
    verifies that the requested variable exists, renames variables to the adopted convention (time,lat,lon) and checks that the time
    coordinate represents daily data.

    Parameters
    ----------
    file : str or list[str]
        Path or pattern pointing to NetCDF file(s). Passed to
        ``xarray.open_mfdataset``.
    variable : str
        Name of the variable to extract from the dataset.
    units : str, optional
        Units of the data, e.g. "mm" for daily precipitation totals. If given, it replaces
        the 'units' attribute of the file (files often come with missing or unusual units).
        The values are not converted: give the units the values are actually in.
        The units are carried through aggregation into the products, so for daily totals
        that are summed (e.g. weekly totals), give the units of an amount ("mm"), not of a
        rate ("mm/day").

    Returns
    -------
    xarray.DataArray
        DataArray containing the requested variable.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    OSError
        If the file cannot be opened.
    KeyError
        If the requested variable is not present in the dataset.
    ValueError
        If the dataset does not appear to contain daily data.
    """

    _log("\n" + "="*60)
    _log(" START: read_netcdf ".center(60, "="))
    _log("="*60 + "\n")

    _log("reading {} from {}".format(variable,file))


    # Check file existence (for simple paths; glob patterns handled by xarray)
    if isinstance(file, str) and not any(c in file for c in "*?[]"):
        if not os.path.exists(file):
            raise FileNotFoundError(f"data file not found: {file}")

    try:
        ds = xr.open_dataset(file)
        _log("success")
    except Exception as e:
        raise OSError("Unable to open dataset: {}".format(file)) from e

    _log("looking for {}".format(variable))

    if variable not in ds:
        raise KeyError("Variable '{}' not found in dataset.".format(variable))
    else:
        _log("found")

    # Make sure lat,lon and time are there, rename if necessary
    _log("Harmonizing coordinates...")
    ds = _harmonize_coords(ds)

    #and we return a data array rather than a dataset
    da = ds[variable]

    # units given by the user replace those of the file
    if units is not None:
        _log("setting units to '{}' (in file: '{}')".format(units, da.attrs.get("units", "")))
        da = da.assign_attrs(units=units)

    # just an idiot-check
    #_log("check if data are daily...")
    #if da.time.size > 2:
    #    dt = pd.Series(da.time.values).diff().dropna()

        # dominant timestep
    #    median_dt = dt.median()

     #   if median_dt < pd.Timedelta(hours=23):
    #        raise ValueError(
    #            "Dataset appears to be sub-daily (median timestep < 1 day)."
    #        )
    #    _log("daily with data time range: {} to {}".format(str(da.time.values[0]),str(da.time.values[-1])))
    #else:
    #    raise ValueError(
    #            "Dataset appears to only one time step. This is not what is expected."
    #        )

    _log("all done")
    _log("\n" + "="*60+"\n")

    return da




LAT_NAMES = ("lat", "latitude")
LON_NAMES = ("lon", "longitude")


def _spatial_names(da):
    """Names of the latitude and longitude dimensions of `da`."""
    lat = next((n for n in LAT_NAMES if n in da.dims), None)
    lon = next((n for n in LON_NAMES if n in da.dims), None)
    if lat is None or lon is None:
        raise ValueError(f"no lat/lon dimensions found in {da.dims}; expected one of "
                         f"{LAT_NAMES} and one of {LON_NAMES}")
    return lat, lon


def align_grid(finegrid, coarsegrid, direction="fine_to_coarse", method="conservative",
               raise_if_missing=True, threshold=0.9, nan_threshold=0.5):
    """
    Put two datasets on the same spatial grid, keeping all other dimensions.

    Parameters
    ----------
    finegrid : DataArray, high resolution, e.g. observations (time, lat, lon).
    coarsegrid : DataArray, low resolution, e.g. model data
        (valid_time, effective_lead_time, member, latitude, longitude).
    direction : "fine_to_coarse" (default) or "coarse_to_fine".
        "fine_to_coarse": finegrid is regridded to the coarse grid, conservatively
                          (area-weighted mean of the fine cells in each coarse cell).
        "coarse_to_fine": coarsegrid is interpolated bilinearly to the fine grid; fine cells
                          outside the area spanned by the coarse cell centres get the value
                          of the nearest coarse cell.
    method : "conservative" for fine_to_coarse, "bilinear" for coarse_to_fine.
    raise_if_missing, threshold : passed to _check_grid_overlap.
    nan_threshold : fine_to_coarse only. Largest fraction of NaN (by area) in a coarse cell
        for which a value is still computed from the valid part; above it the coarse cell is
        NaN. Same meaning as xESMF's na_thres (0.5 as in the previous version).

    Returns
    -------
    finealigned, coarsealigned : both on the chosen grid, with the dimension names of that
        grid. Cells without data in either dataset are NaN in both. Attributes are kept, and
        the regridding settings are added as attributes (regrid_direction, regrid_method,
        regrid_nan_threshold), so that they reach the products and can be repeated for
        new observations (align_obs_to_product).
    """
    _log(" align_grid ".center(60, "="))

    allowed = {"fine_to_coarse": ["conservative"], "coarse_to_fine": ["bilinear"]}
    if direction not in allowed:
        raise ValueError("direction must be 'fine_to_coarse' or 'coarse_to_fine'")
    if method not in allowed[direction]:
        raise ValueError(f"only {', '.join(allowed[direction])} available for {direction}")

    _check_grid_overlap(finegrid, coarsegrid, raise_if_missing, threshold)

    flat, flon = _spatial_names(finegrid)
    clat, clon = _spatial_names(coarsegrid)

    if direction == "fine_to_coarse":
        _log("Regridding finegrid -> coarsegrid (conservative)...")
        # xarray-regrid matches grids by coordinate name: use the coarse grid's names
        src = finegrid.rename({flat: clat, flon: clon})
        target = xr.Dataset(coords={clat: coarsegrid[clat], clon: coarsegrid[clon]})
        finealigned = src.regrid.conservative(target, latitude_coord=clat, time_dim=None,
                                              skipna=True, nan_threshold=nan_threshold)
        finealigned = finealigned.assign_attrs(finegrid.attrs)
        coarsealigned = coarsegrid
        lat, lon = clat, clon
    else:
        _log("Regridding coarsegrid -> finegrid (bilinear)...")
        src = coarsegrid.rename({clat: flat, clon: flon})
        target = xr.Dataset(coords={flat: finegrid[flat], flon: finegrid[flon]})
        lin = src.regrid.linear(target, time_dim=None)
        nearest = src.reindex({flat: finegrid[flat], flon: finegrid[flon]}, method="nearest")
        coarsealigned = lin.fillna(nearest).assign_attrs(coarsegrid.attrs)
        finealigned = finegrid
        lat, lon = flat, flon

    # common spatial mask: cells with data in both datasets (at any time / lead / member)
    def has_data(da):
        other = [d for d in da.dims if d not in (lat, lon)]
        return da.notnull().any(other) if other else da.notnull()

    mask = has_data(finealigned) & has_data(coarsealigned)
    finealigned = finealigned.where(mask)
    coarsealigned = coarsealigned.where(mask)

    # record the settings (where() keeps the attributes)
    settings = dict(regrid_direction=direction, regrid_method=method,
                    regrid_nan_threshold=float(nan_threshold))
    finealigned = finealigned.assign_attrs(settings)
    coarsealigned = coarsealigned.assign_attrs(settings)

    _log(f"done: {int(mask.sum())} of {mask.size} grid cells with data in both")
    _log("=" * 60)
    return finealigned, coarsealigned



def align_grid_xESMF(finegrid, coarsegrid, direction="fine_to_coarse", method="conservative", raise_if_missing=True, threshold=0.9):
    """
    Align two datasets spatially using xESMF, preserving time and member dimensions.

    Parameters
    ----------
    finegrid : xarray.DataArray
        High-resolution dataset with dimensions including `time`, `member`, `lat`, `lon`.
    coarsegrid : xarray.DataArray
        Low-resolution dataset with dimensions including `time`, `member`, `lat`, `lon`.
    direction : {"fine_to_coarse", "coarse_to_fine"}, default "fine_to_coarse"
        Direction of spatial alignment:
        - "fine_to_coarse": aggregate finegrid to coarsegrid (conservative regridding)
        - "coarse_to_fine": interpolate coarsegrid to finegrid (method specifies interpolation)
    method : str, optional
        Regridding method when interpolating coarse to fine. Ignored for fine to coarse.

    Returns
    -------
    finealigned : xarray.DataArray
        finegrid dataset aligned to the chosen spatial grid, dims (time, member, lat, lon)
    coarsealigned : xarray.DataArray
        coarsegrid dataset aligned to the chosen spatial grid, dims (time, member, lat, lon)

    Notes
    -----
    - NaN masking is applied along spatial dimensions only; all time steps and members are preserved.
    """
    _log("\n" + "="*60)
    _log(" START: align_spatial ".center(60, "="))
    _log("="*60 + "\n")


    #while using xESMF, only these make sense. But perhaps it is worth thinking about switch to rioxarray regridded for
    # coarse_to_fine, as it offers more options than just bilinear

    allowed={"coarse_to_fine":["bilinear"],
             "fine_to_coarse":["conservative"]
            }

    if direction not in allowed.keys():
        raise ValueError("direction must be 'fine_to_coarse' or 'coarse_to_fine'")

    if method not in allowed[direction]:
        raise ValueError("Only {} methods available for {}".format(",".join(allowed[direction]),direction))

    #checking if grids overlap
    overlap_check=_check_grid_overlap(finegrid,coarsegrid,raise_if_missing, threshold)

    # select one timestep for weight generation
    fine_step = finegrid.isel(time=0, drop=True)
    coarse_step = coarsegrid.isel(valid_time=0,drop=True)
    if 'member' in fine_step.dims:
        fine_step = fine_step.isel(member=0)
    if 'member' in coarse_step.dims:
        coarse_step = coarse_step.isel(member=0)
    if 'effective_lead_time' in coarse_step.dims:
        coarse_step = coarse_step.isel(effective_lead_time=0)

    # Regrid
    if direction == "fine_to_coarse":
        _log("Regridding finegrid → coarsegrid (conservative)...")
        regridder = xe.Regridder(fine_step, coarse_step, "conservative")
        finealigned = regridder(finegrid, skipna=True, na_thres=0.5, keep_attrs=True)
        coarsealigned = coarsegrid

    elif direction == "coarse_to_fine":
        _log("Regridding coarsegrid → finegrid ({} )...".format(method))
        regridder = xe.Regridder(coarse_step, fine_step, method, extrap_method="inverse_dist")
        coarsealigned = regridder(coarsegrid, skipna=True, keep_attrs=True)
        finealigned = finegrid

    else:
        raise ValueError("direction must be 'fine_to_coarse' or 'coarse_to_fine'")


    # Apply spatial masks using the first timestep (time=0)
    coarsealigned = coarsealigned.where(~np.isnan(finealigned.isel(time=0).data))
    finealigned = finealigned.where(~coarsealigned.isnull().all(["valid_time","effective_lead_time", "member"]).data)

    attrs=coarsealigned.attrs
    for attr in coarsegrid.attrs:
        attrs
    _log("done")
    _log("\n" + "="*60+"\n")


    return finealigned, coarsealigned




def load_raw_data(nominal_date,
                        download_dir,
                        target_domain,
                        fcst_model,
                        fcst_var,
                        obs_file,
                        obs_var,
                        verbose=True,
                       ):
    """
    reading raw forecast, hindcast, and observations.

    This function reads forecast, hindcast, and observation NetCDF files.

    Parameters
    ----------
    nominal_date : str or datetime-like
        Nominal initialization date of the forecast. Used to identify
        the forecast and hindcast files and to align hindcasts with the
        forecast cycle.

    download_dir : str
        Directory containing forecast and hindcast NetCDF files.

    target_domain : str
        Spatial domain identifier used in the input filenames.

    fcst_model : str
        Forecast model name (e.g., "ECMWF").

    fcst_var : str
        Forecast variable name in the NetCDF files.

    Returns
    -------
    hindcast : xarray.DataArray
        Hindcast data in original structure with dimensions:

        (lead_time, init_date, member, lat, lon)

    forecast : xarray.DataArray
        Forecast data in original structure.

    obs : xarray.DataArray
        Observations data in original structure

        (date, lat, lon)

    Notes
    -----
    * ECMWF precipitation (`tp`) is provided as running accumulation and
      is automatically converted to daily totals.

    """

    #setting up verbosity
    set_verbose(verbose)
    _log("logging is on")


    #feedback
    _log("nominal forecast date: {}".format(nominal_date), force=True)
    _log("download dir: {}".format(download_dir), force=True)
    _log("domain: {}".format(target_domain), force=True)
    _log("model: {}".format(fcst_model), force=True)
    _log("forecast variable: {}".format(fcst_var), force=True)
    _log("observed file: {}".format(obs_file), force=True)
    _log("observed variable: {}".format(obs_var), force=True)


    #*******
    # setting things up
    #*******
    #this is also validation of nominaldate
    try:
        fcst_date=pd.to_datetime(nominal_date)
    except:
        raise TypeError("Forecast date does not appear to be valid")

    fcst_date_str=fcst_date.strftime("%Y%m%d")
    fcst_day=fcst_date.day
    fcst_mon=fcst_date.month
    fcst_year=fcst_date.year

    # download function aligns hindcast date with forecast date, so
    hcst_date=fcst_date

    #*******
    # processing
    #*******

    # forecast data file
    fcst_file="{}/{}_{}_{}_{}_fc.nc".format(download_dir,fcst_var,fcst_model, fcst_date_str, target_domain)

    # hindcast data file
    hcst_file="{}/{}_{}_{}_{}_hc.nc".format(download_dir,fcst_var,fcst_model, fcst_date_str, target_domain)

    #reading forecast data
    forecast=read_netcdf(fcst_file, fcst_var)

    #reading hindast
    hindcast=read_netcdf(hcst_file, fcst_var)

    # reading observed data
    obs=read_netcdf(obs_file, obs_var)

    #returning arrays
    return hindcast,forecast,obs





# registry of available aggregation functions
AGG_FUNCTIONS = {}

def register_agg(name):
    """Decorator to register an aggregation function under a name."""
    def wrapper(func):
        AGG_FUNCTIONS[name] = func
        return func
    return wrapper


# --- built-ins ---

@register_agg("mean")
def _mean(da, dim, **kwargs):
    return da.mean(dim=dim)

@register_agg("sum")
def _sum(da, dim, **kwargs):
    return da.sum(dim=dim)

@register_agg("count_zero")
def _count_zero(da, dim, **kwargs):
    return (da == 0).sum(dim=dim)

@register_agg("count_above")
def _count_above(da, dim, threshold=0, **kwargs):
    return (da > threshold).sum(dim=dim)

@register_agg("max")
def _max(da, dim, **kwargs):
    return da.max(dim=dim)

# aggregations whose result is a number of days, not a value in the units of the data
COUNT_METHODS = ("count_zero", "count_above")




def aggregate(
    data,
    window_size,
    method="mean",
    dim="effective_lead_time",
    **kwargs):
    """
    Resample `data` over `dim` into `agg_window`-sized bins, applying
    the named aggregation function, and masking incomplete trailing windows.

    Parameters
    ----------
    data : xr.DataArray or xr.Dataset
    window_size : int, e.g. 5
    method : str, name of a function registered in AGG_FUNCTIONS
    dim : str, dimension being resampled (default "lead_time")
    **kwargs : passed through to the aggregation function

    The settings are added to the attributes of the output (aggregation_method,
    aggregation_window and, if any, aggregation_kwargs as JSON text), so that they reach
    the products and can be repeated for new observations (align_obs_to_product).
    For counting methods (COUNT_METHODS) the units are set to "days".
    """

    _log(f"Aggregating lead_time to {window_size}-D blocks using ({method})...")

    #arbitrary choice
    agg_windows=list(range(5,11))

    #checking if method is available
    if method not in AGG_FUNCTIONS:
        raise ValueError(
            f"Unknown aggregation method '{method}'. "
            f"Available: {list(AGG_FUNCTIONS)}"
        )

    #picking up requested method
    func = AGG_FUNCTIONS[method]

    # validating aggregation window
    if window_size not in agg_windows:
        raise ValueError(
            "agg_window must be one of {} got '{}'".format(" ".join(map(str, agg_windows)), window_size)
        )

    #agg_window is just window in the xarray format
    agg_window=f"{window_size}D"

    # this converts integer index to timedelta - and this is necessary for the aggregator function
    data = data.assign_coords({dim: pd.to_timedelta(data[dim], "D")})

    # truncate to a multiple of window_days before resampling
    n_total = data.sizes[dim]
    n_full = (n_total // window_size) * window_size

    if n_full < n_total:
        dropped = n_total - n_full
        print(
                f"resample_agg: dropping last {dropped} step(s) of '{dim}' "
                f"({n_total} not divisible by window_size={window_size}); "
                f"keeping {n_full} steps."
        )
        data = data.isel({dim: slice(0, n_full)})

    resampler = data.resample(
        **{dim: agg_window},
        label="left",
        closed="left"
    )

    #aggregating done here!
    aggdata = resampler.map(lambda da: func(da, dim=dim, **kwargs))


    #finding nans
    dims=["effective_lead_time"]
    for v in ["member","target_time","valid_time","init_date","init_lag"]:
        if v in data.dims:
            dims.append(v)

    spatial_nan_mask = np.isnan(data).all(dims)

    #removing all nans
    aggdata = aggdata.where(~spatial_nan_mask)

    #bringing the lead_time to days from timedelta
    #aggdata[dim]=(aggdata[dim]/np.timedelta64(1, 'D')).astype(int)

    # attributes of the input plus the aggregation settings
    attrs = dict(data.attrs)
    attrs.update(aggregation_method=method, aggregation_window=int(window_size))
    if kwargs:
        attrs["aggregation_kwargs"] = json.dumps(kwargs)
    if method in COUNT_METHODS:
        attrs["units"] = "days"
    aggdata = aggdata.assign_attrs(attrs)

    return aggdata





def align_to_nominal_forecast_time(rf_set):
    '''
    A function that aligns downloaded reforecast to nominal forecast date.
    by Josh T.
    '''
    lag_days = rf_set['lag'] * np.timedelta64(1,'D')
    valid_time_lagged = (rf_set.valid_time - lag_days)
    hc_nominal_init_date = (rf_set.hc_init_date - lag_days)

    rf_set = rf_set.assign_coords(hc_nominal_init_date=hc_nominal_init_date,
                                  valid_time=valid_time_lagged,)

    nominal_dates = np.unique(hc_nominal_init_date.values)

    nominal_sets = []

    for nominal_date in nominal_dates:
        # Stack each native initialisation/member combination
        subset = rf_set.stack(source_member=("hc_init_date", "member"))

        # Select the members belonging to this nominal initialisation
        mask = (subset["hc_nominal_init_date"] == nominal_date).compute()

        subset = subset.isel(source_member=np.flatnonzero(mask.values))

        # Retrieve the aligned valid-time axis.
        # It should be the same across all selected members.
        valid_time = subset["valid_time"].isel(source_member=0)

        # Sanity check: all members should have identical aligned valid times
        expected_valid_time = valid_time.broadcast_like(subset["valid_time"])

        if not np.array_equal(subset["valid_time"].values,expected_valid_time.values,):
            raise ValueError(
                f"Aligned valid times differ between members for "
                f"{nominal_date!s}"
            )

        # Preserve the original lag before resetting the stacked index
        lag = subset["lag"].reset_index("source_member", drop=True)

        # Remove coordinates inherited from the stacked dimensions
        subset = subset.reset_index("source_member", drop=True)

        subset = subset.rename(source_member="member")
        subset = subset.assign_coords(member=np.arange(subset.sizes["member"]),lag=("member", lag.values),valid_time=("lead_time", valid_time.values),)

        # Add the new nominal initialisation dimension as a single value
        subset = subset.drop_vars("hc_nominal_init_date",errors="ignore",)
        subset = subset.assign_coords(hc_nominal_init_date=np.datetime64(nominal_date))

        nominal_sets.append(subset)

    result = xr.concat(nominal_sets,dim="hc_nominal_init_date",join="exact",coords=["valid_time"])

    output_rf_set = result.transpose("hc_nominal_init_date","member","lead_time","latitude","longitude",)

    return output_rf_set








def _find_cycles(init_dates, max_gap=None):
    """
    Group sorted init dates into cycles of staggered initialisations.

    A new cycle starts wherever the gap to the previous init date exceeds `max_gap`.
    max_gap : timedelta-like (e.g. "10D"), or None to infer it: with all gaps equal there is
              a single cycle (e.g. a forecast); otherwise the threshold is the geometric mean
              of the smallest and largest gap (2 days and ~1 year -> ~27 days).
    Returns a 2-D array (n_cycles, n_inits_per_cycle) of dates; all cycles must have the
    same number of inits.
    """
    dates = np.sort(np.asarray(init_dates))
    if len(dates) == 1:
        return dates[None, :]
    gaps = np.diff(dates)
    if max_gap is None:
        g = gaps / np.timedelta64(1, "s")
        if g.min() == g.max():
            return dates[None, :]                               # one cycle
        thresh = np.timedelta64(int(np.sqrt(g.min() * g.max())), "s")
    else:
        thresh = np.timedelta64(pd.Timedelta(max_gap).value, "ns")
    starts = np.r_[0, np.flatnonzero(gaps > thresh) + 1]
    groups = np.split(dates, starts[1:])
    sizes = sorted({len(g) for g in groups})
    if len(sizes) > 1:
        raise ValueError(f"cycles have different numbers of inits {sizes} with a gap threshold "
                         f"of {thresh.astype('timedelta64[h]')}; check the init dates or pass max_gap")
    return np.stack(groups)


def _check_daily_leads(leads, name):
    """Raise unless lead times are whole days, one day apart."""
    leads = np.asarray(leads).astype("timedelta64[ns]")
    steps = np.diff(leads)
    if (leads % ONE_DAY).any() or (len(steps) and (steps != ONE_DAY).any()):
        found = sorted(set((steps / ONE_DAY).round(3).tolist())) if len(steps) else []
        found = [int(f) if float(f).is_integer() else f for f in found]
        raise ValueError(f"'{name}' must be daily (steps of 1 day); found steps of {found} days. "
                         "Restructure daily data first and aggregate afterwards.")


def hcst_to_effective_lead_time(ds, n_inits_per_cycle=None, *, anchor=None, trim=False, max_gap=None,
                      init_dim="hc_init_date", lead_dim="lead_time", member_dim="member",
                      drop_coords=("valid_time",)):
    """
    Combine staggered initialisations into cycles with a common lead-time axis.

    Parameters
    ----------
    ds : Dataset or DataArray with dims (init_dim, lead_dim, member_dim, ...).
         lead_dim must be daily (timedelta, steps of 1 day); otherwise ValueError.
         Aggregate only after restructuring.
    n_inits_per_cycle : number of initialisations per cycle. If None (default) the cycles are
         inferred from gaps between init dates (see find_cycles); if given, it is checked
         against the inferred grouping.
    max_gap : passed to find_cycles; only needed if the automatic grouping fails.
    anchor : "earliest" or "latest". Date that labels the cycle and from which
         effective_lead_time is counted. Default: "earliest", or "latest" if trim=True.
         "earliest": later inits start later -> NaN at their first leads.
         "latest"  : earlier inits are cut before the anchor and end earlier ->
                     NaN at their last leads.
         Without trimming, the effective_lead_time axis has the same values as lead_dim.
    trim : if True, keep only effective lead times covered by every initialisation (no NaN
         from the staggering). Requires anchor="latest" (the default when trim=True); the
         trailing leads where earlier inits have already ended are removed.
    drop_coords : coordinates along (init_dim, lead_dim) to drop; they would be wrong after
         shifting. 'target_time' (= valid_time + effective_lead_time) is added instead.

    Returns
    -------
    Same type as ds, dims (valid_time, effective_lead_time, member, ...), with coordinates
      init_date(valid_time, member) : actual initialisation date of each member
      init_lag(valid_time, member)  : init_date - valid_time (timedelta)
      target_time(valid_time, effective_lead_time)
    plus any other coordinates along (init_dim, member_dim), e.g. 'lag', as (valid_time, member).
    Data variables are float with NaN where an initialisation has no data; their on-disk
    packing (integer dtype, scale_factor, _FillValue) is cleared so that NaN survives saving.
    """
    if anchor is None:
        anchor = "latest" if trim else "earliest"
    if anchor not in ("earliest", "latest"):
        raise ValueError("anchor must be 'earliest' or 'latest'")
    if trim and anchor != "latest":
        raise ValueError("trim=True requires anchor='latest'")
    _check_daily_leads(ds[lead_dim].values, lead_dim)
    ds = ds.drop_vars([c for c in drop_coords if c in ds.coords]).sortby(init_dim)

    cycles = _find_cycles(ds[init_dim].values, max_gap)
    if n_inits_per_cycle is not None and cycles.shape[1] != n_inits_per_cycle:
        raise ValueError(f"found {cycles.shape[1]} inits per cycle in the data, "
                         f"but n_inits_per_cycle={n_inits_per_cycle}")
    if ((cycles - cycles[:, :1]) % ONE_DAY).any():
        raise ValueError("inits within a cycle must be whole days apart")

    leads = ds[lead_dim].values
    n_mem = ds.sizes[member_dim]

    out_cycles = []
    for dates in cycles:
        a = dates[0] if anchor == "earliest" else dates[-1]
        parts = []
        for k, d in enumerate(dates):
            offset = d - a                                   # >= 0 (earliest) or <= 0 (latest)
            x = ds.sel({init_dim: d}, drop=True)
            # value at original lead L belongs to effective lead L + offset
            x = x.assign_coords({lead_dim: x[lead_dim] + offset}).reindex({lead_dim: leads})
            x = x.assign_coords({member_dim: np.arange(k * n_mem, (k + 1) * n_mem,
                                                       dtype=ds[member_dim].dtype),
                                 "init_date": (member_dim, np.full(n_mem, d)),
                                 "init_lag": (member_dim, np.full(n_mem, offset))})
            parts.append(x)
        cyc = xr.concat(parts, dim=member_dim, coords="minimal", compat="equals", join="exact")
        out_cycles.append(cyc.expand_dims(valid_time=[a]))

    member_coords = [c for c in out_cycles[0].coords
                     if member_dim in out_cycles[0][c].dims and c != member_dim]
    out = xr.concat(out_cycles, dim="valid_time", coords=member_coords,
                    compat="equals", join="exact")
    out = out.rename({lead_dim: "effective_lead_time"})
    out = out.assign_coords(effective_lead_time=out["effective_lead_time"].astype("timedelta64[ns]"))

    if trim:
        # leads covered by every init in every cycle, from the offsets (not from the data,
        # which may contain genuine NaN, e.g. over the ocean)
        lags = out["init_lag"].values                        # (valid_time, member), <= 0
        last = leads[-1] + lags.min()                        # earliest init ends first
        out = out.sel(effective_lead_time=slice(leads[0], last))

    out = out.assign_coords(target_time=out["valid_time"] + out["effective_lead_time"])

    _clear_packing(out)
    return out.transpose("valid_time", "effective_lead_time", member_dim, ...)






def fcst_to_effective_lead_time(fc, *, leads=None, time_dim="valid_time", member_dim="member",
                                init_coord="fc_init_date", drop_coords=("lead_time",)):
    """
    Bring a forecast that is already on a calendar-date axis into the same format as
    to_effective_init(hindcast, trim=True).

    Input  : (valid_time, member, lat, lon) where valid_time are target dates and each member
             has its initialisation date in coordinate `init_coord` (member,).
    Output : (valid_time: 1, effective_lead_time, member, lat, lon)
             valid_time          = first date (from the latest initialisation on) at which
                                   every member has data
             effective_lead_time = target date - valid_time, starting at 0 (as for the hindcast)
             coords init_date, init_lag (= init_date - valid_time) (valid_time, member),
             target_time (valid_time, effective_lead_time), other member coords (e.g. 'lag')
             as (valid_time, member).

    leads : effective lead times to keep, e.g. hcst.effective_lead_time, so that forecast and
            hindcast have identical lead axes; an error is raised if a requested lead is
            missing or if any member has no data at it. If None, all leads up to the last one
            at which every member has data are kept (like trim=True).
    """
    t = fc[time_dim].values
    _check_daily_leads(t - t[0], time_dim)
    fc = fc.drop_vars([c for c in drop_coords if c in fc.coords])
    anchor = fc[init_coord].values.max()

    def gaps(o):
        """True at dates where any member has no data anywhere in the domain."""
        first = o if isinstance(o, xr.DataArray) else o[list(o.data_vars)[0]]
        space = [d for d in first.dims if d not in (time_dim, member_dim)]
        g = first.isnull().all(space) if space else first.isnull()
        return g.any(member_dim).values

    # dates from the latest init on; the first date with data from every member is lead 0
    out = fc.isel({time_dim: np.flatnonzero(fc[time_dim].values >= anchor)})
    ok = np.flatnonzero(~gaps(out))
    if ok.size == 0:
        raise ValueError("no date at which every member has data")
    out = out.isel({time_dim: slice(ok[0], None)})
    dates = out[time_dim].values
    out = (out.assign_coords(effective_lead_time=(time_dim, (dates - dates[0]).astype("timedelta64[ns]")),
                             target_time=(time_dim, dates))
              .swap_dims({time_dim: "effective_lead_time"})
              .drop_vars(time_dim))

    def gap_leads(o):
        return gaps(o.rename({"effective_lead_time": time_dim}))

    if leads is None:
        bad = np.flatnonzero(gap_leads(out))
        if bad.size:                                       # trailing gaps: earlier inits ended
            out = out.isel(effective_lead_time=slice(0, bad[0]))
    else:
        leads = np.asarray(leads).astype("timedelta64[ns]")
        missing = np.setdiff1d(leads, out["effective_lead_time"].values)
        if missing.size:
            raise ValueError(f"forecast does not cover leads {missing.astype('timedelta64[D]')}")
        out = out.sel(effective_lead_time=leads)
        bad = out["effective_lead_time"].values[gap_leads(out)]
        if bad.size:
            raise ValueError(f"some members have no data at leads {bad.astype('timedelta64[D]')}")

    vt = dates[0]                                          # effective lead 0
    out = out.drop_vars("target_time")
    out = out.rename({init_coord: "init_date"}) if init_coord != "init_date" else out
    out = out.assign_coords(init_lag=out["init_date"] - vt)
    out = out.expand_dims(valid_time=[vt])
    member_coords = [c for c in out.coords if out[c].dims == (member_dim,) and c != member_dim]
    out = out.assign_coords({c: out[c].expand_dims(valid_time=[vt]) for c in member_coords})
    out = out.assign_coords(target_time=out["valid_time"] + out["effective_lead_time"])
    _clear_packing(out)
    return out.transpose("valid_time", "effective_lead_time", member_dim, ...)






def fcst_to_effective_lead_time_v0(fc, *, leads=None, time_dim="valid_time", member_dim="member",
                               init_coord="fc_init_date",
                               drop_coords=("lead_time",)):
    """
    Bring a forecast that is already on a calendar-date axis into the same format as
    to_effective_init(hindcast, trim=True).

    Input  : (valid_time, member, lat, lon) where valid_time are target dates and each member
             has its initialisation date in coordinate `init_coord` (member,).
    Output : (valid_time: 1, effective_lead_time, member, lat, lon)
             valid_time          = latest initialisation date (the anchor)
             effective_lead_time = target date - anchor
             coords init_date, init_lag (valid_time, member), target_time
             (valid_time, effective_lead_time), other member coords (e.g. 'lag') as
             (valid_time, member).

    leads : effective lead times to keep, e.g. hcst.effective_lead_time, so that forecast and
            hindcast have identical lead axes; an error is raised if a requested lead is
            missing or if any member has no data at it. If None, leads at which any member has
            no data anywhere in the domain (staggering gaps) are removed, like trim=True.
    """
    fc = fc.drop_vars([c for c in drop_coords if c in fc.coords])
    init = fc[init_coord]
    anchor = init.values.max()

    eff = fc[time_dim].values - anchor
    out = fc.isel({time_dim: np.flatnonzero(eff >= np.timedelta64(0, "ns"))})
    out = (out.assign_coords(effective_lead_time=(time_dim, out[time_dim].values - anchor))
              .swap_dims({time_dim: "effective_lead_time"})
              .drop_vars(time_dim))

    out = out.assign_coords(effective_lead_time=out["effective_lead_time"].astype("timedelta64[ns]"))

    # staggering gaps: a member with no data anywhere in the domain at a lead
    def gap_leads(o):
        first = o if isinstance(o, xr.DataArray) else o[list(o.data_vars)[0]]
        space = [d for d in first.dims if d not in ("effective_lead_time", member_dim)]
        gaps = first.isnull().all(space) if space else first.isnull()
        return gaps.any(member_dim).values

    if leads is None:
        out = out.isel(effective_lead_time=np.flatnonzero(~gap_leads(out)))   # trim
    else:
        leads = np.asarray(leads).astype("timedelta64[ns]")
        missing = np.setdiff1d(leads, out["effective_lead_time"].values)
        if missing.size:
            raise ValueError(f"forecast does not cover leads {missing.astype('timedelta64[D]')}")
        out = out.sel(effective_lead_time=leads)
        bad = out["effective_lead_time"].values[gap_leads(out)]
        if bad.size:
            raise ValueError(f"some members have no data at leads {bad.astype('timedelta64[D]')}")

    out = out.rename({init_coord: "init_date"}) if init_coord != "init_date" else out
    out = out.assign_coords(init_lag=out["init_date"] - anchor)
    out = out.expand_dims(valid_time=[anchor])
    member_coords = [c for c in out.coords if out[c].dims == (member_dim,) and c != member_dim]
    out = out.assign_coords({c: out[c].expand_dims(valid_time=[anchor]) for c in member_coords})
    out = out.assign_coords(target_time=out["valid_time"] + out["effective_lead_time"])
    _clear_packing(out)
    return out.transpose("valid_time", "effective_lead_time", member_dim, ...)



def _clear_packing(obj):
    """NaN must survive writing: drop integer packing inherited from the source file."""
    variables = [obj] if isinstance(obj, xr.DataArray) else [obj[v] for v in obj.data_vars]
    for var in variables:
        for key in ("dtype", "scale_factor", "add_offset", "_FillValue", "missing_value"):
            var.encoding.pop(key, None)


ONE_DAY = np.timedelta64(1, "D")








def align_obs_to_model_time(obs, model, *, add_members=False, raise_if_missing=True, obs_time="time",
              init_dim="valid_time", lead_dim="effective_lead_time", member_dim="member"):
    """
    Put daily observations on the (valid_time, effective_lead_time) structure of `model`.

    Parameters
    ----------
    obs : DataArray or Dataset (time, lat, lon), daily, no gaps.
    model : hindcast or forecast in effective-init format, with daily lead times.
    add_members : replicate obs along the model's member dim, NaN where a model member has
          no data anywhere in the domain (e.g. staggering gaps in untrimmed data).
    raise_if_missing : if True, raise if obs do not cover all model target dates; if False,
          drop the valid_times (cycles) that are not fully covered, from obs and model.

    Returns
    -------
    obs_aligned : (valid_time, effective_lead_time, [member,] lat, lon), with target_time
    model_aligned : model, restricted to fully covered valid_times if raise_if_missing=False

    Raises
    ------
    ValueError if obs are not daily without gaps, or if the model lead times are not daily
    (e.g. already aggregated).
    """
    _log(" align_obs ".center(60, "="))

    obs = obs.assign_coords({obs_time: obs.indexes[obs_time].normalize()})
    model = model.assign_coords({init_dim: model.indexes[init_dim].normalize()})

    if len(obs[obs_time]) > 1 and (np.diff(obs[obs_time].values) != ONE_DAY).any():
        raise ValueError("obs must be daily without gaps")
    leads = model[lead_dim].values.astype("timedelta64[ns]")
    if len(leads) > 1 and (np.diff(leads) != ONE_DAY).any():
        raise ValueError(f"model lead times must be daily; found steps of "
                         f"{sorted(set(np.diff(leads).astype('timedelta64[D]').astype(int).tolist()))} "
                         "days. Align daily data first, then aggregate model and obs together.")

    # target dates (valid_time, lead)
    vt = model[init_dim].values
    dates = vt[:, None] + leads[None, :]

    # coverage
    have = obs[obs_time].values
    missing_per_vt = (~np.isin(dates, have)).any(axis=1)
    _log(f"obs: {str(have[0])[:10]} to {str(have[-1])[:10]} | "
         f"model targets: {str(dates.min())[:10]} to {str(dates.max())[:10]}")
    if missing_per_vt.any():
        if raise_if_missing:
            raise ValueError(f"obs do not cover {missing_per_vt.sum()} of {len(vt)} valid_times")
        _log(f"WARNING: dropping {missing_per_vt.sum()} valid_times not covered by obs")
        keep = ~missing_per_vt
        model, dates, vt = model.isel({init_dim: keep}), dates[keep], vt[keep]
    else:
        _log("obs cover all model target dates")

    # select obs for every (valid_time, lead) at once
    out = obs.sel({obs_time: xr.DataArray(dates, dims=[init_dim, lead_dim])}).drop_vars(obs_time)
    out = out.assign_coords({init_dim: vt, lead_dim: model[lead_dim].values})
    if "target_time" in model.coords:
        out = out.assign_coords(target_time=model["target_time"])

    if add_members:
        first = model if isinstance(model, xr.DataArray) else model[list(model.data_vars)[0]]
        space = [d for d in first.dims if d not in (init_dim, lead_dim, member_dim)]
        has_data = first.notnull().any(space)                 # (valid_time, lead, member)
        member_coords = {c: model[c] for c in model.coords
                         if member_dim in model[c].dims and c != member_dim}
        out = out.expand_dims({member_dim: model[member_dim].values}).where(has_data)
        out = out.assign_coords(member_coords)

    order = [init_dim, lead_dim] + ([member_dim] if add_members else [])
    out = out.transpose(*order, ...)
    _log("=" * 60)
    return out, model




def align_obs_to_product(obs, product, *, raise_if_missing=True):
    """
    Put raw daily observations on the grid and (aggregated) lead times of a saved forecast
    product, repeating the steps of the hindcast pipeline with the settings stored in the
    product, so that the result can go straight into verify_deterministic /
    verify_probabilistic.

    Steps (settings from the product attributes, written there by align_grid and aggregate):
      1. grid  - regrid_direction "fine_to_coarse": obs regridded conservatively to the
                 product grid (regrid_method, regrid_nan_threshold);
                 "coarse_to_fine": the obs kept their own grid in the pipeline (the model
                 was interpolated to it), so the product's grid points are taken from the
                 obs, which must be on the same grid.
                 Grid cells without forecast data are set to NaN.
      2. dates - the daily obs of every day covered by the forecast: valid_time + daily
                 leads from the first lead to the end of the last aggregation window
                 (as align_obs_to_model_time).
      3. aggregation - aggregate() with aggregation_method, aggregation_window and
                 aggregation_kwargs; lead times are the starts of the windows, as in the
                 product.

    Parameters
    ----------
    obs : DataArray (time, latitude, longitude), daily, as returned by read_netcdf
          (with units=... if the file's units need replacing).
    product : product Dataset (make_deterministic_product / make_probabilistic_product, or
          the saved file).
    raise_if_missing : passed to align_grid and align_obs_to_model_time; with True (default)
          an error is raised if the obs do not cover the grid or the forecast dates.

    Returns
    -------
    DataArray (valid_time, effective_lead_time, latitude, longitude), aligned with the
    product's forecast.
    """
    _log(" align_obs_to_product ".center(60, "="))

    a = product.attrs
    needed = ["regrid_direction", "regrid_method", "regrid_nan_threshold",
              "aggregation_method", "aggregation_window"]
    missing = [k for k in needed if k not in a]
    if missing:
        raise ValueError(f"the product has no {missing} attributes: it was made from obs that "
                         "did not go through the current align_grid / aggregate; regenerate it")

    fc = product["fcst_mean"] if "fcst_mean" in product else product["fcst_prob"]
    other = [d for d in fc.dims if d not in ("latitude", "longitude")]
    has_data = fc.notnull().any(other)                    # (latitude, longitude)

    # 1. grid
    if a["regrid_direction"] == "fine_to_coarse":
        template = xr.ones_like(has_data, dtype=float).where(has_data)
        obs_grid, _ = align_grid(obs, template, direction="fine_to_coarse",
                                 method=a["regrid_method"],
                                 nan_threshold=float(a["regrid_nan_threshold"]),
                                 raise_if_missing=raise_if_missing)
    else:
        try:
            obs_grid = obs.sel(latitude=fc["latitude"].values, longitude=fc["longitude"].values)
        except KeyError:
            raise ValueError("the product was made with regrid_direction='coarse_to_fine', i.e. on "
                             "the grid of the obs, but these obs are on a different grid") from None
    obs_grid = obs_grid.drop_vars([c for c in obs_grid.coords if c not in obs_grid.dims])
    obs_grid = obs_grid.where(has_data)

    # 2. daily dates covered by the aggregated leads
    window = int(a["aggregation_window"])
    leads = product["effective_lead_time"].values.astype("timedelta64[ns]")
    daily = np.arange(leads[0], leads[-1] + window * ONE_DAY, ONE_DAY).astype("timedelta64[ns]")
    model_like = xr.DataArray(np.zeros((product.sizes["valid_time"], len(daily))),
                              dims=["valid_time", "effective_lead_time"],
                              coords=dict(valid_time=product["valid_time"].values,
                                          effective_lead_time=daily))
    obs_daily, _ = align_obs_to_model_time(obs_grid, model_like,
                                           raise_if_missing=raise_if_missing)

    # 3. aggregation, as for the hindcast
    kwargs = json.loads(a.get("aggregation_kwargs", "{}"))
    out = aggregate(obs_daily, window, a["aggregation_method"], **kwargs)
    found = out["effective_lead_time"].values.astype("timedelta64[ns]")
    if not np.array_equal(found, leads):
        raise ValueError(f"aggregated obs leads {found.astype('timedelta64[D]').tolist()} differ "
                         f"from the product's {leads.astype('timedelta64[D]').tolist()}; the "
                         "product's aggregation attributes do not match its lead times")
    out = out.assign_coords(effective_lead_time=leads).where(has_data)

    u_obs, u_prod = out.attrs.get("units"), a.get("units")
    if u_obs and u_prod and u_obs != u_prod:
        raise ValueError(f"obs units '{u_obs}' differ from the product's '{u_prod}'; set the "
                         "units when reading the obs (read_netcdf(..., units=...))")

    _log("=" * 60)
    return out.transpose("valid_time", "effective_lead_time", "latitude", "longitude")









def align_obs_to_model_time_v0(obs, model, *, add_members=False, raise_if_missing=True, obs_time="time",
              init_dim="valid_time", lead_dim="effective_lead_time", member_dim="member"):
    """
    Put daily observations on the (valid_time, effective_lead_time) structure of `model`.

    Parameters
    ----------
    obs : DataArray or Dataset (time, lat, lon), daily, no gaps.
    model : hindcast or forecast in effective-init format, with daily lead times.
    add_members : replicate obs along the model's member dim, NaN where a model member has
          no data anywhere in the domain (e.g. staggering gaps in untrimmed data).
    raise_if_missing : if True, raise if obs do not cover all model target dates; if False,
          drop the valid_times (cycles) that are not fully covered, from obs and model.

    Returns
    -------
    obs_aligned : (valid_time, effective_lead_time, [member,] lat, lon), with target_time
    model_aligned : model, restricted to fully covered valid_times if raise_if_missing=False

    Raises
    ------
    ValueError if obs are not daily without gaps, or if the model lead times are not daily
    (e.g. already aggregated).
    """
    _log(" align_obs ".center(60, "="))

    obs = obs.assign_coords({obs_time: obs.indexes[obs_time].normalize()})
    model = model.assign_coords({init_dim: model.indexes[init_dim].normalize()})

    if len(obs[obs_time]) > 1 and (np.diff(obs[obs_time].values) != ONE_DAY).any():
        raise ValueError("obs must be daily without gaps")
    leads = model[lead_dim].values.astype("timedelta64[ns]")
    if len(leads) > 1 and (np.diff(leads) != ONE_DAY).any():
        raise ValueError(f"model lead times must be daily; found steps of "
                         f"{sorted(set(np.diff(leads).astype('timedelta64[D]').astype(int).tolist()))} "
                         "days. Align daily data first, then aggregate model and obs together.")

    # target dates (valid_time, lead)
    vt = model[init_dim].values
    dates = vt[:, None] + leads[None, :]

    # coverage
    have = obs[obs_time].values
    missing_per_vt = (~np.isin(dates, have)).any(axis=1)
    _log(f"obs: {str(have[0])[:10]} to {str(have[-1])[:10]} | "
         f"model targets: {str(dates.min())[:10]} to {str(dates.max())[:10]}")
    if missing_per_vt.any():
        if raise_if_missing:
            raise ValueError(f"obs do not cover {missing_per_vt.sum()} of {len(vt)} valid_times")
        _log(f"WARNING: dropping {missing_per_vt.sum()} valid_times not covered by obs")
        keep = ~missing_per_vt
        model, dates, vt = model.isel({init_dim: keep}), dates[keep], vt[keep]
    else:
        _log("obs cover all model target dates")

    # select obs for every (valid_time, lead) at once
    out = obs.sel({obs_time: xr.DataArray(dates, dims=[init_dim, lead_dim])}).drop_vars(obs_time)
    out = out.assign_coords({init_dim: vt, lead_dim: model[lead_dim].values})
    if "target_time" in model.coords:
        out = out.assign_coords(target_time=model["target_time"])

    if add_members:
        first = model if isinstance(model, xr.DataArray) else model[list(model.data_vars)[0]]
        space = [d for d in first.dims if d not in (init_dim, lead_dim, member_dim)]
        has_data = first.notnull().any(space)                 # (valid_time, lead, member)
        member_coords = {c: model[c] for c in model.coords
                         if member_dim in model[c].dims and c != member_dim}
        out = out.expand_dims({member_dim: model[member_dim].values}).where(has_data)
        out = out.assign_coords(member_coords)

    order = [init_dim, lead_dim] + ([member_dim] if add_members else [])
    out = out.transpose(*order, ...)
    _log("=" * 60)
    return out, model






"""
Spatial alignment of two datasets with xarray-regrid (pip-installable replacement for xESMF).

Note on performance: if the optional package `sparse` is installed (it is a dependency of
xESMF, among others), xarray-regrid stores its conservative weights as sparse arrays. For
dense data this is ~300x slower, uses far more memory, and returns sparse-backed results.
align_grid therefore runs xarray-regrid with dense weights (see _dense_weights).
"""

#from __future__ import annotations

from contextlib import contextmanager

#import numpy as np
#import xarray as xr
import xarray_regrid  # noqa: F401  (registers the .regrid accessor)
import xarray_regrid.methods.conservative as _xrc

LAT_NAMES = ("lat", "latitude")
LON_NAMES = ("lon", "longitude")



@contextmanager
def _dense_weights():
    """Make xarray-regrid use dense weights even if `sparse` is installed.
    Relies on xarray-regrid's module attribute `sparse` (checked in v0.4.2)."""
    saved = getattr(_xrc, "sparse", None)
    _xrc.sparse = None
    try:
        yield
    finally:
        _xrc.sparse = saved


def _spatial_names(da):
    """Names of the latitude and longitude dimensions of `da`."""
    lat = next((n for n in LAT_NAMES if n in da.dims), None)
    lon = next((n for n in LON_NAMES if n in da.dims), None)
    if lat is None or lon is None:
        raise ValueError(f"no lat/lon dimensions found in {da.dims}; expected one of "
                         f"{LAT_NAMES} and one of {LON_NAMES}")
    return lat, lon


def _crop_to(src, slat, slon, ref, rlat, rlon):
    """Crop src to the extent of ref plus one ref grid cell (either latitude order)."""
    def step(c):
        v = np.asarray(c.values, dtype=float)
        return float(np.abs(np.diff(v)).max()) if v.size > 1 else 0.0
    pad_lat, pad_lon = step(ref[rlat]), step(ref[rlon])
    lo, hi = float(ref[rlat].min()) - pad_lat, float(ref[rlat].max()) + pad_lat
    lat_sl = slice(hi, lo) if src[slat].values[0] > src[slat].values[-1] else slice(lo, hi)
    lon_sl = slice(float(ref[rlon].min()) - pad_lon, float(ref[rlon].max()) + pad_lon)
    out = src.sel({slat: lat_sl, slon: lon_sl})
    if out.sizes[slat] == 0 or out.sizes[slon] == 0:
        raise ValueError("grids do not overlap after cropping; check longitude conventions "
                         "(0..360 vs -180..180) and latitude ranges")
    return out


def align_grid_sparse(finegrid, coarsegrid, direction="fine_to_coarse", method="conservative",
               raise_if_missing=True, threshold=0.9, nan_threshold=0.5):
    """
    Put two datasets on the same spatial grid, keeping all other dimensions.

    Parameters
    ----------
    finegrid : DataArray, high resolution, e.g. observations (time, lat, lon).
    coarsegrid : DataArray, low resolution, e.g. model data
        (valid_time, effective_lead_time, member, latitude, longitude).
    direction : "fine_to_coarse" (default) or "coarse_to_fine".
        "fine_to_coarse": finegrid is regridded to the coarse grid, conservatively
                          (area-weighted mean of the fine cells in each coarse cell).
        "coarse_to_fine": coarsegrid is interpolated bilinearly to the fine grid; fine cells
                          outside the area spanned by the coarse cell centres get the value
                          of the nearest coarse cell.
    method : "conservative" for fine_to_coarse, "bilinear" for coarse_to_fine.
    raise_if_missing, threshold : passed to _check_grid_overlap.
    nan_threshold : fine_to_coarse only. Largest fraction of NaN (by area) in a coarse cell
        for which a value is still computed from the valid part; above it the coarse cell is
        NaN. Same meaning as xESMF's na_thres.

    Returns
    -------
    finealigned, coarsealigned : both on the chosen grid, with the dimension names of that
        grid. Cells without data in either dataset are NaN in both. Attributes are kept.
    """
    _log(" align_grid ".center(60, "="))

    allowed = {"fine_to_coarse": ["conservative"], "coarse_to_fine": ["bilinear"]}
    if direction not in allowed:
        raise ValueError("direction must be 'fine_to_coarse' or 'coarse_to_fine'")
    if method not in allowed[direction]:
        raise ValueError(f"only {', '.join(allowed[direction])} available for {direction}")

    _check_grid_overlap(finegrid, coarsegrid, raise_if_missing, threshold)

    flat, flon = _spatial_names(finegrid)
    clat, clon = _spatial_names(coarsegrid)

    if direction == "fine_to_coarse":
        _log("Regridding finegrid -> coarsegrid (conservative)...")
        # crop first: xarray-regrid's cost grows with the size of the source grid
        # xarray-regrid matches grids by coordinate name: use the coarse grid's names
        src = _crop_to(finegrid, flat, flon, coarsegrid, clat, clon).rename({flat: clat, flon: clon})
        target = xr.Dataset(coords={clat: coarsegrid[clat], clon: coarsegrid[clon]})
        with _dense_weights():
            finealigned = src.regrid.conservative(target, latitude_coord=clat, time_dim=None,
                                                  skipna=True, nan_threshold=nan_threshold)
        finealigned = finealigned.assign_attrs(finegrid.attrs)
        coarsealigned = coarsegrid
        lat, lon = clat, clon
    else:
        _log("Regridding coarsegrid -> finegrid (bilinear)...")
        src = _crop_to(coarsegrid, clat, clon, finegrid, flat, flon).rename({clat: flat, clon: flon})
        target = xr.Dataset(coords={flat: finegrid[flat], flon: finegrid[flon]})
        lin = src.regrid.linear(target, time_dim=None)
        nearest = src.reindex({flat: finegrid[flat], flon: finegrid[flon]}, method="nearest")
        coarsealigned = lin.fillna(nearest).assign_attrs(coarsegrid.attrs)
        finealigned = finegrid
        lat, lon = flat, flon

    # common spatial mask: cells with data in both datasets (at any time / lead / member)
    def has_data(da):
        other = [d for d in da.dims if d not in (lat, lon)]
        return da.notnull().any(other) if other else da.notnull()

    mask = has_data(finealigned) & has_data(coarsealigned)
    finealigned = finealigned.where(mask)
    coarsealigned = coarsealigned.where(mask)

    _log(f"done: {int(mask.sum())} of {mask.size} grid cells with data in both")
    _log("=" * 60)
    return finealigned, coarsealigned
