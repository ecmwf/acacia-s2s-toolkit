# download sub-seasonal forecast data from WMO lead centre
from acacia_s2s_toolkit import argument_check, argument_output

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
    if leadtime_hour == None:
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

def download_forecast(variable,model,fcdate,area=[90,-180,-90,180],data_format='netcdf',grid='1.5/1.5',plevs=None,leadtime_hour=None):
    '''
    Overarching function that will download forecast data from ECDS.
    From variable - script will work out whether sfc or pressure level and ecds varname. If necessary will also compute leadtime_hour. 

    '''

    level_type, plevs, webapi_param, ecds_varname, origin_id, leadtime_hour = check_and_output_all_arguments(variable,model,fcdate,area,data_format,grid,plevs,leadtime_hour)

    # download control forecast


    # download perturbed forecast

    return level_type

