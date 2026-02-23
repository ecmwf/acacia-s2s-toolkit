# practice python script that tests downloads from WMO lead centre.

from acacia_s2s_toolkit.download_forecast import download_forecast
from acacia_s2s_toolkit.download_hindcast import download_hindcast
import numpy as np

fc_time=False
rf_enslags=[-1]
leadtime_hour=np.arange(24,28*24,24)
fcdate='20251120'

#download_forecast('ECMWF','tp',fcdate='20251101',fc_enslags=[-1],leadtime_hour=[24,48],bbox_bounds=[20,-20,-40,50])
download_hindcast('ECMWF', 'tp', fcdate=fcdate, location_name='madagascar',leadtime_hour=leadtime_hour, rf_years=None, rf_enslags=rf_enslags, fc_time=fc_time,verbose=True)
