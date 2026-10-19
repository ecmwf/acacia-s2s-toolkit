Models
======

.. important::
    This is a tool being developed by the ACACIA project. Please email feedback to joshua.talib@ecmwf.int.

Model Selection by the User
---------------------------

Use the following syntax to select your desired model (example model below is ECMWF):

.. code-block:: python

   download_forecast(variable, model='ECMWF')
   
.. note::

    ECMWF has the most ensemble members so will be selected as the default if no model is specified by the user.

Available Models
----------------

The models differ from each other in many ways, including forecast frequency, ensemble size, and data access delay.  Different institutions also manage reforecasts differently.  A full summary of all models available in the ECMWF database can be found on the ECMWF `confluence page <https://confluence.ecmwf.int/display/S2S/Models>`_, where you can find useful information about each model in the following columns:

.. image:: models_table.png
   :alt: Models available in ECMWF database
   :align: center

Image: where to find helpful information about how each model available in the ECMWF database manages forecasts (black boxes) and reforecasts (orange boxes).  This is an illustrative example; for up-to-date information please see the ECMWF `confluence page <https://confluence.ecmwf.int/display/S2S/Models>`_.

