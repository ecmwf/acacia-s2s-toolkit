# script containing all relevant code for producing webAPI requests.
# In Q3 2025, will move from webAPI to ECDS

from acacia_s2s_toolkit import argument_output, merge_lag_ensemble
import numpy as np
import os
import eccodes as ec
from datetime import datetime, timedelta
from ecmwfapi import ECMWFDataServer
server = ECMWFDataServer()

def create_initial_webAPI_request(fcdate,grid,area,origin,webapi_param,leadtimes,filename):
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

    # add area component
    area_formatted = '/'.join(str(x) for x in area)
    request_dict['area'] = f"{area_formatted}"

    return request_dict

def request_forecast(fcdate,origin,grid,variable,area,data_format,webapi_param,leadtime_hour,leveltype,filename,plevs,fc_enslags):
    # to enable lagged ensemble, loop through requested ensembles
    for lag in fc_enslags:
        leadtimes, convert_fcdate = argument_output.output_formatted_leadtimes(leadtime_hour,fcdate,variable,lag=lag,fc_enslags=fc_enslags)
        # create initial control request
        request_dict = create_initial_webAPI_request(convert_fcdate,grid,area,origin,webapi_param,leadtimes,f'{filename}_control_{lag}')

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
        set_cf_to_pf(f'{filename}_control_{lag}',f'{filename}_control2_{lag}')
        #os.system(f'grib_set -s type=pf -w type=cf {filename}_control_{lag} {filename}_control2_{lag}')
        # merge both control and perturbed forecast
        os.system(f'cdo merge {filename}_control2_{lag} {filename}_perturbed_{lag} {filename}_allens_{lag}')

    # create new 'member' dimension based on same date. For instance, 5 members per date and three initialisations used
    # smae process following even with one forecast initialisation date to ensure same structure for all output. 
    combined_forecast = merge_lag_ensemble.merge_all_ens_members(f'{filename}',leveltype)
    combined_forecast.to_netcdf(f'{filename}.nc')

    # remove previous files  
    os.system(f'rm {filename}_control* {filename}_perturbed* {filename}_allens*')

def request_hindcast(fcdate,origin,grid,variable,area,data_format,webapi_param,leadtime_hour,leveltype,filename,plevs,rf_enslags,rf_years):
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
        request_dict = create_initial_webAPI_request(convert_fcdate,grid,area,origin,webapi_param,leadtimes,f'{filename}_control_{lag}')

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
        set_cf_to_pf(f'{filename}_control_{lag}',f'{filename}_control2_{lag}')
        #os.system(f'grib_set -s type=pf -w type=cf {filename}_control_{lag} {filename}_control2_{lag}')
        # merge both control and perturbed forecast
        os.system(f'cdo merge {filename}_control2_{lag} {filename}_perturbed_{lag} {filename}_allens_{lag}')
        # shift the time so all reforecasts have the same time values
        os.system(f'cdo shifttime,{lag*-1}days {filename}_allens_{lag} {filename}_timeshifted_allens_{lag}')

    # create new 'member' dimension based on same date. For instance, 5 members per date and three initialisations used
    # same process following even with one forecast initialisation date to ensure same structure for all output. 
    combined_forecast = merge_lag_ensemble.merge_all_ens_members(f'{filename}_timeshifted',leveltype)
    combined_forecast.to_netcdf(f'{filename}.nc')

    # remove previous files  
    os.system(f'rm {filename}_control* {filename}_perturbed* {filename}_*allens*')

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

