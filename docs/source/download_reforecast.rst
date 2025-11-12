Downloading operational reforecasts
=====

.. important::
    This is a tool being developed by the ACACIA project. Please email feedback to joshua.talib@ecmwf.int.

Download a collection of reforecasts
-----------

To download a selection of reforecasts from ECMWF's S2S database, you will need to use the `download_hindcast` function from the `download_hindcast.py` python module. To begin with, it is recommended that you download ECMWF reforecast data first to get used to the system. 

To import the necessary function, use the following line of python code:

.. code-block:: python
    
    from acacia_s2s_toolkit.download_hindcast import download_hindcast

After this, use `download_hindcast` to download operational reforecasts:

.. code-block:: python

   download_hindcast(model, variable, fcdate=None, plevs=None, location_name=None, bbox_bounds=[90, -180, -90, 180], filename=None, data_save_dir=None, data_format="netcdf", grid="1.5/1.5", leadtime_hour=None, rf_years=None, rf_enslags=None, fc_time=True, overwrite=False, verbose=True)

:Necessary parameters:

- **model** (*str*): The forecasting model. Full details of supported models will be updated on the `download_forecasts <https://acacia-s2s-toolkit.readthedocs.io/en/latest/download_forecasts.html>`_ webpage.

- **variable** (*str*): The forecasted variable. Please use variable abbreviations listed on `ECMWF's S2S parameter page <https://confluence.ecmwf.int/display/S2S/Parameters>`_.

Currently a separate download request is required for each variable. 

:Optional parameters:

- **fcdate** (*str*, optional): Forecast initialisation date in ``YYYYMMDD`` format. If no date is given, then the latest avaliable reforecast is downloaded.

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

- **rf_years** (*list of int*, optional): Need to write.

- **rf_enslags** (*list of int*, optional): Need to write.

- **fc_time** (*bool*, default ``True``): If ``True``, overwrite existing file. If ``False``, skip download if file exists.

- **overwrite** (*bool*, default ``True``): If ``True``, overwrite existing file. If ``False``, skip download if file exists.

- **verbose** (*bool*, default ``True``): If ``True``, prints download info, debug messages, and rollback messages. If ``False``, suppresses output.

:Returns:
  Path to the downloaded file as a string.

.. note::

    For simplicity, all ensemble members are downloaded in a single request. Currently, the control and perturbed reforecasts are concatenated into one file after download.

You can check the status of your webAPI downloads on the following `page <https://apps.ecmwf.int/webmars/joblist/>`_. 

Examples
------------
To be developed.


Explanations of certain options
-------------

rf_enslags (reforecast lagged ensemble capability)
~~~~~~~~~~~~

