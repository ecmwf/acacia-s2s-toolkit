# SPDX-FileCopyrightText: 2024 European Centre for Medium-Range Weather Forecasts (ECMWF)
# SPDX-License-Identifier: Apache-2.0

# download sub-seasonal reforecast from S2S Database
from acacia_s2s_toolkit import argument_check, argument_output, ecdsAPI_requests, download_S2Stc_tracks, grid_functions
import os
import sys
import datetime
import numpy as np

# this is for sphinx - only functions listed here will have entries in readthedocs API
__all__ = ["download_hindcast"]

class SuppressOutput:
    """Context manager to silence stdout/stderr (for ECMWF WebAPI logs)."""
    def __enter__(self):
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        return self

    def __exit__(self, exc_type, exc, tb):
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = self._stdout
        sys.stderr = self._stderr
        # If an exception happened, return False so Python re-raises it (with logs visible next time)
        return False

def download_hindcast(variable,
                      model='ECMWF',
                      fcdate=None,
                      leadtime_hour=None,
                      start_lt=0,
                      end_lt=None,
                      period='1D',
                      country_name=None,
                      region_name=None,
                      bbox_bounds=[90, -180, -90, 180],
                      plevs=None,
                      filename=None,
                      data_save_dir=None,
                      data_format="netcdf",
                      grid="1.5x1.5",
                      rf_enslags=None,
                      rf_years=None,
                      fc_time=True,
                      overwrite=False,
                      verbose=True,
                      cleanup=True):

    """
    Overarching function that will download hindcast data from ECDS.

    Parameters
    ----------
    variable : str
        Variable to download.
    model : str
        Forecast model name (default = 'ECMWF').
    fcdate : str, optional
        Forecast initialization date in YYYYMMDD format. If None, today's UTC
        date is used and rolled back until a valid forecast date is found.
    plevs : int or list[int], optional
        Pressure level(s), where applicable.
    country_name : str, optional
        Country name used to derive bounds automatically from Natural Earth
        country polygons. If provided, this overrides both region_name and
        bbox_bounds.
    region_name : str, optional
        Predefined domain name. If provided, this overrides bbox_bounds unless
        country_name is also provided.
    bbox_bounds : list[float]
        Bounding box in the form [north, west, south, east].
    filename : str, optional
        Output filename without or with extension.
    data_save_dir : str, optional
        Directory where the downloaded file will be saved.
    data_format : str
        Output format, e.g. "netcdf" or "grib".
    grid : str
        Grid resolution as "dlonxdlat", e.g. "1.5x1.5".
    leadtime_hour : optional
        Forecast lead hours passed to downstream request logic.
    rf_years : optional
        Hindcast years passed to downstream request logic.
    rf_enslags : optional
        Hindcast ensemble lag selection passed to downstream request logic.
    fc_time : bool
        Passed to hindcast request logic.
    overwrite : bool
        If False and file exists already, skip the download.
    verbose : bool
        If True, print diagnostic information.

    Returns
    -------
    str
        Path to the saved file (or intended saved file base, depending on
        downstream request behaviour).
    """

    # Normalise grid for downstream request code
    grid_for_request = grid.replace("x", "/")

    # ------------------------------------------------------------------
    # Domain resolution priority:
    # 1. country_name
    # 2. region_name
    # 3. bbox_bounds
    # ------------------------------------------------------------------
    if country_name is not None:
        bbox_bounds = grid_functions.get_country_bbox_bounds(country_name, resolution="110m")
        region_name = None
    elif region_name is not None:
        cname = region_name.lower().replace(" ", "")
        if cname not in grid_functions.DOMAIN_BOUNDS:
            raise ValueError(
                f"Unsupported region_name '{region_name}'. "
                f"Choose from {list(grid_functions.DOMAIN_BOUNDS)}."
            )
        bbox_bounds = grid_functions.DOMAIN_BOUNDS[cname]
        region_name = cname
    else:
        cname = grid_functions.match_domain_from_bbox_bounds(bbox_bounds)
        if cname is not None:
            region_name = cname

    # Snap bbox to the nearest valid global model grid while ensuring
    # the requested domain remains fully contained.
    original_bbox_bounds = list(map(float, bbox_bounds))
    bbox_bounds = grid_functions.snap_bbox_to_grid_containing(bbox_bounds, grid=grid)
    bbox_bounds = [float(x) for x in bbox_bounds]

    # Date handling with rollback to get the latest available forecast
    if fcdate is None:
        fcdate = datetime.datetime.utcnow().strftime("%Y%m%d")

    # Make sure only uppercase model name is used if needed
    model = model.upper() if any(c.islower() for c in model) else model
    origin_id = argument_output.output_originID(model, fcdate)

    while True:
        try:
            argument_check.check_fcdate(fcdate, origin_id)
            break
        except ValueError:
            old_date = fcdate
            fcdate = (
                datetime.datetime.strptime(fcdate, "%Y%m%d")
                - datetime.timedelta(days=1)
            ).strftime("%Y%m%d")
            if verbose:
                print(f"[INFO] {old_date} not valid, rolling back to {fcdate}...")
 
    # convert start_lt to leadtime if dayofweek
    start_lt = argument_output.convert_dayofweek_to_leadtime(fcdate, start_lt)

    # if leadtime_hour is set, no aggregation!
    if leadtime_hour:
        aggregation_switch = False
    else:
        aggregation_switch = True

    # Get parameters
    leveltype, plevs, webapi_param, ecds_varname, origin_id, leadtime_hour, fc_enslags = (
        argument_output.check_and_output_all_fc_arguments(
            variable,
            model,
            fcdate,
            bbox_bounds,
            data_format,
            grid_for_request,
            plevs,
            leadtime_hour,
            start_lt,
            end_lt,
            period,
            fc_enslags=0
        )
    )

    if rf_enslags is None:
        rf_enslags = argument_output.output_hc_lags(origin_id, fcdate)

    # Filename construction
    if filename is None:
        plev_str = ""
        if plevs is not None:
            plevs = [plevs] if isinstance(plevs, int) else plevs
            if len(plevs) == 1:
                plev_str = f"_{plevs[0]}hPa"
            else:
                plev_str = f"_{plevs[0]}-{plevs[-1]}hPa"

        if country_name:
            filename = f"{variable}_{model}_{fcdate}{plev_str}_{country_name.strip().lower().replace(' ', '')}_hc"
        elif region_name:
            filename = f"{variable}_{model}_{fcdate}{plev_str}_{region_name}_hc"
        else:
            north, west, south, east = bbox_bounds
            bounds_str = (
                f"{format_coord(north, lat=True)}_{format_coord(west, lat=False)}_"
                f"{format_coord(south, lat=True)}_{format_coord(east, lat=False)}"
            )
            filename = f"{variable}_{model}_{fcdate}{plev_str}_{bounds_str}_hc"

    # Add extension
    filename_save = filename
    ext = ".nc" if data_format.lower() == "netcdf" else ".grib"
    if not filename_save.endswith(ext):
        filename_save = f"{filename_save}{ext}"

    # Ensure save directory
    if data_save_dir is not None:
        os.makedirs(data_save_dir, exist_ok=True)
        filename_save = os.path.join(data_save_dir, os.path.basename(filename_save))

    print("[DEBUG] Hindcast download request")
    print(f"   Model               : {model}")
    print(f"   Target grid         : {grid}")
    print(f"   Variable            : {variable}")
    print(f"   Pressure levels     : {plevs}")
    print(f"   Forecast date       : {fcdate}")

    if country_name is not None:
        print(f"   Requested country   : {country_name}")
    elif region_name is not None:
        print(f"   Requested region    : {region_name}")

    print(f"   Requested bbox      : {original_bbox_bounds}")
    print(f"   Selected bbox       : {bbox_bounds}")
    print(f"   Output file         : {filename_save}")

    # Skip download if file exists
    if os.path.exists(filename_save) and not overwrite:
        print(f"[INFO] File already exists: {filename_save}, skipping download.")
        return filename_save

    # Downstream request code expects path without .nc at this stage
    filename__save = filename_save
    if filename_save.endswith(".nc"):
        filename_save = filename_save[:-3]

    if verbose:
        print(f"[INFO] Downloading {variable} (plevs={plevs}) for {country_name or region_name or bbox_bounds}")
        print(f"[INFO] Saving as {filename_save}")

    try:
        if variable != 'TC_TRACKS':
            if verbose:
                ecdsAPI_requests.request_hindcast(fcdate,origin_id,grid_for_request,variable,bbox_bounds,data_format,
                                                      webapi_param,leadtime_hour,period,leveltype,filename_save,plevs,
                                                      rf_enslags,rf_years,aggregation_switch,fc_time=fc_time,cleanup=cleanup)
            else:
                with SuppressOutput():
                    ecdsAPI_requests.request_hindcast(fcdate,origin_id,grid_for_request,variable,bbox_bounds,data_format,
                                                      webapi_param,leadtime_hour,period,leveltype,filename_save,plevs,
                                                      rf_enslags,rf_years,aggregation_switch,fc_time=fc_time,cleanup=cleanup)
        elif variable == 'TC_TRACKS':
            if verbose:
                download_S2Stc_tracks.download_reforecast_TCtracks(
                    fcdate,
                    model,
                    origin_id,
                    leadtime_hour,
                    filename_save,
                    rf_enslags,
                    rf_years,
                    fc_time
                )
            else:
                with SuppressOutput():
                    download_S2Stc_tracks.download_reforecast_TCtracks(
                        fcdate,
                        model,
                        origin_id,
                        leadtime_hour,
                        filename_save,
                        rf_enslags,
                        rf_years,
                        fc_time
                    )
    except Exception as e:
        print(f"[ERROR] Download failed for {filename_save}")
        raise

    return filename__save
