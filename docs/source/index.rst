Welcome to acacia_s2s_toolkit's documentation!
===================================

**acacia_s2s_toolkit** is a Python library designed to support sub-seasonal operational forecasting and model evaluation. Specifically, this python wrapper is designed to support ACACIA partners, however it can be used by collaborators. 

The python wrapper pulls data from ECMWF's `S2S Open Database <https://confluence.ecmwf.int/display/S2S/S2S+archive>`_ through creating appropriate request scripts to retrieve data efficiently.

.. note::

   This project is under active development.

.. important::

   This python wrapper is originally designed with operational forecasters in mind. Please be careful with using the python wrapper for forecast evaluation as certain timestamps may be invalid for your purpose.

Contents
--------

.. toctree::

   Installation
   download_forecasts
   download_reforecast
   tips_faq
