# download sub-seasonal forecast data from WMO lead centre
from acacia_s2s_toolkit import argument_check, argument_output
import numpy as np
import os
import xarray as xr
from datetime import datetime, timedelta

def create_initial_webAPI_request(fcdate,grid,origin,webapi_param,leadtimes,filename):
    request_dict = {
            "dataset": "s2s",
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
            "type": "cf",
            "target": f"{filename}"
            }

    return request_dict

def webAPI_request_forecast(fcdate,origin,grid,variable,data_format,webapi_param,leadtime_hour,leveltype,filename,plevs,fc_enslags):
    from ecmwfapi import ECMWFDataServer
    server = ECMWFDataServer()

    # to enable lagged ensemble, loop through requested ensembles
    for lag in fc_enslags:
        leadtimes, convert_fcdate = argument_output.output_formatted_leadtimes(leadtime_hour,fcdate,variable,lag=lag,fc_enslags=fc_enslags)
        # create initial control request
        request_dict = create_initial_webAPI_request(convert_fcdate,grid,origin,webapi_param,leadtimes,f'{filename}_control_{lag}')

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
    combined_forecast = merge_all_ens_members(f'{filename}',leveltype)
    combined_forecast.to_netcdf(f'{filename}.nc')

    # remove previous files  
    os.system(f'rm {filename}_control* {filename}_perturbed* {filename}_allens*')

def webAPI_request_hindcast(fcdate,origin,grid,variable,data_format,webapi_param,leadtime_hour,leveltype,filename,plevs,rf_enslags,rf_years):
    from ecmwfapi import ECMWFDataServer
    server = ECMWFDataServer()

    # to enable lagged ensemble, loop through requested ensembles
    print (rf_enslags)
    for lag in rf_enslags:
        # convert fcdate
        lagged_fcdate = datetime.strptime(fcdate, '%Y%m%d')+timedelta(days=lag)
        convert_fcdate = lagged_fcdate.strftime('%Y%m%d')

        rf_model_date, rfyears = argument_output.check_and_output_all_hc_arguments(variable,origin,convert_fcdate,rf_years)
        
        leadtimes, convert_fcdate = argument_output.output_formatted_leadtimes(leadtime_hour,convert_fcdate,variable)
        print (leadtimes)        
    
        # create initial control request
        request_dict = create_initial_webAPI_request(convert_fcdate,grid,origin,webapi_param,leadtimes,f'{filename}_control_{lag}')

        # use correct reforecast model date
        request_dict['date'] = f"{rf_model_date}"

        # download reforecast, so change stream
        request_dict['stream'] = f"enfh"

        # create list of hdates
        hdates = argument_output.create_reforecast_dates(rfyears,convert_fcdate)
        request_dict['hdate']=f"{hdates}"

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
        num_pert_hcs = argument_output.get_num_pert_hcs(origin)
        pert_hcs = '/'.join(str(x) for x in np.arange(1,num_pert_hcs+1))
        request_dict['number'] = f"{pert_hcs}"
        request_dict['target'] = f"{filename}_perturbed_{lag}"

        server.retrieve(request_dict)

        # once requesting control and perturbed forecast, combine the two.
        # set forecast type in control to pf (perturbed forecast).
        os.system(f'grib_set -s type=pf -w type=cf {filename}_control_{lag} {filename}_control2_{lag}')
        # merge both control and perturbed forecast
        os.system(f'cdo merge {filename}_control2_{lag} {filename}_perturbed_{lag} {filename}_allens_{lag}')
        # shift the time so all reforecasts have the same time values
        os.system(f'cdo shifttime,{lag*-1}days {filename}_allens_{lag} {filename}_timeshifted_allens_{lag}')

    # create new 'member' dimension based on same date. For instance, 5 members per date and three initialisations used
    # same process following even with one forecast initialisation date to ensure same structure for all output. 
    combined_forecast = merge_all_ens_members(f'{filename}_timeshifted',leveltype)
    combined_forecast.to_netcdf(f'{filename}.nc')

    # remove previous files  
    os.system(f'rm {filename}_control* {filename}_perturbed* {filename}_*allens*')

def merge_all_ens_members(filename,leveltype):
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
    if leveltype == 'pressure':
        combined = combined.rename({'isobaricInhPa':'level'})
        combined = combined.transpose('time','member','level','latitude','longitude')
    else:
        combined = combined.transpose('time','member','latitude','longitude')

    return combined 

def download_forecast(variable,model,fcdate,local_destination=None,filename=None,area=[90,-180,-90,180],data_format='netcdf',grid='1.5/1.5',plevs=None,leadtime_hour=None,fc_enslags=None):
    '''
    Overarching function that will download forecast data from ECDS.
    From variable - script will work out whether sfc or pressure level and ecds varname. If necessary will also compute leadtime_hour. 

    '''
    leveltype, plevs, webapi_param, ecds_varname, origin_id, leadtime_hour = argument_output.check_and_output_all_fc_arguments(variable,model,fcdate,area,data_format,grid,plevs,leadtime_hour)

    # get fc_enslags
    # get lagged ensemble details
    if fc_enslags is None:
        fc_enslags = argument_output.output_fc_lags(origin_id,fcdate)
    # after gathering fc_enslags, check all ensemble lags are negative or zero and whole numbers as they can be user-inputted.
    argument_check.check_fc_enslags(fc_enslags)

    if filename == None:
        filename = f'{variable}_{model}_{fcdate}_fc'

    if local_destination != None:
        filename = f'{local_destination}/{filename}'

    webAPI_request_forecast(fcdate,origin_id,grid,variable,data_format,webapi_param,leadtime_hour,leveltype,filename,plevs,fc_enslags)

    return None 

def download_hindcast(variable,model,fcdate,local_destination=None,filename=None,area=[90,-180,-90,180],data_format='netcdf',grid='1.5/1.5',plevs=None,leadtime_hour=None,rf_years=None,rf_enslags=None):
    '''
    Overarching function that will download hindcast data from ECDS.
    From variable - script will work out whether sfc or pressure level and ecds varname. If necessary will also compute leadtime_hour. 

    '''
    # get parameters used in forecast and reforecasts
    leveltype, plevs, webapi_param, ecds_varname, origin_id, leadtime_hour = argument_output.check_and_output_all_fc_arguments(variable,model,fcdate,area,data_format,grid,plevs,leadtime_hour)

    # get reforecast lags.
    # from fcdate, work out what the reforecast lags should be.
    rf_enslags = argument_output.output_hc_lags(origin_id,fcdate)

    if filename == None:
        filename = f'{variable}_{model}_{fcdate}_hc'

    if local_destination != None:
        filename = f'{local_destination}/{filename}'

    webAPI_request_hindcast(fcdate,origin_id,grid,variable,data_format,webapi_param,leadtime_hour,leveltype,filename,plevs,rf_enslags,rf_years)

    return None

