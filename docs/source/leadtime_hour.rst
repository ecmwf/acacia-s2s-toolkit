leadtime_hour
=============

.. important::
    This is a tool being developed by the ACACIA project. Please email feedback to joshua.talib@ecmwf.int.
    
The temporal resolution of forecast data available from ECMWF's S2S database varies depending on the selected variable. A complete list of parameters and their corresponding resolutions can be found on the `ECMWF's S2S parameter page <https://confluence.ecmwf.int/display/S2S/Parameters>`_. In general, data is provided at either six-hourly or daily intervals, and may represent instantaneous, averaged, or accumulated values. 

The Python-based dictionary called ``s2s_variables`` in `variable_dict.py <https://github.com/ecmwf/acacia-s2s-toolkit/blob/main/src/acacia_s2s_toolkit/variable_dict.py>`_ provides an overview of all avaliable parameters and their associated temporal resolutions.

When downloading a variable, the default behaviour is to retrieve all available lead times. For example,

.. code-block:: python

   download_forecast('ECMWF', 'tp', fcdate='20251106')

This command downloads accumulated preciptation (``'tp'``) up to 46 days ahead at a six-hourly resolution. As total precipitation (``'tp'``) is an accumulated field, downloading all lead times is often unnecessary. Instead, you can specify a subset of lead times to obtain accumulated precipitation at a weekly resolution for the first four weeks:

.. code-block:: python

   download_forecast('ECMWF', 'tp', fcdate='20251106',leadtime_hour=[168,336,504,672])

This download will include data at four timestamps, each representing the end of a week. 

.. important::

   When working with accumulated variables in a lagged ensemble environment, take care when specifying lead times. The current configuration shifts leadtime_hour according to the lagged_ensemble offset, which may cause discrepancies in accumulated values. For example, using fc_enslag=-1 with leadtime_hour=168 will shift the lead time to 192 hours, effectively adding an extra day of precipitation. To avoid this, compute the difference between two lead times.

