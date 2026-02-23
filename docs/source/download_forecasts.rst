Downloading operational forecasts
=====

.. important::
    This is a tool being developed by the ACACIA project. Please email feedback to joshua.talib@ecmwf.int.

Download a forecast
-----------

To download a forecast from ECMWF's S2S database, you will need to use the `download_forecast` function from the `download_forecast.py` python module. To begin with, it is recommended that you download ECMWF forecast data first to get used to the system. 

To import the necessary function, use the following line of python code:

.. code-block:: python
    
    from acacia_s2s_toolkit.download_forecast import download_forecast

After this, use `download_forecast` to download operational forecasts:

.. code-block:: python

   download_forecast(model, variable, fcdate=None, plevs=None, location_name=None, bbox_bounds=[90, -180, -90, 180], filename=None, data_save_dir=None, data_format="netcdf", grid="1.5/1.5", leadtime_hour=None, fc_enslags=None, overwrite=False, verbose=True)

:Necessary parameters:

- **model** (*str*): The forecasting model. A full summary of models including their forecast frequency and data access delay can be found on the following `confluence page <https://confluence.ecmwf.int/display/S2S/Models>`_. Supported models (as of 6th November 2025) include:

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

Currently a download request is required for each variable. 

:Optional parameters:

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

- **fc_enslags** (*list of int*, optional): The selection of lagged ensemble members relative to the forecast initialisation date. Default values for each model is described on the following `confluence page <https://confluence.ecmwf.int/display/~ecm0847/acacia_s2s_toolkit+available+forecasting+systems>`_.

- **overwrite** (*bool*, default ``False``): If ``True``, overwrite existing file. If ``False``, skip download if file exists.

- **verbose** (*bool*, default ``True``): If ``True``, prints download info, debug messages, and rollback messages. If ``False``, suppresses output.

:Returns:
  Path to the downloaded file as a string.

.. note::

    For simplicity, all ensemble members are downloaded in a single request. Currently, the control and perturbed forecasts are concatenated into one file after download.

You can check the status of your webAPI downloads on the following `page <https://apps.ecmwf.int/webmars/joblist/>`_ . 

Examples
------------
To be developed.


Explanations of certain options
-------------

fc_enslags (lagged ensemble capability)
~~~~~~~~~~~~

As described in `ECMWF's S2S forecast models <https://confluence.ecmwf.int/display/S2S/Models>`_, different forecasting centres run integrations at varying frequencies and ensemble sizes. Consequently, certain choices must be made to ensure a sufficient number of forecasts are downloaded.

The ``fc_enslags`` option allows the user to download a **lagged forecast ensemble**.

- The list of integers provided must always be **less than or equal to zero**.
- Creating a lagged ensemble will only work if a forecast was initialised on the requested lagged date.

Example 1: Single forecast initialisation
^^^^^^^^^^^

Suppose you want to request a JMA forecast of accumulated precipitation on **6th November 2025**. You can set ``fc_enslags=[0]``:

.. code-block:: python

   download_forecast('JMA', 'tp', fcdate='20251106', fc_enslags=[0])

This will download all timesteps of forecasted precipitation from the forecast run initialised on 6th November 2025. Since ``fc_enslags`` is set to ``0``, it only includes integrations starting on that date.

Example 2: Lagged forecast ensemble
^^^^^^^^^^^^^^^^^^^

If you set ``fc_enslags=[0, -1, -2]`` (the default for JMA forecasts):

.. code-block:: python

   download_forecast('JMA', 'tp', fcdate='20251106', fc_enslags=[0, -1, -2])

This will download forecasts from **three initialisations**:

- 2025-11-06 (``0``)
- 2025-11-05 (``-1``)
- 2025-11-04 (``-2``)

For the lagged ensemble, the **time dimension corresponds to the forecasted period**. For example, when requesting a lag of ``-2``, the first two days of the forecast are removed so that all forecasts align at the same starting point.

.. note::

   To download all available forecast data from a model, it is recommended to use ``fc_enslags=[0]`` and loop over start dates.


leadtime_hour
~~~~~~~~~~~~

The temporal resolution of forecast data available from ECMWF's S2S database varies depending on the selected variable. A complete list of parameters and their corresponding resolutions can be found on the `ECMWF's S2S parameter page <https://confluence.ecmwf.int/display/S2S/Parameters>`_. In general, data is provided at either six-hourly or daily intervals, and may represent instantaneous, averaged, or accumulated values. 

The Python-based dictionary called ``s2s_variables`` in `variable_dict.py <https://github.com/joshuatalib/acacia_s2s_toolkit/blob/main/src/acacia_s2s_toolkit/variable_dict.py>`_ provides an overview of all avaliable parameters and their associated temporal resolutions.

When downloading a variable, the default behaviour is to retrieve all available lead times. For example,

.. code-block:: python

   download_forecast('ECMWF', 'tp', fcdate='20251106')

This command downloads accumulated preciptation (``'tp'``) up to 46 days ahead at a six-hourly resolution. As total precipitation (``'tp'``) is an accumulated field, downloading all lead times is often unnecessry. Instead, you can specify a subset of lead times to obtain accumulated precipitation at a weekly resolution for the first four weeks:

.. code-block:: python

   download_forecast('ECMWF', 'tp', fcdate='20251106',leadtime_hour=[168,336,504,672])

This download will include data at four timestamps, each representing the end of a week. 

.. important::

   When working with accumulated variables in a lagged ensemble environment, take care when specifying lead times. The current configuration shifts leadtime_hour according to the lagged_ensemble offset, which may cause discrepancies in accumulated values. For example, using fc_enslag=-1 with leadtime_hour=168 will shift the lead time to 192 hours, effectively adding an extra day of precipitation. To avoid this, compute the difference between two lead times.

