# download sub-seasonal forecast data from WMO lead centre
from acacia_s2s_toolkit import argument_check, argument_output
import numpy as np
import os
import xarray as xr
from datetime import datetime, timedelta

def webAPI_request_forecast(fcdate,origin,grid,variable,data_format,webapi_param,leadtime_hour,leveltype,filename,plevs,fc_enslags):
    from ecmwfapi import ECMWFDataServer
    server = ECMWFDataServer()

    # to enable lagged ensemble, loop through requested ensembles
    for lag in fc_enslags:
        # create new fcdate based on lag
        new_fcdate = datetime.strptime(fcdate, '%Y%m%d')+timedelta(days=lag)
        convert_fcdate = new_fcdate.strftime('%Y-%m-%d')

        # convert leadtimes 
        # is it an average field?
        time_resolution = argument_output.get_timeresolution(variable)
        # if an average field, use '0-24/24-48/48-72...'
        leadtime_hour_copy = leadtime_hour[:]

        # need to ensure correct selection of lead time given lag. Essentially all members should sample same forecast period. 
        max_lag = np.abs(np.min(fc_enslags))
        lag_minus_1 = lag*-1
        lag_end = (max_lag-lag_minus_1)*-1

        if time_resolution.startswith('aver'):
            if lag_end == 0:
                leadtime_hour_copy=leadtime_hour_copy[lag_minus_1:]
            else:
                leadtime_hour_copy=leadtime_hour_copy[lag_minus_1:lag_end]
            leadtimes='/'.join(f"{leadtime_hour_copy[i]}-{leadtime_hour_copy[i]+24}" for i in range(len(leadtime_hour_copy)-1))
        else: # instantaneous field
            nsteps_per_day = 4
            if lag_end == 0:
                leadtime_hour_copy=leadtime_hour_copy[lag_minus_1*nsteps_per_day:]
            else:
                leadtime_hour_copy=leadtime_hour_copy[lag_minus_1*nsteps_per_day:lag_end*nsteps_per_day]
            leadtimes = '/'.join(str(x) for x in leadtime_hour_copy)
        print (leadtimes)

        # create initial control request
        request_dict = {
            "dataset": "s2s",
            "class": "s2",
            "date": f"{convert_fcdate}",
            "expver": "prod",
            "grid": f"{grid}",
            "levtype": "sfc",
            "origin": f"{origin}",
            "param": f"{webapi_param}",
            "step": f"{leadtimes}",
            "time": "00:00:00",
            "stream": "enfo",
            "type": "cf",
            "target": f"{filename}_control_{lag}"
            }

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
        server.retrieve(request_dict)

        # then download perturbed. change type of forecast, add number of ensemble members, and change target filename
        request_dict['type'] = 'pf'
        # add model number (will not be needed for ECDSapi)
        num_pert_fcs = argument_output.get_num_pert_fcs(origin)
        pert_fcs = '/'.join(str(x) for x in np.arange(1,num_pert_fcs+1))
        request_dict['number'] = f"{pert_fcs}"
        request_dict['target'] = f"{filename}_perturbed_{lag}"

        server.retrieve(request_dict)

        # once requesting control and perturbed forecast, combine the two.
        # set forecast type in control to pf (perturbed forecast).
        os.system(f'grib_set -s type=pf -w type=cf {filename}_control_{lag} {filename}_control2_{lag}')
        # merge both control and perturbed forecast
        os.system(f'cdo merge {filename}_control2_{lag} {filename}_perturbed_{lag} {filename}_allens_{lag}')
    
    # create new 'member' dimension based on same date. For instance, 5 members per date and three initialisations used
    # smae process following even with one forecast initialisation date to ensure same structure for all output. 
    combined_forecast = merge_all_ens_members(f'{filename}')
    combined_forecast.to_netcdf(f'{filename}.nc')

    # remove previous files  
    os.system(f'rm {filename}_control* {filename}_perturbed* {filename}_allens*')

def merge_all_ens_members(filename):
    # open all ensemble members. drop step and time variables. Just use valid time.
    all_fcs = xr.open_mfdataset(f'{filename}_allens_*',engine='cfgrib',combine='nested',concat_dim='step') # open mfdataset but have step as a dimension
    all_fcs = all_fcs.drop_vars(['step','time'])
    all_fcs = all_fcs.rename({'valid_time':'time'})

    # make step == valid time
    if 'time' not in all_fcs.dims:
        all_fcs = all_fcs.swap_dims({'step':'time'}) # change step dimension to time

    member_based_fcs = []

    # go through every time stamp and make a dataset with a 'member' dimension that combines all that have the same time.
    for time, group in all_fcs.groupby('time'):
        member_stack = group.stack(member=('number','time'))
        member_stack = member_stack.assign_coords(member=np.arange(np.size(group['time'])*np.size(group['number'])))
        member_stack = member_stack.expand_dims(time=[time])
        member_based_fcs.append(member_stack)
    combined = xr.concat(member_based_fcs,dim='time')
    combined = combined.transpose('time','member','latitude','longitude')

    return combined 

def download_forecast(variable,model,fcdate,local_destination=None,filename=None,area=[90,-180,-90,180],data_format='netcdf',grid='1.5/1.5',plevs=None,leadtime_hour=None,fc_enslags=None):
    '''
    Overarching function that will download forecast data from ECDS.
    From variable - script will work out whether sfc or pressure level and ecds varname. If necessary will also compute leadtime_hour. 

    '''
    leveltype, plevs, webapi_param, ecds_varname, origin_id, leadtime_hour, fc_enslags = argument_output.check_and_output_all_arguments(variable,model,fcdate,area,data_format,grid,plevs,leadtime_hour,fc_enslags)

    if filename == None:
        filename = f'{variable}_{model}_{fcdate}_fc'

    if local_destination != None:
        filename = f'{local_destination}/{filename}'

    webAPI_request_forecast(fcdate,origin_id,grid,variable,data_format,webapi_param,leadtime_hour,leveltype,filename,plevs,fc_enslags)

    return None 

