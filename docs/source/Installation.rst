Getting started
=====

.. important::
    This is a tool being developed by the ACACIA project. Please email feedback to joshua.talib@ecmwf.int.

.. _installation:

Installation
------------

To use the **acacia_s2s_toolkit**, you will first need to have `Python 3 <https://www.python.org/downloads/>`_ installed.

You can then install the package using ``pip``:

.. code-block:: console

   pip install acacia_s2s_toolkit

Upgrading the Package
----------------------
To upgrade to the latest version, run:

.. code-block:: bash

   python3 -m pip install --upgrade acacia_s2s_toolkit

.. note::
    This tool is being developed by the ACACIA project. Regular package updates are recommended due to continuous developments. 

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

Additional package dependencies
~~~~~~~~~~~~~~~~~~~~~~
In addition to requiring "*ecmwf-api-client*", the package has the following dependencies:

- **numpy** (version 1.23 or higher)
- **cdo** (versions 2.4.0 or higher)
- **xarray** (version 2024.09.0 or higher)
- **eccodes** (version 2.40.0 or higher)
- **dask** (version 2024.9.0)
- **pandas** (version 2.2.3 or higher)
- **scipy** (version 1.14.1 or higher)
- **netCDF4** (version 1.7.2 or higher)
- **requests** (versions 2.32.2 or higher)
- **matplotlib** (versions 3.8 or higher)
- **cartopy** (versions 0.22 or higher)

Given the large number of dependencies, we highly recommend using the **acacia_s2s_toolkit** in a virtual environment. 

Quick checklist
~~~~~~~~~~~~~~~~~~~~~~
Before attempting to download sub-seasonal forecast data using this python tool, please ensure you have performed the following steps:

1. `Python 3 <https://www.python.org/downloads/>`_ is installed
2. The Python packages **acacia_s2s_toolkit** and **ecmwf-api-client** are installed. 
3. Your ECMWF webAPI credentials are saved in ``~/.ecmwfapirc`` on your working environment.


Further information
------------

For more details on setting up access to ECMWF public datasets, please visit `access ECMWF public datasets <https://confluence.ecmwf.int/display/WEBAPI/Access+ECMWF+Public+Datasets#AccessECMWFPublicDatasets-availability>`_

