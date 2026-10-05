# SPDX-FileCopyrightText: 2024 European Centre for Medium-Range Weather Forecasts (ECMWF)
# SPDX-License-Identifier: Apache-2.0

import xarray as xr
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import datetime
import os,sys,glob
import xesmf as xe
import pooch


#this is for readthedocs to work correctly. These packages cannot be installed by pip, so one has to mock import them
autodoc_mock_imports = []

#this determines with functions will be publicly visible in the installed package
__all__=["biascorrection"]


#######################################################################################

#
# helper functions
#
#######################################################################################



VERBOSE = True

def set_verbose(v):
    global VERBOSE
    VERBOSE = v
    print("logging is {}".format(v))

def _log(msg, force=False):
    if VERBOSE | force:
        print(msg)
        

def biascorrection_meanvariance(forecast,hindcast,observed):
    """
    Apply mean and variance bias correction to forecast and hindcast data.

    For each lead time, adjusts the mean and variance of the hindcast and
    forecast to match those of the observed data. The correction is computed
    from the hindcast/observation pair and then applied to both hindcast and
    forecast.

    Parameters
    ----------
    forecast : xarray.DataArray
        Forecast data with dimensions (lead_time, member, ...).
    hindcast : xarray.DataArray
        Hindcast data with dimensions (lead_time, member, init_date, ...).
    observed : xarray.DataArray
        Observed data with dimensions (lead_time, init_date, ...).

    Returns
    -------
    forecast_adjusted : xarray.DataArray
        Bias-corrected forecast, same shape as input forecast.
    hindcast_adjusted : xarray.DataArray
        Bias-corrected hindcast, same shape as input hindcast.

    Notes
    -----
    The correction follows:
        adjusted = ((x - mean(x)) * sqrt(var(obs) / var(hindcast))) + mean(obs)

    Hindcast variance is computed (separately for each lead time, of course) over 
    both member and init_date dimensions.
    Grid points where hindcast variance is zero are masked (set to NaN) to
    avoid division by zero.
    """
    
    import warnings

    #warnings off because they are thrown when std is calculated on array with all nans
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        
        #copy of original arrays to store results into
        hindcast_adjusted=hindcast.copy()
        forecast_adjusted=forecast.copy()

        #iterating through lead times
        for lead_time in hindcast.lead_time:

            #selecting lead time
            hc=hindcast.sel(lead_time=lead_time)
            fc=forecast.sel(lead_time=lead_time)
            ob=observed.sel(lead_time=lead_time)

            #calculating variance, or actually standard deviation
            hcsd=hc.std(["member","init_date"],ddof=0)
            
            #making sure no zeros
            hcsd = hcsd.where(hcsd != 0)

            #calculating variance adjustment
            std_correction=ob.std(["init_date"], ddof=0)/hcsd
            
            #adjusting hindcast    
            hcadj=((hc-hc.mean(["member","init_date"]))*std_correction)+ob.mean(["init_date"])

            #inserting adjusted data into the output array 
            hindcast_adjusted.loc[dict(lead_time=lead_time)]=hcadj.data

            #adjusting forecast
            fcadj=((fc-hc.mean(["member","init_date"]))*std_correction)+ob.mean(["init_date"])
            
            forecast_adjusted.loc[dict(lead_time=lead_time)]=fcadj.data
    return forecast_adjusted, hindcast_adjusted


from scipy.stats import gaussian_kde

#helper function for kde distribution fitting
def _kde_cdf_grid(sample, n_grid=2000, pad_factor=3):
    """Return (grid, cdf) for a smoothed CDF via KDE."""
    kde = gaussian_kde(sample)  # Scott's rule bandwidth by default
    std = sample.std()
    lo = sample.min() - pad_factor * std
    hi = sample.max() + pad_factor * std
    grid = np.linspace(lo, hi, n_grid)
    pdf_vals = kde(grid)
    cdf_vals = np.cumsum(pdf_vals)
    cdf_vals /= cdf_vals[-1]
    return grid, cdf_vals


# registry of available aggregation functions
BC_FUNCTIONS = {}

def register_bc(name):
    """Decorator to register an aggregation function under a name."""
    def wrapper(func):
        BC_FUNCTIONS[name] = func
        return func
    return wrapper




@register_bc("scaling")
def simple_scaling(hc_1d, ob_1d, x_1d):

    #simple correction of mean and variance
    
    #calculating variance, or actually standard deviation
    hcsd=hc_1d.std(ddof=0)
    
    #calculating variance adjustment
    std_correction=ob_1d.std(ddof=0)/hcsd
    
    #adjusting target
    fcadj=((x_1d-hc_1d.mean())*std_correction)+x_1d.mean()
    
    return fcadj

@register_bc("qm-kde")
def qm_core_kde(hc_1d, ob_1d, x_1d, n_grid=2000):
    hc_1d = hc_1d[~np.isnan(hc_1d)]
    ob_1d = ob_1d[~np.isnan(ob_1d)]

    if len(hc_1d) < 2 or len(ob_1d) < 2:
        return np.full_like(x_1d, np.nan)

    hc_grid, hc_cdf = _kde_cdf_grid(hc_1d, n_grid=n_grid)
    ob_grid, ob_cdf = _kde_cdf_grid(ob_1d, n_grid=n_grid)

    # x -> quantile via smoothed hindcast CDF
    p = np.interp(x_1d, hc_grid, hc_cdf, left=hc_cdf[0], right=hc_cdf[-1])

    # quantile -> obs value via smoothed obs CDF inverse
    result = np.interp(p, ob_cdf, ob_grid)
    #print(result)
    	
    return result
    
    
@register_bc("qm-ecdf")
def qm_core_ecdf(hc_1d, ob_1d, x_1d):

    # remove NaNs
    hc_1d = hc_1d[~np.isnan(hc_1d)]
    ob_1d = ob_1d[~np.isnan(ob_1d)]
    
    if len(hc_1d) == 0 or len(ob_1d) == 0:
        return np.full_like(x_1d, np.nan)

    hc_sorted = np.sort(hc_1d)
    ob_sorted = np.sort(ob_1d)
    
    q_hc = np.linspace(0, 1, len(hc_sorted))
    q_ob = np.linspace(0, 1, len(ob_sorted))
    
    p = np.interp(x_1d, hc_sorted, q_hc)
    
    return np.interp(p, q_ob, ob_sorted)

from scipy.stats import gamma


@register_bc("qm-gamma")
def qm_core_gamma(hc_1d, ob_1d, x_1d):
    hc_1d = hc_1d[~np.isnan(hc_1d)]
    ob_1d = ob_1d[~np.isnan(ob_1d)]

    if len(hc_1d) < 2 or len(ob_1d) < 2:
        return np.full_like(x_1d, np.nan)

    p0_hc = (hc_1d <= 0).mean()
    p0_ob = (ob_1d <= 0).mean()

    hc_pos = hc_1d[hc_1d > 0]
    ob_pos = ob_1d[ob_1d > 0]

    if len(hc_pos) < 2 or len(ob_pos) < 2:
        return np.full_like(x_1d, np.nan)

    hc_shape, hc_loc, hc_scale = gamma.fit(hc_pos, floc=0)
    ob_shape, ob_loc, ob_scale = gamma.fit(ob_pos, floc=0)

    result = np.zeros_like(x_1d, dtype=float)

    # step 1: get each x's quantile under HC's *mixed* CDF
    p_hc = np.where(
        x_1d <= 0,
        0.0,  # anything <=0 sits at/below HC's own zero mass
        p0_hc + (1 - p0_hc) * gamma.cdf(x_1d, hc_shape, loc=hc_loc, scale=hc_scale)
    )

    # step 2: values whose HC-quantile falls within obs's zero-mass -> 0
    is_zero = p_hc <= p0_ob
    result[is_zero] = 0.0

    # step 3: remaining values -> rescale into obs's positive-part quantile space
    pos_mask = ~is_zero
    if pos_mask.any():
        p_rescaled = (p_hc[pos_mask] - p0_ob) / (1 - p0_ob)
        p_rescaled = np.clip(p_rescaled, 0, 1)  # guard against float edge cases
        result[pos_mask] = gamma.ppf(p_rescaled, ob_shape, loc=ob_loc, scale=ob_scale)

    return result


    
def biascorrection(forecast,hindcast, observed, window_size=7, is_aggregated=False, method="qm-ecdf"):
    """
    Apply quantile-quantile mapping bias correction to forecast and hindcast data.
    
    For each lead time, maps the emiprical distribution of the hindcast and forecast
    to match the observed empirical distribution using quantile mapping. The transfer
    function is derived from the hindcast/observation pair and applied to
    both hindcast and forecast. This is simple quantile mapping based on emiprical 	
    distributions and without extension of tails, and thus by nature bias-corrected forecast 
    maxima/minima will not exceed these in observations.   
    
    Parameters
    ----------
    forecast : xarray.DataArray
        Forecast data with dimensions (lead_time, lat, lon, nominal_time, member).
    hindcast : xarray.DataArray
        Hindcast data with dimensions (lead_time, lat, lon, nominal_time, member).
    observed : xarray.DataArray
        Observed data with dimensions (lead_time, lat, lon, nominal_time).
    leadtime_window : int
        size of window over which data are grouped for bias correction
    is_aggregated: boolean
        whether data are already aggregated over windows. If True, leadtime_window of 1 is permitted.
    
    Returns
    -------
    forecast_bc : xarray.DataArray
        Bias-corrected forecast, same shape as input forecast.
    hindcast_bc : xarray.DataArray
        Bias-corrected hindcast, same shape as input hindcast.
    obs_bc : xarray.DataArray
        Observations in the same structure as bias-corrected hindcast.
    
    Notes
    -----
    Member and nominal_time dimensions are stacked into a single sample dimension
    before applying the quantile mapping, to maximise the sample size used
    for estimating the transfer function.
    
    The core quantile mapping is performed by a function applied pointwise
    over lat/lon using `xr.apply_ufunc` with dask parallelization support.
    
    
    """
    
    #minimum size of grouping window
    min_window_size=5
    
    
    # initial checks
    
    
    #checking if method is available
    if method not in BC_FUNCTIONS:
        raise ValueError(
            f"Unknown bias correction method '{method}'. "
            f"Available: {list(BC_FUNCTIONS)}"
        )
        
    #picking up requested method
    func = BC_FUNCTIONS[method]
        
    
    if is_aggregated:
        #if aggregated data
        if window_size!=1:
            raise ValueError(
                f"Aggregated data provided, and window size for aggregated data should be 1, got ({window_size}). Stopping..."
            )
    else:
        #if non-aggregated data
        if window_size<min_window_size:
            raise ValueError(
                f"Requested window size ({window_size}) is too small to process daily data. Minimum {min_window_size} required. Stopping..."
            )
    
    timevar=None
    for var in ["nominal_time","valid_time","time","init_time"]:
        if var in hindcast.coords:
            timevar=var
    if timevar is None:
            raise ValueError(
                f"Could not find time variable. should be one of time, init_time, valid_time, nominal_time. Stopping..."
            )        
    #copy of original arrays to store results into
    hindcast_adjusted=hindcast.copy().transpose("lead_time", "lat", "lon", timevar, "member")
    forecast_adjusted=forecast.copy().transpose("lead_time", "lat", "lon", timevar, "member")
    observed_adjusted=observed.copy().transpose("lead_time", "lat", "lon", timevar, "member")
    
    #getting some parameters for processing
    lead_time = (set(forecast_adjusted.lead_time.data) & set(hindcast_adjusted.lead_time.data))
    lead_time=np.array(list(lead_time))
    
    #splitting into windows
    window_idx = lead_time // window_size
    
    #number of windows
    n_windows = window_idx.max().item() + 1
    
    #number of full windows, i.e. with window_size datapoints
    n_full = (len(lead_time) // window_size) * window_size
    
    if n_full<len(lead_time):
        _log(f"Requested window size: {window_size}, data has {len(lead_time)} lead times. the last two windows will be processed as one")
        window_idx[window_idx == window_idx.max()] = np.partition(window_idx, -2)[-2]

    
    #trimming to full window
    n_lt=len(window_idx)
    
    forecast_trimmed = forecast_adjusted.isel(lead_time=slice(0, n_lt))
    hindcast_trimmed = hindcast_adjusted.isel(lead_time=slice(0, n_lt))
    observed_trimmed = observed.isel(lead_time=slice(0, n_lt))
    
    #trimming to full windows
    #window_idx=window_idx[0:n_full]
    lead_time=lead_time[0:n_lt]
    
    n_windows=max(window_idx)
    
    #iterating through lead times
    for w in np.unique(window_idx):
        mask=window_idx==w
        
        hc=hindcast_trimmed.isel(lead_time=mask)
        fc=forecast_trimmed.isel(lead_time=mask)
        ob=observed_trimmed.isel(lead_time=mask)
    
        #OBSERVATIONS
        #pooling across all init_dates
        ob_sample = (
            ob.stack(sample_ob=("member", timevar))
        )
                
        # drop for apply_ufunc
        ob_input = ob_sample.reset_index("sample_ob", drop=True)
    
        #HINDCAST     
        #pooling across all init_dates
        #this creates dimension sample_hc, but keeps member and nominal_time coordinates
        hc_sample = (
            hc.stack(sample_hc=("member", timevar))
        )
        
        # save the index before dropping
        hc_sample_index = hc_sample.indexes["sample_hc"]
    
        # drop unnecessary dimensions for apply_ufunc
        hc_input = hc_sample.reset_index("sample_hc", drop=True)
    
    
        # adjusting hindcast
        hcadj0=xr.apply_ufunc(
            func,
            hc_input,
            ob_input,
            hc_input,
            input_core_dims=[["sample_hc"], ["sample_ob"], ["sample_hc"]],
            output_core_dims=[["sample_hc"]],
            vectorize=True,
            dask="parallelized",
            output_dtypes=[hc.dtype],
            join="override",   
        )
    
        
        # restore index and unstack
        #we need to create coordinates object to accommodate multiindex (member, nominal_time)
        sample_hc_coords = xr.Coordinates.from_pandas_multiindex(hc_sample_index, 'sample_hc')
        hcadj = hcadj0.assign_coords(sample_hc_coords)
        hcadj = hcadj.unstack("sample_hc")
        hcadj = hcadj.transpose(*hc.dims)
    
        
        #FORECAST
        #pooling across all init_dates
        fc_sample = (
            fc.stack(sample_fc=("member", timevar))
        )
        
        # save the index before dropping
        fc_sample_index = fc_sample.sample_fc
        
        # drop for apply_ufunc
        fc_input = fc_sample.reset_index("sample_fc", drop=True)
        
    
        # adjusting forecast
        fcadj=xr.apply_ufunc(
            func,
            hc_input,
            ob_input,
            fc_input,
            input_core_dims=[["sample_hc"], ["sample_ob"], ["sample_fc"]],
            output_core_dims=[["sample_fc"]],
            vectorize=True,
            dask="parallelized",
            output_dtypes=[hc.dtype],
            join="override", 
        )
    
    
        fcadj = fcadj.assign_coords(sample_fc=fc_sample_index)
        fcadj = fcadj.unstack("sample_fc")
        fcadj = fcadj.transpose(*fc.dims)
        
        
        #injecting adjusted data back to the original array
        hindcast_trimmed.loc[dict(lead_time=mask)]=hcadj.data
        forecast_trimmed.loc[dict(lead_time=mask)]=fcadj.data
    
        #adjusting sequence of dimensions
        forecast_bc=forecast_trimmed.transpose(*hindcast.dims)
        hindcast_bc=hindcast_trimmed.transpose(*forecast.dims)

        
        return forecast_bc, hindcast_bc, observed_trimmed


