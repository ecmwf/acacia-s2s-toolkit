Getting started
=====

.. _installation:

Installation
------------

To use the **acacia_s2s_toolkit**, you will first need to have `Python 3 <https://www.python.org/downloads/>`_ installed.

You can then install the package using ``pip``:

.. code-block:: console

   pip install acacia_s2s_toolkit

Necessary requirements
------------

Saving ECMWF webAPI credentials
~~~~~~~~~~~~~~~~~~~~~~
At the time of writing, sub-seasonal forecast data from `ECMWF's S2S database <https://apps.ecmwf.int/datasets/data/s2s-realtime-instantaneous-accum-ecmf/levtype=sfc/type=cf/>`_ is made available through ECMWF's webAPI. To download data from the ECMWF webAPI, you need to configure your ECMWF API key.

After registering for an ECMWF account, your API credentials can be found at `https://api.ecmwf.int/v1/key <https://api.ecmwf.int/v1/key>`_. 

Save these credentials to your home directory as a file named ``~/.ecmwfapirc`` .

Installing ECMWF client libraries
~~~~~~~~~~~~~~~~~~~~~~
Once your ECMWF webAPI credentials are saved, install the ECMWF client library using ``pip``:

.. code-block:: console

   pip install ecmwf-api-client

This package provides the necessary client functions for accessing ECMWF data.

.. important::
    Access to data stored on ECMWF's S2S database will be changing from webAPI to cdsAPI. The new system relies on retrieval scripts compatible with the Climate Data Store (CDS). This package will be updated to support the new system after the transition is complete.

Quick checklist
~~~~~~~~~~~~~~~~~~~~~~
Before attempting to download sub-seasonal forecast data using this python tool, please ensure you have performed the following steps:
1) `Python 3 <https://www.python.org/downloads/>`_ is installed
2) The Python packages **acacia_s2s_toolkit** and **ecmwf-api-client** are installed. 
3) Your ECMWF webAPI credentials are saved in ``~/.ecmwfapirc`` on your working environment.

Further information
------------

For more details on setting up access to ECMWF public datasets, please visit `access ECMWF public datasets <https://confluence.ecmwf.int/display/WEBAPI/Access+ECMWF+Public+Datasets#AccessECMWFPublicDatasets-availability>`_

