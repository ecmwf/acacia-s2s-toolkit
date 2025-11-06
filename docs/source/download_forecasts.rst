Downloading forecasts
=====

To download a forecast from ECMWF's S2S database, you will need to use the download_forecast function from the download_forecast.py python module. To begin with, it is recommended that you download ECMWF forecast data first to get used to the system. 

To import the module, use the following line of python code:

.. code-block:: python
    
    from acacia_s2s_toolkit.download_forecast import download_forecast

Use the `download_forecast` to download operational forecasts:

.. code-block:: python

   download_forecast(model, variable, fcdate=None, plevs=None, location_name=None, bbox_bounds=[90, -180, -90, 180], filename=None, data_save_dir=None, data_format="netcdf", grid="1.5/1.5", leadtime_hour=None, fc_enslags=None, overwrite=False, verbose=True)

:Parameters:

- **model** (*str*): The forecasting model. Supported models (as of 6th November 2025):

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

- **fcdate** (*str*, optional): Forecast initialisation date in ``YYYYMMDD`` format. If no date is given, then the latest avaliable forecast is downloaded.

- **plevs** (*int or list of int*, optional): Pressure levels in hPa for pressure-level variables. Avaliable levels include 1000, 925, 850, 700, 500, 300, 200, 100, 50 and 10 hPa.  

- **location_name** (*str*, optional): Predefined geographic region. Overrides ``bbox_bounds`` if provided. Current supported values include:
  - ``"ethiopia"``
  - ``"kenya"``
  - ``"madagascar"``
  - ``"eastafrica"``

- **bbox_bounds** (*list of float*, optional, default ``[90, -180, -90, 180]``): Geographic bounding box in the order ``[north, west, south, east]`` (degrees latitude/longitude). Overridden if ``location_name`` is provided.

- **filename** (*str*, optional): Name of the outputted file. If ``None``, filename is automatically constructed from variable, model, date, pressure levels, and domain. The function appends ``.nc`` or ``.grib`` depending on ``data_format``.

- **data_save_dir** (*str*, optional): Directory to save the downloaded file. Created if it doesn’t exist. Defaults to the current working directory if ``None``.

- **data_format** (*str*, optional, default ``"netcdf"``): Output data format: ``"netcdf"`` or ``"grib"``. Current testing has focused on netCDF format.

- **grid** (*str*, optional, default ``"1.5/1.5"``): Horizontal grid spacing (degrees) in ``lat/lon`` order.

- **leadtime_hour** (*int or list of int*, optional): Forecast lead times in hours from initialisation. If ``None``, then all avaliable lead times for the requested forecast will be provided. Example: ``24`` for 1 day, or ``[24, 48, 72]`` for 1 to 3 days.

- **fc_enslags** (*list of int*, optional): Ensemble member numbers to download. Ignored for deterministic forecasts. Example: ``[0, 1, 2]``.

- **overwrite** (*bool*, default ``False``): If ``True``, overwrite existing file. If ``False``, skip download if file exists.

- **verbose** (*bool*, default ``True``): If ``True``, prints download info, debug messages, and rollback messages. If ``False``, suppresses output.

:Returns:
  Path to the downloaded file as a string.

Explanations of certain options
-------------

fc_enslags
~~~~~~~~~~~~


leadtime_hour
~~~~~~~~~~~~


Examples
------------

