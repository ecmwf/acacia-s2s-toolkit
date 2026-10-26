Postprocessing, bias correction and evaluation framework
========================================================

Why an "open-ended" postprocessing framework?
---------------------------------------------

Downloaded data come in a format that is not particularly convenient for further
processing. The general path from data to product is:

#. download data;
#. bias correction against observations;
#. derivation of forecast products;
#. evaluation of hindcast skill against observations;
#. verification of a single forecast against observations.

The general problem
~~~~~~~~~~~~~~~~~~~

- At lead times longer than those of weather forecasts, skill is present in multi-day
  aggregates, not at the daily time scale.
- Biases depend on lead time, so bias correction should be done on a lead-time basis.
- Skill and verification have to be evaluated on a valid-time basis.
- Skill increases with ensemble size, particularly at longer lead times, but hindcasts
  have small ensembles.
- There is therefore a benefit in creating lagged ensembles (ensembles composed of
  ensembles started on different initialisation dates), both for the hindcast and the
  forecast.
- Working with lagged ensembles, however, requires choices about how to "stitch" the
  ensembles together for forecasting, bias correction and evaluation.

Two approaches are possible:

#. Lead-time based bias correction of daily data (done in multi-day lead-time windows),
   and construction of valid-time based forecasts and hindcasts of multi-day aggregates
   derived from the daily bias-corrected data. With lagged ensembles, aggregates are
   calculated for the valid times at which all ensembles overlap.

   The problem with this approach is that bias correction at the daily time scale does
   not guarantee that the multi-day aggregates are free of bias.

#. Construction of an "effective" ensemble of multi-day aggregates from lagged ensembles,
   with aggregates created in valid time, and bias correction of that ensemble against
   observations. The "effective" ensemble and its aggregates are composed of individual
   simulations with different initialisation dates, and thus different lead times.

   The problem with this approach is that, because the forecast and hindcast ensembles
   are initialised at different times, the "effective" hindcast ensemble may not combine
   lead times across the aggregation windows in exactly the same way as the "effective"
   forecast ensemble.

Data structures
---------------

Structure of downloaded data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Forecast
   The lagged ensemble is aligned in valid time, and the data dimensions are
   ``(valid_time, member, latitude, longitude)``. Each member's initialisation date is
   stored in the coordinate ``fc_init_date`` (along ``member``). We call this the
   *valid time-aligned* data structure.

Hindcast
   The lagged ensemble is aligned in lead time, and the data dimensions are
   ``(hc_init_date, lead_time, member, latitude, longitude)``. We call this the
   *lead time-aligned* data structure.

Structure used in postprocessing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For processing, the most convenient structure, for both forecast and hindcast, is::

    (valid_time, effective_lead_time, member, latitude, longitude)

We call this the *effective lead time-aligned* structure. Each member also carries the
coordinates ``init_date`` (its actual initialisation date) and ``init_lag``
(``init_date - valid_time``), and the calendar date of every value is given by the
coordinate ``target_time = valid_time + effective_lead_time``.

Note that we distinguish between ``valid_time``, ``hc_init_date``, ``lead_time``,
``effective_lead_time`` and ``target_time``:

``valid_time``
   In the downloaded forecast, ``valid_time`` is the "real time", i.e. the calendar date
   that the data for a given day represent. It is the principal time axis of the data,
   and all members, whichever initialisation they come from, share the same
   ``valid_time``. For daily data it is 00:00:00Z of that day.

   In the effective lead time-aligned structure, ``valid_time`` has a different role:
   it labels each forecast (or each hindcast year) and is the date from which
   ``effective_lead_time`` is counted. The calendar date of each value is then
   ``target_time``.

``hc_init_date``
   The initialisation date of the hindcast. It is identical for all members initialised
   on a particular date. If data for one initialisation are requested, its size is the
   number of hindcast years, N\ :sub:`years`; for a lagged ensemble it is
   N\ :sub:`years` × N\ :sub:`lags`.

``lead_time``
   The time since the initialisation of the model simulation: the difference between
   the start of the period for which data are given (00:00:00Z of the first day of that
   period) and the time of initialisation (00:00:00Z of the initialisation date). It is
   stored as a timedelta (``timedelta64``).

``effective_lead_time``
   The lead time in the "effective" ensemble, i.e. the ensemble in which members are
   aligned in valid time and which is used to derive forecast products and hindcast
   skill. For hindcasts with members from a single initialisation it is the same as
   ``lead_time``. For lagged ensembles it is counted from the initialisation chosen as
   anchor: the most recent one when the ensemble is trimmed (``trim=True`` or
   ``anchor="latest"`` in :func:`~toolkit_extension.postprocess.hcst_to_effective_lead_time`),
   otherwise the earliest one. It is called differently from ``lead_time`` because, for
   members of the other initialisations, it differs from their own lead time:
   ``effective_lead_time = lead_time + init_lag``.

   For consistency, ``effective_lead_time`` is also used for forecast data. As for the
   trimmed hindcast, it is counted from the most recent initialisation (more precisely,
   from the first date from that initialisation on at which every member has data), and
   it is identical for all members of the lagged ensemble.

``target_time``
   The calendar date of each value, ``valid_time + effective_lead_time``.

Why is this structure convenient?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It allows the same bias correction and product generation functions to be applied to
both hindcast and forecast, in a way that facilitates the generation of standard
forecast products, i.e. products based on forecast data aggregated to weekly (or
similar) totals or indices. It also facilitates bespoke processing pipelines leading to
non-standard products, as explained below.

Building a processing pipeline
------------------------------

A processing pipeline transforms data from downloaded files into products, which
include forecast products but also skill and verification products. We distinguish two
types of pipeline:

Generation of forecast products from bias-corrected forecast data
   This pipeline works with forecast, hindcast and observations, and covers bias
   correction, generation of products and evaluation of hindcast skill. The resulting
   product file can later be used to verify the forecast against observations (once
   the observations are available).

Verification of a forecast
   This pipeline verifies individual forecasts once observational data are available.

Product generation pipeline
---------------------------

There are two principal ways of structuring the product generation pipeline::

    ingestion -> transformation -> bias correction -> aggregation -> product generation
    ingestion -> transformation -> aggregation -> bias correction -> product generation

They differ in when bias correction is done relative to aggregation: in the first, on
daily data, before aggregation; in the second, on aggregated data. Which path to choose
depends on the nature of the forecast product to be generated; this is illustrated in
the section presenting example pipelines.

In both, transformation comes before aggregation: the restructuring and temporal
alignment functions require daily data.

Ingestion
~~~~~~~~~

Ingestion reads the files with forecast, hindcast and observational data, and is done
with one function for all three:

- :func:`~toolkit_extension.postprocess.read_netcdf` opens a NetCDF file, extracts the
  requested variable and returns it as an ``xarray.DataArray`` rather than an
  ``xarray.Dataset``.

The download functions of this package provide forecast and hindcast data in a strictly
prescribed format, so for these the function mainly extracts the variable. Observational
data, however, can come from various sources and have various structures. The function
therefore harmonises coordinate names to the structure expected by the other
postprocessing, bias correction, product generation, skill and verification functions:
latitude and longitude are renamed to ``latitude`` and ``longitude`` (e.g. from ``lat``,
``lon``) in all files, and in observational files the time coordinate is renamed to
``time`` (e.g. from ``valid_time`` or ``date``).

In addition, the function checks that the data are daily (along ``time`` for
observations, ``lead_time`` for the hindcast and ``valid_time`` for the forecast), and
can set the units of the data (argument ``units``), which are carried through to the
products.

Transformation
~~~~~~~~~~~~~~

Transformation involves:

- restructuring forecast and hindcast data into the effective lead time-aligned
  structure;
- putting observations and model data on the same spatial grid;
- putting observations on the same temporal structure as the model data.

It is implemented with the following functions:

- :func:`~toolkit_extension.postprocess.hcst_to_effective_lead_time` restructures
  downloaded hindcast data into the effective lead time-aligned structure.
- :func:`~toolkit_extension.postprocess.fcst_to_effective_lead_time` does the same for
  forecast data; given the hindcast's lead times (argument ``leads``), it makes the
  forecast's lead-time axis identical to the hindcast's.
- :func:`~toolkit_extension.postprocess.align_grid` puts observations and model data on
  the same grid, in one of two directions: the observations are regridded
  conservatively to the (coarser) model grid (``direction="fine_to_coarse"``, the
  default), or the model data are interpolated bilinearly to the (finer) observation
  grid (``direction="coarse_to_fine"``). Grid cells without data in either dataset are
  set to missing in both.
- :func:`~toolkit_extension.postprocess.align_obs_to_model_time` creates an
  observational dataset that replicates the temporal structure of the hindcast or
  forecast: for every ``valid_time`` and ``effective_lead_time`` of the model it takes
  the observation at the corresponding ``target_time``.

Aggregation
~~~~~~~~~~~

As explained in the theory section, the skill of sub-seasonal forecasts manifests at
aggregation periods longer than one day. Aggregation derives these time aggregates from
daily data, with :func:`~toolkit_extension.postprocess.aggregate`. Daily lead times are
grouped into consecutive windows of 5 to 50 days; each aggregate is labelled with the
lead time at the start of its window, and an incomplete last window is dropped. The
available aggregation methods are:

- the mean, sum or maximum of the daily values;
- the number of days with a value of zero (``count_zero``);
- the number of days with a value above a threshold, whether consecutive or not
  (``count_above``);
- the longest run of consecutive days with values below a threshold, e.g. the longest
  dry spell (``max_dry_spell``).

Further methods can be added with
:func:`~toolkit_extension.postprocess.register_agg`.

Bias correction
~~~~~~~~~~~~~~~

Forecast model data carry different types of systematic and non-systematic errors.
Most errors cannot be reduced in postprocessing, but the systematic error, or bias, can.
Bias correction is implemented with several approaches, such as simple scaling and
various "flavours" of quantile mapping (for details see the API documentation).
Importantly, the bias correction function allows three different ways of pooling data
to calculate the bias correction transform:

fixed window
   The data are divided into a set of windows spanning different lead times, and the
   transform is derived separately for each window (and, of course, for each grid cell).

rolling window
   The data for each lead time are bias-corrected based on the data from a temporal
   window "surrounding" that lead time.

lead
   Each lead time is bias-corrected based on the data for that lead time only.

Bias correction is implemented in the function
:func:`~toolkit_extension.bias_correction.bias_correct`.

Product generation and hindcast skill evaluation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The generation of forecast products, namely deterministic and probabilistic forecasts,
is merged with the evaluation of hindcast skill, for efficiency and traceability.
Calculating skill requires the same data as generating products, and involves several
of the same processing steps, so it is efficient to bundle the two. Doing both in one
function produces a single data object that contains the forecast and its hindcast
skill. This reduces the possibility of errors such as associating a forecast with the
skill of a different forecast. In addition, a single product with forecast and hindcast
skill allows easy generation of forecast verification products, free of operator
errors (described below). The product also records the settings of the pipeline that
produced it: regridding, aggregation and bias correction.

Deterministic and probabilistic products are generated with two separate functions:

- :func:`~toolkit_extension.products.make_deterministic_product` derives the "best
  guess" forecast and hindcast, which is the ensemble mean, together with anomalies and
  percent anomalies relative to the climatology of the hindcast period.
- :func:`~toolkit_extension.products.make_probabilistic_product` derives the
  probabilities of categories. The category boundaries are given either as
  climatological quantiles (``quantiles``; by default terciles, ``[1/3, 2/3]``) or as
  absolute values of the variable (``thresholds``). With N boundaries the function
  derives probabilities for N + 1 categories; for example, with one threshold X, the
  probabilities of "below X" and "above X".

Both functions also evaluate the hindcast skill of the product. The toolkit implements a
range of skill measures following WMO recommendations; by default, the probabilistic
product stores the RPSS, 2AFC, ROC, BSS and Heidke skill score, and the deterministic
product the correlation, RMSE and bias.

Forecast verification pipeline
------------------------------

Once observations are available for the period covered by an issued forecast, the
forecast can be verified against them. The verification pipeline has two steps:

#. alignment of the observations with the data used to issue the forecast;
#. verification of the forecast against the aligned observations.

The pipeline used to derive the forecast product is user-determined (see above) and can
be convoluted. For verification, it has to be reproduced exactly on the new
observational data. The toolkit simplifies this because the forecast product records
the settings of that pipeline. The alignment function,
:func:`~toolkit_extension.postprocess.align_obs_to_product`, therefore needs only the
forecast product and the observations as returned by
:func:`~toolkit_extension.postprocess.read_netcdf`, and no additional information. It
repeats the steps applied to the hindcast-period observations: regridding to the
product grid, temporal alignment with the forecast, and aggregation. This ensures the
traceability of the process and reduces the possibility of operator errors.

The verification functions,
:func:`~toolkit_extension.verify_deterministic.verify_deterministic` and
:func:`~toolkit_extension.verify_probabilistic.verify_probabilistic`, implement a range
of forecast verification measures following WMO recommendations (WMO-No. 1220).
