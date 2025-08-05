# download sub-seasonal forecast data from WMO lead centre
from acacia_s2s_toolkit import variable_check, variable_output

def download_forecast(variable,model,fcdate,grid='1.5/1.5',data_format='netcdf',area=[],plevs=None,leadtime_hour=None):
    '''
    Overarching function that will download suitable forecast data from ECDS.
    '''

    # check variable name
    variable_check.check_requested_variable(variable)
    # get sfc or plev field
    level_type = variable_output.output_sfc_or_plev(variable)

    # if level_type == plevs and plevs=None, output_plevs. will only give troposphere for q. 

    # get ECDS version of variable name.
    ecds_varname = variable_output.output_ECDS_variable_name(variable)

    # if leadtime_hour = None, get leadtime_hour (output all hours).
    if leadtime_hour == None:
        leadtime_hour = variable_output.output_leadtime_hour(variable)




