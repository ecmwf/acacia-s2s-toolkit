Downloading forecasts
=====

To download a forecast from ECMWF's S2S database, you will need to use the download_forecast function from the download_forecast.py python module. To import the module, use the following line of code:

from acacia_s2s_toolkit.download_forecast import download_forecast

Use the `download_forecast` to download operational forecasts:

.. code-block:: python

   download_forecast(model,variable,fcdate=None,plevs=None,location_name=None,bbox_bounds=[90, -180, -90, 180],filename=None,data_save_dir=None,data_format="netcdf",grid="1.5/1.5",leadtime_hour=None,fc_enslags=None,overwrite=False,verbose=True)

- **model** (*str*): The forecasting model. As of 6th November 2025, available options include:

  - ``'ECMWF'``: European Centre for Medium-Range Weather Forecasts
  - ``'ECCC'``: Environment and Climate Change Canada
  - ``'HMCR'``: Hydrometeorological Centre of Russia
  - ``'JMA'``: Japan Meteorological Agency
  - ``'KMA'``: Korea Meteorological Administration
  - ``'NCEP'``: National Centers for Environmental Prediction (NOAA/USA)
  - ``'CMA'``: China Meteorological Administration

- **variable** (*str*): The forecasted variable. Please use variable abbreviations listed on `ECMWF's S2S parameter page <https://confluence.ecmwf.int/display/S2S/Parameters>`_. A few examples include:

  - ``10u``: 10 metre u-velocity (:math:`\mathrm{m \, s^{-1}}`)
  - ``10v``: 10 metre v-velocity (:math:`\mathrm{m \, s^{-1}}`)
  - ``2t``: Surface air temperature (K)
  - ``tp``: Total precipitation (mm)





