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

Parameters including **fcdate**, **plevs**, **location_name**, **bbox_bounds**, **filename**, **data_save_dir**, **data_format**, **grid**, **leadtime_hour**, **overwrite** and **verbose** are described in the `download_forecasts <https://acacia-s2s-toolkit.readthedocs.io/en/latest/download_forecasts.html>`_ webpage. Additional parameters unique to downloading a set of reforecasts include:

- **rf_years** (*list of int*, optional): A list of years, i.e. [2000, 2001, 2002], to download reforecasts. 

- **rf_enslags** (*list of int*, optional): The selection of lagged ensemble members relative to the forecast initialisation date. Default values for each model is described on the following confluence page.

- **fc_time** (*bool*, default ``True``): If ``True``, overwrite existing file. If ``False``, skip download if file exists.

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

