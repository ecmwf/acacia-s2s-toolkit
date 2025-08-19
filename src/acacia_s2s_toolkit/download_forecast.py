# download sub-seasonal forecast data from WMO lead centre
from acacia_s2s_toolkit import argument_check, argument_output, webAPI_requests

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

    webAPI_requests.request_forecast(fcdate,origin_id,grid,variable,area,data_format,webapi_param,leadtime_hour,leveltype,filename,plevs,fc_enslags)

    return None 


