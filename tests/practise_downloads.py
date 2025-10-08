# practice python script that tests downloads from WMO lead centre.

from acacia_s2s_toolkit.download_forecast import download_forecast
from acacia_s2s_toolkit.download_hindcast import download_hindcast
import numpy as np

mc = 'ECMWF'

hours = np.arange(24,97,24)

chosen_date = '20250825'
download_hindcast('ECMWF','2t',fcdate=chosen_date,leadtime_hour=hours,bbox_bounds=[20,-20,-40,50],rf_enslags=[0])


# testing for ECMWF, Monday, Wednesday, Thursday between all model changes
for chosen_date in ['20250828','20250827','20250825','20241007','20241009','20241010']:
    variable = '2t'
    #for variable in ['2t', '10u']:
        #, 'tp','t','pv','sm20','ttr','sshf','msl']:
    if variable == 't':
        download_forecast(variable, mc, chosen_date,plevs=[925,850],area=[20,-20,-40,50])
        download_hindcast(variable, mc, chosen_date,leadtime_hour=hours,plevs=[925,850],area=[20,-20,-40,50])
    else:
        download_forecast(variable, mc, chosen_date,area=[5,10,-10,20],leadtime_hour=hours)
        download_hindcast(variable, mc, chosen_date,leadtime_hour=hours,area=[5,10,-10,20])
