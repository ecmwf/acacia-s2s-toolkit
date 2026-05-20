Welcome to acacia_s2s_toolkit's documentation!
===================================

**acacia_s2s_toolkit** is a Python library designed to support sub-seasonal operational forecasting and model evaluation. Specifically, this python wrapper is designed to support ACACIA partners, however it can be used by collaborators. 

The python wrapper pulls data from `ECMWF's Data Store <https://ecds.ecmwf.int/datasets/s2s-forecasts?tab=overview>`_ through creating appropriate request scripts to retrieve data efficiently.

.. note::

   This project is under active development.

.. important::

   This python wrapper is originally designed with operational forecasters in mind. Please be careful with using the python wrapper for forecast evaluation as certain timestamps may be invalid for your purpose.

Main authors
--------

- Joshua Talib (ECMWF), joshua.talib@ecmwf.int
- Innocent Masukwedza (NCAS-Reading), g.t.masukwedza@reading.ac.uk
- Piotr Wolski (University of Cape Town), wolski@csag.uct.ac.za
- Linda Hirons (NCAS-Reading), l.c.hirons@reading.ac.uk

Contents
--------
.. toctree::
   :maxdepth: 1
   :caption: Core

   Installation
   download_forecasts
   download_reforecast

.. toctree::
   :maxdepth: 1
   :caption: Example notebooks

   notebooks/deterministic_forecast_example
   notebooks/probabilistic_forecast_example
   notebooks/bias_correction_example
   notebooks/postprocessing_basic_example

.. toctree::
   :maxdepth: 1
   :caption: Other

   api
   tips_faq
   
