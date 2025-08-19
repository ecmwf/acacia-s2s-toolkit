# download sub-seasonal reforecast from WMO lead centre
from acacia_s2s_toolkit import argument_output, webAPI_requests

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
    rf_model_date, rf_years = argument_output.check_and_output_all_hc_arguments(variable,origin_id,fcdate,rf_years)

    if filename == None:
        filename = f'{variable}_{model}_{fcdate}_hc'

    if local_destination != None:
        filename = f'{local_destination}/{filename}'

    webAPI_requests.request_hindcast(fcdate,origin_id,grid,variable,area,data_format,webapi_param,leadtime_hour,leveltype,filename,plevs,rf_enslags,rf_years)

    return None

