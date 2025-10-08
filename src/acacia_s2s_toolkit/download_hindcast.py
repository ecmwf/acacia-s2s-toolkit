# download sub-seasonal reforecast from S2S Database
from acacia_s2s_toolkit import argument_check, argument_output, webAPI_requests
import os
import sys
import datetime

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

def download_hindcast(model,
                         variable,
                         fcdate=None,
                         plevs=None,
                         location_name=None,
                         bbox_bounds=[90, -180, -90, 180],
                         filename=None,
                         data_save_dir=None,
                         data_format="netcdf",
                         grid="1.5/1.5",
                         leadtime_hour=None,
                         rf_years=None,
                         rf_enslags=None,
                         overwrite=False,
                         verbose=True):

    """
    Overarching function that will download hindcast data from ECDS.
    """

    # Domain bounds mapping
    DOMAIN_BOUNDS = {"ethiopia":   [15, 33, 3, 48],
                      "kenya":      [5, 33, -5, 42],
                      "madagascar": [-12, 43, -26, 51],
                      "eastafrica": [25, 10, -13, 55]}

    def match_domain_from_bbox_bounds(bbox_bounds):
        for name, bounds in DOMAIN_BOUNDS.items():
            if list(map(float, bounds)) == list(map(float, bbox_bounds)):
                return name
        return None

    def format_coord(value, lat=True):
        hemi = "N" if lat and value >= 0 else "S" if lat else "E" if value >= 0 else "W"
        return f"{abs(value)}{hemi}"

    # Domain overrides bbox_bounds
    if location_name is not None:
        cname =location_name.lower()
        if cname not in DOMAIN_BOUNDS:
            raise ValueError(f"Unsupportedlocation_name '{location_name}'. Choose from {list(DOMAIN_BOUNDS)}.")
        bbox_bounds = DOMAIN_BOUNDS[cname]
    else:
        cname = match_domain_from_bbox_bounds(bbox_bounds)
        if cname is not None:
           location_name = cname

    # Date handling with rollback to get the latest available forecast
    if fcdate is None:
        fcdate = datetime.datetime.utcnow().strftime("%Y%m%d")
  
    # output origin_id here
    model = model.upper() if any(c.islower() for c in model) else model
    origin_id = argument_output.output_originID(model,fcdate)

    while True:
        try:
            argument_check.check_fcdate(fcdate, origin_id)  # validate date
            break
        except ValueError:
            old_date = fcdate
            fcdate = (
                datetime.datetime.strptime(fcdate, "%Y%m%d")
                - datetime.timedelta(days=1)
            ).strftime("%Y%m%d")
            if verbose:
                print(f"[INFO] {old_date} not valid, rolling back to {fcdate}...")

    # Get parameters
    leveltype, plevs, webapi_param, ecds_varname, origin_id, leadtime_hour, fc_enslags = (argument_output.check_and_output_all_fc_arguments(variable, model, fcdate, bbox_bounds, data_format, grid, plevs, leadtime_hour, fc_enslags=0))

    print("[DEBUG] Download request details:")
    print(f"   Variable    : {variable}")
    print(f"   Domain     :  {location_name}")
    print(f"   BBox Bounds : {bbox_bounds}")
    print(f"   Forecast Date (fcdate): {fcdate}")
    print(f"   Pressure lvls: {plevs}")
    print(f"   Model       : {model}")
    print(f"   Origin ID   : {origin_id}")
    print(f"   Data format : {data_format}")
    print(f"   Grid        : {grid}")
    print(f"   Save Dir    : {data_save_dir}")
    print(f"   Filename    : {filename}")

    if rf_enslags == None:
        rf_enslags = argument_output.output_hc_lags(origin_id, fcdate)
    rf_model_date, rf_years = argument_output.check_and_output_all_hc_arguments(variable, origin_id, fcdate, rf_years)

    # Filename construction
    if filename is None:
        plev_str = ""
        if plevs is not None:
            plevs = [plevs] if isinstance(plevs, int) else plevs
            if len(plevs) == 1:
                plev_str = f"_{plevs[0]}hPa"
            else:
                plev_str = f"_{plevs[0]}-{plevs[-1]}hPa"

        if location_name:
            filename = f"{variable}_{model}_{fcdate}{plev_str}_{location_name}_hc"
        else:
            north, west, south, east = bbox_bounds
            bounds_str = (
                f"{format_coord(north, lat=True)}_{format_coord(west, lat=False)}_"
                f"{format_coord(south, lat=True)}_{format_coord(east, lat=False)}"
            )
            filename = f"{variable}_{model}_{fcdate}{plev_str}_{bounds_str}_hc"


    # Add extension
    filename_save = filename  # reassign var name as ther are intermediate file names saved
    ext = ".nc" if data_format.lower() == "netcdf" else ".grib"
    if not filename_save.endswith(ext):
        filename_save = f"{filename_save}{ext}"

    # Ensure save directory
    if data_save_dir is not None:
        os.makedirs(data_save_dir, exist_ok=True)
        filename_save = os.path.join(data_save_dir, os.path.basename(filename_save))

    # Skip download if file exists
    if os.path.exists(filename_save) and not overwrite:
        print(f"[INFO] File already exists: {filename_save}, skipping download.")
        return filename_save

    # Request download
    filename_save = filename_save[:-3] #drop the .nc extension

    # Print clean info
    if verbose:
        print(f"[INFO] Downloading {variable} (plevs={plevs}) for {location_name or bbox_bounds}")
        print(f"[INFO] Saving as {filename_save}")

    # Request with suppression logic
    # print(">>>> DEBUG PLEVS GOING TO REQUEST:", plevs)
    try:
        if verbose:
            webAPI_requests.request_hindcast(
                fcdate, origin_id, grid, variable, bbox_bounds, data_format, webapi_param,
                leadtime_hour, leveltype, filename_save, plevs, rf_enslags, rf_years
            )
        else:
            with SuppressOutput():
                webAPI_requests.request_hindcast(
                    fcdate, origin_id, grid, variable, bbox_bounds, data_format, webapi_param,
                    leadtime_hour, leveltype, filename_save, plevs, rf_enslags, rf_years
                )
    except Exception as e:
        # Re-raise but ensure logs aren't hidden if debugging
        print(f"[ERROR] Download failed for {filename_save}")
        raise

    return filename_save



