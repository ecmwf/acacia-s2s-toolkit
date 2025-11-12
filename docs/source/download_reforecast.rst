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

After this, use the `download_hindcast` function to download operational reforecasts:

.. code-block:: python

   download_hindcast(model, variable, fcdate=None, plevs=None, location_name=None, bbox_bounds=[90, -180, -90, 180], filename=None, data_save_dir=None, data_format="netcdf", grid="1.5/1.5", leadtime_hour=None, rf_years=None, rf_enslags=None, fc_time=True, overwrite=False, verbose=True)

This function retrieves operational reforecast (hindcast) data for a specified model and variable from the S2S database. It supports downloading multiple initialization years and ensemble lags for a given forecasting system.

:Necessary parameters:

- **model** (*str*): The forecasting model. The full list of supported models is avaliable on the `download_forecasts <https://acacia-s2s-toolkit.readthedocs.io/en/latest/download_forecasts.html>`_ webpage.

- **variable** (*str*): The forecasted variable to download. Use variable abbreviations listed on `ECMWF's S2S parameter page <https://confluence.ecmwf.int/display/S2S/Parameters>`_.

.. note::

Each variable must be requested separately.

:Optional parameters:

Parameters including **fcdate**, **plevs**, **location_name**, **bbox_bounds**, **filename**, **data_save_dir**, **data_format**, **grid**, **leadtime_hour**, **overwrite** and **verbose** are described in detail on the `download_forecasts <https://acacia-s2s-toolkit.readthedocs.io/en/latest/download_forecasts.html>`_ webpage. Additional parameters specific to reforecast downloads include:

- **rf_years** (*list of int*, optional): List of years to download reforecasts for. For example, [2000, 2001, 2002] will retrieve all reforecasts initialised between 2000 and 2002. 

- **rf_enslags** (*list of int*, optional): List of lagged ensemble members (in days) relative to the forecast initialization date. Default values depend on the selected model; see the following `confluence page <https://confluence.ecmwf.int/display/~ecm0847/acacia_s2s_toolkit+available+forecasting+systems>`_ for details. 

- **fc_time** (*bool*, default ``True``): **Option in development** If ``True``, shifts all lagged ensemble members so their forecast times are aligned to a common initialization date (useful for ensemble averaging). If False, preserves each member’s original valid time (useful for forecast validation).

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

