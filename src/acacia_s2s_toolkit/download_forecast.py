# download sub-seasonal forecast data from WMO lead centre
from acacia_s2s_toolkit import argument_check, argument_output
import numpy as np

def check_and_output_all_arguments(variable,model,fcdate,area,data_format,grid,plevs,leadtime_hour):
    # check variable name. Is the variable name one of the abbreviations?
    argument_check.check_requested_variable(variable)
    # is it a sfc or pressure level field. # output sfc or level type
    level_type = argument_output.output_sfc_or_plev(variable)

    # if level_type == plevs and plevs=None, output_plevs. Will only give troposphere for q. 
    # work out appropriate pressure levels
    if level_type == 'pressure':
        if plevs is None:
            plevs = argument_output.output_plevs(variable)
        else:
            print (f"Downloading the requested pressure levels: {plevs}") # if not, use request plevs.
        # check plevs
        argument_check.check_plevs(plevs,variable)
    else:
        print (f"Downloading the following level type: {level_type}")
        plevs=None

    # get ECDS version of variable name. - WILL WRITE UP IN OCTOBER 2025!
    #ecds_varname = variable_output.output_ECDS_variable_name(variable)
    ecds_varname=None

    # get webapi param
    webapi_param = argument_output.output_webapi_variable_name(variable) # temporary until move to ECDS (Aug - Oct).
 
    # check model is in acceptance list and get origin code!
    argument_check.check_model_name(model)
    # get origin id
    origin_id = argument_output.output_originID(model)

    # if leadtime_hour = None, get leadtime_hour (output all hours).
    if leadtime_hour is None:
        leadtime_hour = argument_output.output_leadtime_hour(variable,origin_id) # the function outputs an array of hours. This is the leadtime used during download.
    print (f"For the following variable '{variable}' using the following leadtimes '{leadtime_hour}'.")

    # check fcdate.
    argument_check.check_fcdate(fcdate,origin_id) 

    # check dataformat
    argument_check.check_dataformat(data_format)

    # check leadtime_hours (as individuals can choose own leadtime_hours).
    argument_check.check_leadtime_hours(leadtime_hour,variable,origin_id)    

    # check area selection
    argument_check.check_area_selection(area)

    return level_type, plevs, webapi_param, ecds_varname, origin_id, leadtime_hour

def webAPI_request_forecast(fcdate,origin,grid,variable,webapi_param,leadtime_hour,leveltype,filename,plevs):
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

    if grid != '1.5/1.5':
        # add repres
        request_dict['repres'] = 'll'

    if leveltype == 'pressure':
        request_dict['levtype'] = 'pl'
        # convert plevs
        plevels = '/'.join(str(x) for x in plevs)
        request_dict['levelist'] = f"{plevels}"

    server.retrieve(request_dict)

    # then download perturbed. change type of forecast, add number of ensemble members, and change target filename
    request_dict['type'] = 'pf'
    request_dict['target'] = f"{filename}_perturbed"
    # add model number
    num_pert_fcs = argument_output.get_num_pert_fcs(origin)
    pert_fcs = '/'.join(str(x) for x in np.arange(1,num_pert_fcs+1))
    request_dict['number'] = f"{pert_fcs}"

    server.retrieve(request_dict)


def download_forecast(variable,model,fcdate,local_destination=None,filename=None,area=[90,-180,-90,180],data_format='netcdf',grid='1.5/1.5',plevs=None,leadtime_hour=None):
    '''
    Overarching function that will download forecast data from ECDS.
    From variable - script will work out whether sfc or pressure level and ecds varname. If necessary will also compute leadtime_hour. 

    '''

    leveltype, plevs, webapi_param, ecds_varname, origin_id, leadtime_hour = check_and_output_all_arguments(variable,model,fcdate,area,data_format,grid,plevs,leadtime_hour)

    if filename == None:
        filename = f'{variable}_{model}_{fcdate}_fc'

    if local_destination != None:
        filename = f'{local_destination}/{filename}'

    webAPI_request_forecast(fcdate,origin_id,grid,variable,webapi_param,leadtime_hour,leveltype,filename,plevs)


    return level_type

