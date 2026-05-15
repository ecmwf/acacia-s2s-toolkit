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
__all__=["biascorrection_qqmapping", "biascorrection_meanvariance"]


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




def qm_core(hc_1d, ob_1d, x_1d):
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


def biascorrection_simple_qqmapping(forecast,hindcast,observed):
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
        Forecast data with dimensions (lead_time, lat, lon, init_date, member).
    hindcast : xarray.DataArray
        Hindcast data with dimensions (lead_time, lat, lon, init_date, member).
    observed : xarray.DataArray
        Observed data with dimensions (lead_time, lat, lon, init_date).

    Returns
    -------
    forecast_adjusted : xarray.DataArray
        Bias-corrected forecast, same shape as input forecast.
    hindcast_adjusted : xarray.DataArray
        Bias-corrected hindcast, same shape as input hindcast.

    Notes
    -----
    Member and init_date dimensions are stacked into a single sample dimension
    before applying the quantile mapping, to maximise the sample size used
    for estimating the transfer function.

    The core quantile mapping is performed by a function applied pointwise
    over lat/lon using `xr.apply_ufunc` with dask parallelization support.
    """
    
    #copy of original arrays to store results into
    hindcast_adjusted=hindcast.copy().transpose("lead_time", "lat", "lon", "init_date", "member")
    forecast_adjusted=forecast.copy().transpose("lead_time", "lat", "lon", "init_date", "member")

    #iterating through lead times
    for lead_time in hindcast.lead_time:

        hc=hindcast_adjusted.sel(lead_time=lead_time)
        fc=forecast_adjusted.sel(lead_time=lead_time)
        ob=observed.sel(lead_time=lead_time)


        #pooling across all init_dates
        hc_sample = (
            hc.stack(sample_hc=("member", "init_date"))
        )
        
        # save the index before dropping
        hc_sample_index = hc_sample.sample_hc

        # drop for apply_ufunc
        hc_input = hc_sample.reset_index("sample_hc", drop=True)

        #pooling across all init_dates
        fc_sample = (
            fc.stack(sample_fc=("member", "init_date"))
        )
        
        # save the index before dropping
        fc_sample_index = fc_sample.sample_fc
        
        # drop for apply_ufunc
        fc_input = fc_sample.reset_index("sample_fc", drop=True)
        
        #pooling across all init_dates
        ob_sample = (
            ob.stack(sample_ob=("init_date",))
        )
                
        # drop for apply_ufunc
        ob_input = ob_sample.reset_index("sample_ob", drop=True)

        

        # adjusting hindcast
        hcadj=xr.apply_ufunc(
            qm_core,
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

        # adjusting forecast
        fcadj=xr.apply_ufunc(
            qm_core,
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

        # restore index and unstack
        hcadj = hcadj.assign_coords(sample_hc=hc_sample_index)
        hcadj = hcadj.unstack("sample_hc")
        hcadj = hcadj.transpose(*hc.dims)

        fcadj = fcadj.assign_coords(sample_fc=fc_sample_index)
        fcadj = fcadj.unstack("sample_fc")
        fcadj = fcadj.transpose(*fc.dims)
        
        
        #injecting adjusted data into
        hindcast_adjusted.loc[dict(lead_time=lead_time)]=hcadj.data
        forecast_adjusted.loc[dict(lead_time=lead_time)]=fcadj.data

        #adjusting sequence of dimensions
        forecast_adjusted=forecast_adjusted.transpose(*hindcast.dims)
        hindcast_adjusted=hindcast_adjusted.transpose(*forecast.dims)
            
    return forecast_adjusted, hindcast_adjusted

