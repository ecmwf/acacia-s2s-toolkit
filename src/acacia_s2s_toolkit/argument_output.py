# output suitable ECDS variables in light of requested forecasts.
from acacia_s2s_toolkit.variable_dict import s2s_variables, webAPI_params, model_origin, forecast_length_hours, forecast_pert_members
from acacia_s2s_toolkit import argument_check
import numpy as np

def get_endtime(origin_id):
    # next find maximum end time
    end_time=None
    for originID, fc_length in forecast_length_hours.items():
        if originID == origin_id:
            end_time=fc_length
            break

    if end_time is None:
        print (f"[ERROR] could not find forecast length for originID '{origin_id}'.")
        return None

    return end_time

def get_num_pert_fcs(origin_id):
    # find number pert. forecasts
    num_pert_fcs=None
    for originID, num_fc_ens in forecast_pert_members.items():
        if originID == origin_id:
            num_pert_fcs=num_fc_ens
            break

    if num_pert_fcs is None:
        print (f"[ERROR] could not find number pert. forecasts for originID '{origin_id}'.")
        return None

    return num_pert_fcs

def get_timeresolution(variable):
    # first find which sub-category the variable sits in
    time_resolution=None
    for category_name, category_dict in s2s_variables.items():
        for subcategory_name, subcategory_vars in category_dict.items():
            if variable in subcategory_vars:
                time_resolution = subcategory_name
                break # found correct time resolution
        if time_resolution:
            break # break outer loop

    if time_resolution is None:
        print (f"[ERROR] could not find variable '{variable}'.")
        return None
    return time_resolution

def output_leadtime_hour(variable,origin_id,start_time=0):
    '''
    Given variable (variable abbreivation), output suitable leadtime_hour. The leadtime_hour will request all avaliable steps. Users should be able to pre-define leadtime_hour if they do not want all output.
    return: leadtime_hour
    '''
    time_resolution = get_timeresolution(variable)

    # next find maximum end time
    end_time = get_endtime(origin_id)

    # given time resolution, work out array of appropriate time values
    if time_resolution.endswith('6hrly'):
        leadtime_hour = np.arange(start_time,end_time+1,6)
    else:
        leadtime_hour = np.arange(start_time,end_time+1,24) # will output 0 to 1104 in steps of 24 (ECMWF example). 
 
    print (f"For the following variable '{variable}' using the following leadtimes '{leadtime_hour}'.")

    return leadtime_hour

def output_sfc_or_plev(variable):
    '''
    Given variable (variable abbreivation), output whether variable is sfc level or on pressure levels?
    return: level_type
    '''
    # Flatten all variables from nested dictionary
    level_type=None
    for category_name, category_dict in s2s_variables.items():
        for subcategory_vars in category_dict.values():
            if variable in subcategory_vars:
                level_type = category_name
                return level_type
    if level_type == None:
        print (f"[ERROR] No leveltype found for '{variable}'.")
        return level_type

def output_webapi_variable_name(variable):
    ''' 
    Given variable abbreviation, output webAPI paramID.
    return webAPI paramID.

    '''
    for variable_abb, webapi_code in webAPI_params.items():
        if variable == variable_abb:
            return webapi_code
    print (f"[ERROR] No webAPI paramID found for '{variable}'.")
    return None

def output_originID(model):
    '''
    Given model name, output originID.
    return originID.

    '''
    for modelname, originID in model_origin.items():
        if model == modelname:
            return originID
    print (f"[ERROR] No originID found for '{model}'.")
    return None


def output_ECDS_variable_name(variable):
    '''
    Given variable name, output the matching ECDS variable name
    
    return ECDS_varname (ECMWF Data Store)
    '''
    ECDS_varname='10m_uwind'
    return ECDS_varname

def output_plevs(variable):
    '''
    Output suitable plevs, if q, (1000, 925, 850, 700, 500, 300, 200) else add 100, 50 and 10 hPa. 
    '''
    all_plevs=[1000,925,850,700,500,300,200,100,50,10]
    if variable == 'q':
        plevs=all_plevs[:-3] # if q is chosen, don't download stratosphere
    else:
        plevs=all_plevs
    print (f"Selected the following pressure levels: {plevs}")
    
    return plevs

def check_and_output_all_arguments(variable,model,fcdate,area,data_format,grid,plevs,leadtime_hour):
    # check variable name. Is the variable name one of the abbreviations?
    argument_check.check_requested_variable(variable)
    # is it a sfc or pressure level field. # output sfc or level type
    level_type = output_sfc_or_plev(variable)

    # if level_type == plevs and plevs=None, output_plevs. Will only give troposphere for q. 
    # work out appropriate pressure levels
    if level_type == 'pressure':
        if plevs is None:
            plevs = output_plevs(variable)
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
    webapi_param = output_webapi_variable_name(variable) # temporary until move to ECDS (Aug - Oct).

    # check model is in acceptance list and get origin code!
    argument_check.check_model_name(model)
    # get origin id
    origin_id = output_originID(model)

    # if leadtime_hour = None, get leadtime_hour (output all hours).
    if leadtime_hour is None:
        leadtime_hour = output_leadtime_hour(variable,origin_id) # the function outputs an array of hours. This is the leadtime used during download.
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



