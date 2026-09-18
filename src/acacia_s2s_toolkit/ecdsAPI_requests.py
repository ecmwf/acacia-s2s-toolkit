# SPDX-FileCopyrightText: 2024 European Centre for Medium-Range Weather Forecasts (ECMWF)
# SPDX-License-Identifier: Apache-2.0

# script containing all relevant code for producing ecdsAPI requests.
from acacia_s2s_toolkit import argument_output, merge_lag_ensemble
import numpy as np
import os
import eccodes as ec
import xarray as xr
from datetime import datetime, timedelta
import subprocess
import cdsapi
import glob
from pathlib import Path
import acacia_s2s_toolkit
import json

def get_ecds_client():
    os.environ["CDSAPI_RC"] = os.path.expanduser("~/.cdsapirc.ecds")
    return cdsapi.Client()

def cleanup_patterns(*patterns):
    for pattern in patterns:
        for path_str in glob.glob(pattern):
            path = Path(path_str)
            if path.is_file():
                path.unlink()

def create_initial_ecdsAPI_request(fcdate,grid,area,origin,webapi_param,leadtimes):
    request_dict = {
            "class": "s2",
            "date": f"{fcdate}",
            "expver": "prod",
            "grid": f"{grid}",
            "levtype": "sfc",
            "origin": f"{origin}",
            "param": f"{webapi_param}",
            "step": f"{leadtimes}",
            "time": "00:00:00",
            "stream": "enfo",
            "type": "cf"
            }

    # add area component
    area_formatted = '/'.join(str(x) for x in area)
    request_dict['area'] = f"{area_formatted}"

    return request_dict

def request_forecast(fcdate,origin,grid,variable,area,data_format,webapi_param,leadtime_hour,period,leveltype,filename,plevs,fc_enslags,aggregation_switch,cleanup=True):
    # import registration detailis
    client = get_ecds_client()
    dataset = "s2s-forecasts"
    # to enable lagged ensemble, loop through requested ensembles
    for lag in np.atleast_1d(fc_enslags):
        lag = int(lag)
        leadtimes, convert_fcdate = argument_output.output_formatted_leadtimes(leadtime_hour,fcdate,variable,origin,period=period,lag=lag,fc_enslags=fc_enslags) # you need to know new fcdate, but also appropriate leadtimes so all are forecasting same period
        # create initial control request
        print (f'leadtimes going in {leadtimes} at lag {lag}')
        request_dict = create_initial_ecdsAPI_request(convert_fcdate,grid,area,origin,webapi_param,leadtimes)

        # change components of request based on level type, and grid
        # if grid doesn't equal '1.5/1.5', add 'repres' dictionary item which sets the requested representation, in this case, 'll'=latitude/longitude.
        if grid != '1.5/1.5':
            # add repres
            request_dict['repres'] = 'll'

        # if a pressure level type is selected, just need to change levtype and add list of pressure levels.
        if leveltype == 'pressure':
            request_dict['levtype'] = 'pl'
            # convert plevs
            plevels = '/'.join(str(x) for x in plevs)
            request_dict['levelist'] = f"{plevels}"

        # specific change needed for pv
        if variable == 'pv':
            request_dict['levtype'] = 'pt'
            request_dict['levelist'] = '320'

        # retrieve the control forecast
        target=f'{filename}_control_{lag}'
        client.retrieve(dataset,request_dict,target)

        # then download perturbed. change type of forecast, add number of ensemble members, and change target filename
        request_dict['type'] = 'pf'

        target = f'{filename}_perturbed_{lag}' 
        client.retrieve(dataset,request_dict,target)

        # once requesting control and perturbed forecast, combine the two.
        # set forecast type in control to pf (perturbed forecast).
        set_cf_to_pf(f'{filename}_control_{lag}',f'{filename}_control2_{lag}')
       
        # get variable resolution
        time_resolution = argument_output.get_timeresolution(variable)

        if origin == 'rjtd' and leadtimes.startswith('0') and ('accumulated' in time_resolution):
            print ('need to add zero time')
            add_zero_time(f'{filename}_control2_{lag}',f'{filename}_controlZEROADDED_{lag}')
            add_zero_time(f'{filename}_perturbed_{lag}',f'{filename}_perturbedZEROADDED_{lag}')
            control_fn = f'{filename}_controlZEROADDED_{lag}'
            pert_fn = f'{filename}_perturbedZEROADDED_{lag}'
        else:
            control_fn = f'{filename}_control2_{lag}'
            pert_fn = f'{filename}_perturbed_{lag}'

        # merge both control and perturbed forecast
        cmd = ["cdo","-O","merge",control_fn,pert_fn,f"{filename}_allens_{lag}",]
        result = subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        if result.returncode != 0:
            print(result.stderr)
            raise subprocess.CalledProcessError(result.returncode, cmd, stderr=result.stderr)

    # create new 'member' dimension based on same date. For instance, 5 members per date and three initialisations used
    # smae process following even with one forecast initialisation date to ensure same structure for all output. 
    combined_forecast = merge_lag_ensemble.merge_all_ens_members(f'{filename}',leveltype)
    
    # addition to deaccumulate accumulation field or average instantaneous or daily fields.
    # if accumulation field, take a difference
    # Convention:
    # time coordinate always represents the START of the period
    # represented by each value.
    if aggregation_switch:
        time_resolution = argument_output.get_timeresolution(variable)
        time_label='time label denotes start of period'
        if 'accumulated' in time_resolution:
            start_times = combined_forecast.time.isel(time=slice(0, -1))
            combined_forecast = combined_forecast.diff(dim='time')
            combined_forecast = combined_forecast.assign_coords(time=start_times)
        else:
            # if not accumulated, work out average field, like weekly averages.
            n_days = int(period[:-1])  # e.g. 7 for '7D'
            # trim to complete periods
            n_complete = (combined_forecast.sizes['time'] // n_days) * n_days
            # Save start times before aggregation
            start_times = combined_forecast.time.isel(time=slice(0, n_complete, n_days))
            
            combined_forecast = (combined_forecast.isel(time=slice(0, n_complete)).coarsen(time=n_days, boundary='trim').mean())
            
            # Force time coordinate to start of averaging period
            combined_forecast = combined_forecast.assign_coords(time=start_times)
    else:
        time_label='no change made to variable timing'

    metadata = {
            'Conventions': 'CF-1.8',
                    'title': f'{origin} Sub-seasonal Forecast',
                    'institution': 'ECMWF',
                    'source': 'Downloaded via acacia_s2s_toolkit',
                    'history': 'Downloaded via acacia_s2s_toolkit',
                    'toolkit': 'acacia_s2s_toolkit',
                    'toolkit_version': acacia_s2s_toolkit.__version__,
                    'forecast_initialisation_date': str(fcdate),
                    'origin': origin,
                    'grid': grid,
                    'variable': variable,
                    'leadtime_hour': ','.join(map(str, np.atleast_1d(leadtime_hour))),
                    'period': period,
                    'leveltype': leveltype,
                    'timelabel': time_label,
                    'pressure_levels': (
                        '' if plevs is None
                        else ','.join(map(str, np.atleast_1d(plevs)))
                    ),
                    'lag_ensemble_days': ','.join(
                        map(str, np.atleast_1d(fc_enslags))
                    ),
                    'aggregation_applied': str(aggregation_switch),
                    'data_format': data_format,
            }

    combined_forecast.attrs.update(metadata)
    
    for var in combined_forecast.data_vars:
        combined_forecast[var].attrs.update(metadata)

    combined_forecast.to_netcdf(f'{filename}.nc')

    # remove previous files
    if cleanup:
        cleanup_patterns(f"{filename}_control*",f"{filename}_perturbed*",f"{filename}_allens*",)  

def request_hindcast(fcdate,origin,grid,variable,area,data_format,webapi_param,leadtime_hour,period,leveltype,filename,plevs,rf_enslags,rf_years,aggregation_switch,fc_time=True,cleanup=True):
    # to enable lagged ensemble, loop through requested ensembles
    # import registration details
    client = get_ecds_client()
    dataset = "s2s-reforecasts"  
    print (rf_enslags)
    for lag in np.atleast_1d(rf_enslags):
        lag = int(lag)
        # convert fcdate
        lagged_fcdate = datetime.strptime(fcdate, '%Y%m%d')+timedelta(days=lag) # work out what the lagged fcdate is.
        convert_fcdate = lagged_fcdate.strftime('%Y%m%d') # convert that date to YYYYMMDD format

        rf_model_date, rfyears = argument_output.check_and_output_all_hc_arguments(variable,origin,convert_fcdate,rf_years) # get the reforecast model date version plus the number of reforecast years

        leadtimes, lag_fcdate_dashed_format = argument_output.output_formatted_leadtimes(leadtime_hour,convert_fcdate,variable,origin,period=period) # get the appropriate leadtimes plus the convert fcdate. For reforecast, the lag is set to zero as forecast date has already changed, additionally fc_enslags=0 as you always want full series (i.e. no trimming).

        print (leadtimes)

        # create initial control request
        request_dict = create_initial_ecdsAPI_request(lag_fcdate_dashed_format,grid,area,origin,webapi_param,leadtimes)

        # use correct reforecast model date
        request_dict['date'] = f"{rf_model_date}"

        # download reforecast, so change stream
        request_dict['stream'] = f"enfh"

        request_dict['hyear'] = [str(year) for year in rfyears]
        request_dict['hmonth'] = convert_fcdate[4:6]
        request_dict['hday']   = convert_fcdate[6:]

        # change components of request based on level type, and grid
        # if grid doesn't equal '1.5/1.5', add 'repres' dictionary item which sets the requested representation, in this case, 'll'=latitude/longitude.
        if grid != '1.5/1.5':
            # add repres
            request_dict['repres'] = 'll'

        # if a pressure level type is selected, just need to change levtype and add list of pressure levels.
        if leveltype == 'pressure':
            request_dict['levtype'] = 'pl'
            # convert plevs
            plevels = '/'.join(str(x) for x in plevs)
            request_dict['levelist'] = f"{plevels}"

        # specific change needed for pv
        if variable == 'pv':
            request_dict['levtype'] = 'pt'
            request_dict['levelist'] = '320'

        # retrieve the control forecast
        target=f'{filename}_control_{lag}'
        client.retrieve(dataset,request_dict,target)

        # then download perturbed. change type of forecast, add number of ensemble members, and change target filename
        request_dict['type'] = 'pf'

        target=f"{filename}_perturbed_{lag}"
        client.retrieve(dataset,request_dict,target)

        # once requesting control and perturbed forecast, combine the two.
        # set forecast type in control to pf (perturbed forecast).
        set_cf_to_pf(f'{filename}_control_{lag}',f'{filename}_control2_{lag}')
        
        # get variable resolution
        time_resolution = argument_output.get_timeresolution(variable)

        if origin == 'rjtd' and leadtimes.startswith('0') and ('accumulated' in time_resolution):
            print ('need to add zero time')
            add_zero_time(f'{filename}_control2_{lag}',f'{filename}_controlZEROADDED_{lag}')
            add_zero_time(f'{filename}_perturbed_{lag}',f'{filename}_perturbedZEROADDED_{lag}')
            control_fn = f'{filename}_controlZEROADDED_{lag}'
            pert_fn = f'{filename}_perturbedZEROADDED_{lag}'
        else:
            control_fn = f'{filename}_control2_{lag}'
            pert_fn = f'{filename}_perturbed_{lag}'

        # Merge control and perturbed forecast members into one file.
        # We suppress routine CDO warning noise, but still raise on real failures.
        cmd = ["cdo","-O","merge",control_fn,pert_fn,f"{filename}_allens_{lag}",]
        result = subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        if result.returncode != 0:
            print(result.stderr)
            raise subprocess.CalledProcessError(result.returncode, cmd, stderr=result.stderr)

        # shift the time so all reforecasts have the same time values
        if fc_time:
            shift_day_value = lag*-1
        else:
            shift_day_value = 0 
        # only shift the time, if you want a 'forecast-based' time.
        rf_shifttime(f'{filename}_allens_{lag}',f'{filename}_timeshifted_allens_{lag}',lag,shift_days=shift_day_value)

    # create new 'member' dimension based on same date. For instance, 5 members per date and three initialisations used
    # same process following even with one forecast initialisation date to ensure same structure for all output. 
    combined_forecast = merge_lag_ensemble.merge_all_ens_hindcasts(f'{filename}_timeshifted',leveltype)

    # addition to deaccumulate accumulation field or average instantaneous or daily fields.
    # if accumulation field, take a difference
    # Convention:
    # time coordinate always represents the START of the period
    # represented by each value.
    if aggregation_switch:
        time_resolution = argument_output.get_timeresolution(variable)
        time_label='time label denotes start of period'
        if 'accumulated' in time_resolution:
            start_times = combined_forecast.time.isel(time=slice(0, -1))
            combined_forecast = combined_forecast.diff(dim='time')
            combined_forecast = combined_forecast.assign_coords(time=start_times)
        else:
            # if not accumulated, work out average field, like weekly averages.
            n_days = int(period[:-1])  # e.g. 7 for '7D'
            # trim to complete periods
            n_complete = (combined_forecast.sizes['time'] // n_days) * n_days
            # Save start times before aggregation
            start_times = combined_forecast.time.isel(time=slice(0, n_complete, n_days))

            combined_forecast = (combined_forecast.isel(time=slice(0, n_complete)).coarsen(time=n_days, boundary='trim').mean())

            # Force time coordinate to start of averaging period
            combined_forecast = combined_forecast.assign_coords(time=start_times)
    else:
        time_label='no change made to variable timing'

    # before saving, put in request attributes
    metadata = {'Conventions': 'CF-1.8',
                    'title': f'{origin} Sub-seasonal Reforecast',
                    'institution': 'ECMWF',
                    'source': 'Downloaded via acacia_s2s_toolkit',
                    'history': 'Downloaded via acacia_s2s_toolkit',
                    'toolkit': 'acacia_s2s_toolkit',
                    'toolkit_version': acacia_s2s_toolkit.__version__,
                    'forecast_initialisation_date': str(fcdate),
                    'origin': origin,
                    'grid': grid,
                    'variable': variable,
                    'leadtime_hour': ','.join(map(str, np.atleast_1d(leadtime_hour))),
                    'period': period,
                    'leveltype': leveltype,
                    'timelabel': time_label,
                    'lag_ensemble_days': ','.join(map(str, np.atleast_1d(rf_enslags))),
                    'reforecast_years': ','.join(map(str, np.atleast_1d(rf_years))),
                    'fctime': str(fc_time),
                    'pressure_levels': (
                        '' if plevs is None
                        else ','.join(map(str, np.atleast_1d(plevs)))
                    ),
                    'lag_ensemble_days': ','.join(
                        map(str, np.atleast_1d(rf_enslags))
                    ),
                    'aggregation_applied': str(aggregation_switch),
                    'data_format': data_format,}
    
    combined_forecast.attrs.update(metadata)

    for var in combined_forecast.data_vars:
        combined_forecast[var].attrs.update(metadata)
    
    combined_forecast.to_netcdf(f'{filename}.nc')

    # remove previous files  
    if cleanup:
        cleanup_patterns(f"{filename}_control*",f"{filename}_perturbed*",f"{filename}_allens*",f'{filename}_timeshifted')

def rf_shifttime(fn,output_fn,lag,shift_days=0):
    orig_hc = xr.open_dataset(fn,engine='cfgrib')
    if np.size(orig_hc['step'].values) > 1: # different option depending on size of step variable.
        orig_hc_new = orig_hc.stack(valid_time=("time","step")).drop_vars(["time","step"]).assign_coords(valid_time=orig_hc.valid_time.values.ravel()) # have a valid_time coordinate instead
    else:
        orig_hc_new = orig_hc.swap_dims({'time':'valid_time'})
        orig_hc_new = orig_hc_new.drop_vars("time")

    orig_hc_new = orig_hc_new.assign_coords(
            valid_time=orig_hc_new.valid_time+np.timedelta64(shift_days,'D')
            )
    orig_hc_new = orig_hc_new.rename({'valid_time':'time'})
    orig_hc_new = orig_hc_new.assign_coords(lag=lag)
    orig_hc_new.to_netcdf(output_fn)

def set_cf_to_pf(input_file, output_file):
    # Open input file
    with open(input_file, 'rb') as fin,open(output_file,'wb') as fout:
        while True:
            gid = ec.codes_grib_new_from_file(fin)
            if gid is None:
                break
            # Set type from 'cf' to 'pf'
            ec.codes_set(gid, 'type', 'pf')
            ec.codes_write(gid,fout)
            ec.codes_release(gid)

def add_zero_time(input_file, output_file):
    first_messages = []
    with open(input_file, 'rb') as fin:
        first_endstep = None
        while True:
            gid = ec.codes_grib_new_from_file(fin)
            if gid is None:
                break
            endstep = ec.codes_get(gid, 'endStep')

            if first_endstep is None:
                first_endstep = endstep

            if endstep == first_endstep:
                first_messages.append(ec.codes_clone(gid))

            ec.codes_release(gid)

    with open(output_file, 'wb') as fout:
        # Write synthetic 0-0 fields first
        for gid in first_messages:
            values = ec.codes_get_values(gid)
            values[:] = 0.0
            ec.codes_set_values(gid, values)

            ec.codes_set(gid, 'startStep', 0)
            ec.codes_set(gid, 'endStep', 0)

            ec.codes_write(gid, fout)
            ec.codes_release(gid)

        # Now append original file
        with open(input_file, 'rb') as fin:
            while True:
                gid = ec.codes_grib_new_from_file(fin)
                if gid is None:
                    break
                ec.codes_write(gid, fout)
                ec.codes_release(gid)


