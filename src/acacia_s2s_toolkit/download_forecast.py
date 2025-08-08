# download sub-seasonal forecast data from WMO lead centre
from acacia_s2s_toolkit import argument_check, argument_output
import numpy as np
import os

def webAPI_request_forecast(fcdate,origin,grid,variable,data_format,webapi_param,leadtime_hour,leveltype,filename,plevs):
    from ecmwfapi import ECMWFDataServer
    server = ECMWFDataServer()

    # convert fcdate to YYYY-MM-DD
    convert_fcdate = f'{fcdate[:4]}-{fcdate[4:6]}-{fcdate[6:]}'
    
    # convert leadtimes 
    # is it an average field?
    time_resolution = argument_output.get_timeresolution(variable) 
    # if an average field, use '0-24/24-48/48-72...'
    if time_resolution.startswith('aver'):
        leadtimes='/'.join(f"{leadtime_hour[i]}-{leadtime_hour[i]+24}" for i in range(len(leadtime_hour)-1))
    else: # instantaneous field
        leadtimes = '/'.join(str(x) for x in leadtime_hour)

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
        "target": f"{filename}_control"
        }

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

    server.retrieve(request_dict)

    # then download perturbed. change type of forecast, add number of ensemble members, and change target filename
    request_dict['type'] = 'pf'
    # add model number (will not be needed for ECDSapi)
    num_pert_fcs = argument_output.get_num_pert_fcs(origin)
    pert_fcs = '/'.join(str(x) for x in np.arange(1,num_pert_fcs+1))
    request_dict['number'] = f"{pert_fcs}"
    request_dict['target'] = f"{filename}_perturbed"

    server.retrieve(request_dict)

    # once requesting control and perturbed forecast, combine the two.
    # set forecast type in control to pf (perturbed forecast).
    os.system(f'grib_set -s type=pf -w type=cf {filename}_control {filename}_control2')
    # merge both control and perturbed forecast
    os.system(f'cdo merge {filename}_control2 {filename}_perturbed {filename}_allens')
    # convert to netcdf if data formatted request, else keep as grib
    if data_format == 'netcdf':
        os.system(f'grib_to_netcdf -o {filename}.nc {filename}_allens')
    else:
        os.system(f'mv {filename}_allens {filename}.grb')
    # remove all unnecessary files    
    os.system(f'rm {filename}_control {filename}_control2 {filename}_perturbed {filename}_allens')

def download_forecast(variable,model,fcdate,local_destination=None,filename=None,area=[90,-180,-90,180],data_format='netcdf',grid='1.5/1.5',plevs=None,leadtime_hour=None):
    '''
    Overarching function that will download forecast data from ECDS.
    From variable - script will work out whether sfc or pressure level and ecds varname. If necessary will also compute leadtime_hour. 

    '''
    leveltype, plevs, webapi_param, ecds_varname, origin_id, leadtime_hour = argument_output.check_and_output_all_arguments(variable,model,fcdate,area,data_format,grid,plevs,leadtime_hour)

    if filename == None:
        filename = f'{variable}_{model}_{fcdate}_fc'

    if local_destination != None:
        filename = f'{local_destination}/{filename}'

    webAPI_request_forecast(fcdate,origin_id,grid,variable,data_format,webapi_param,leadtime_hour,leveltype,filename,plevs)

    return None 

