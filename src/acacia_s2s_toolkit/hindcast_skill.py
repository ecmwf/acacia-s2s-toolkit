# SPDX-FileCopyrightText: 2024 European Centre for Medium-Range Weather Forecasts (ECMWF)
# SPDX-License-Identifier: Apache-2.0

import xarray as xr
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import datetime
import os,sys,glob
import xesmf as xe
import pooch


#this is for readthedocs to work correctly. These packages cannot be installed by pip, so one has to mock import them
autodoc_mock_imports = []

#this determines with functions will be publicly visible in the installed package
__all__=["hindcast_deterministic_skill", "hindcast_probabilistic_skill", "deterministic_hindcast", "probabilistic_hindcast", "get_obs_category"]


#######################################################################################

#
# helper functions
#
#######################################################################################



VERBOSE = True

def set_verbose(v):
    global VERBOSE
    VERBOSE = v
    print("logging is {}".format(v))

def _log(msg, force=False):
    if VERBOSE | force:
        print(msg)
        

def _safe_quantile(obs, q, dim):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="All-NaN slice encountered")
        return obs.quantile(q, dim=dim, skipna=True)



    

#######################################################################################
#
# callable functions to get hindcast. should go to postprocessing.py, but parking them here fore the time being
#
#######################################################################################


def deterministic_hindcast(hcst, obs, method="mean", index="value"):
    if method=="mean":
        hcstmean=hcst.mean("member")
    elif method=="median":
        hcstmean=hcst.median("member")
    else:
        raise ValueError(f"Can only take mean or median, got {method}")

    if index=="value":        
        return hcstmean
    elif index=="absanom":
        return hcstmean-obs.mean("valid_time")
    elif index=="relanom":
        # in % of mean
        return (hcstmean-obs.mean("valid_time"))/obs.mean("valid_time")*100
        



def probabilistic_hindcast(
    hcst, obs, quant_thresh=None, other_thresh=None, abs_thresh=None,
    exceed="above", method="count"
):
    # hcst: (valid_time, lead_time, member, lat, lon)
    # obs:  (valid_time, lead_time, lat, lon)
    # quant_thresh - quantile threshold of the obs distribution
    # abs_thresh   - absolute threshold value
    # exceed       - "above" or "below"
    # other_thresh - defines the other end of a range, if given
    # method       - "count" (fraction of members exceeding threshold)

    time_dim="valid_time"
    
    if quant_thresh is None and abs_thresh is None:
        raise ValueError("either quant_thresh or abs_thresh have to be provided")

    if quant_thresh is not None and abs_thresh is not None:
        raise ValueError(
            "either quant_thresh or abs_thresh have to be provided, but not both at the same time"
        )

    valid_exceeds = ["above", "below"]
    if exceed not in valid_exceeds:
        raise ValueError(f"exceed has to be one of {valid_exceeds}")

    valid_methods = ["count"]
    if method not in valid_methods:
        raise ValueError(f"method has to be one of {valid_methods}")

    if quant_thresh is not None and not (0 <= quant_thresh <= 1):
        raise ValueError(f"quant_thresh must be in the range of 0 <= quant_thresh <= 1, got {quant_thresh}")

    for threshname, thresh in [("quant_thresh", quant_thresh), ("abs_thresh", abs_thresh)]:
        if thresh is not None and other_thresh is not None:
            if exceed == "above" and other_thresh <= thresh:
                raise ValueError(
                    f"got exceed='above' so other_thresh has to be > {threshname}, "
                    f"got other_thresh={other_thresh} and {threshname}={thresh}"
                )
            if exceed == "below" and other_thresh >= thresh:
                raise ValueError(
                    f"got exceed='below' so other_thresh has to be < {threshname}, "
                    f"got other_thresh={other_thresh} and {threshname}={thresh}"
                )

    # calculating...

    spatial_nan_mask = np.isnan(obs).all([time_dim, "lead_time"])
        
    # 1. resolve threshold(s) to absolute value(s)
    if abs_thresh is not None:
        thresh = abs_thresh
        other_thresh_abs = other_thresh  # already absolute, or None
    else:
        #thresh=_safe_quantile(obs, quant_thresh, time_dim)
        thresh = obs.quantile(quant_thresh, dim=time_dim, skipna=True)
        if other_thresh is not None:
            #other_thresh_abs=_safe_quantile(obs, quant_thresh, time_dim)
            other_thresh_abs = obs.quantile(other_thresh, dim=time_dim, skipna=True)
        else:
            other_thresh_abs = None

    # 2. compute probability
    if method == "count":
        if other_thresh_abs is None:
            if exceed == "above":
                mask = hcst > thresh
            else:
                mask = hcst < thresh
        else:
            if exceed == "above":
                lo, hi = thresh, other_thresh_abs
            else:
                lo, hi = other_thresh_abs, thresh
            mask = (hcst > lo) & (hcst < hi)

        prob = mask.mean(dim="member")

    prob.name = "probability"
    prob.attrs["quant_thresh"] = quant_thresh
    prob.attrs["abs_thresh"] = abs_thresh
    prob.attrs["other_thresh"] = other_thresh
    prob.attrs["exceed"] = exceed
    prob.attrs["method"] = method
    
    #removing all nans
    prob = prob.where(~spatial_nan_mask)    
    return prob
    

def get_obs_category(obs, quant_thresh=None, abs_thresh=None, dim="valid_time"):
    """
    Assign each obs value to an integer category based on a set of boundaries.
    
    quant_thresh : list of quantiles (e.g. [1/3, 2/3] for terciles), resolved
                   to absolute boundaries via obs's own distribution.
    abs_thresh   : list of absolute boundary values, used directly.
    dim          : dimension over which quantiles are computed (if quant_thresh given).
    
    Returns
    -------
    obs_category : same shape as obs (minus `dim` if boundaries vary along it... 
                    actually same shape as obs, since categorization is per-timestep)
    """
    
    time_dim="valid_time"
    
    if quant_thresh is None and abs_thresh is None:
        raise ValueError("either quant_thresh or abs_thresh have to be provided")
    if quant_thresh is not None and abs_thresh is not None:
        raise ValueError("either quant_thresh or abs_thresh have to be provided, but not both")

    if quant_thresh is not None:
        if not all(0 <= q <= 1 for q in quant_thresh):
            raise ValueError(f"all quant_thresh values must be in [0, 1], got {quant_thresh}")
        if list(quant_thresh) != sorted(quant_thresh):
            raise ValueError(f"quant_thresh must be sorted ascending, got {quant_thresh}")
        boundaries = obs.quantile(quant_thresh, dim=dim, skipna=True)
    else:
        if list(abs_thresh) != sorted(abs_thresh):
            raise ValueError(f"abs_thresh must be sorted ascending, got {abs_thresh}")
        # wrap as a DataArray with a matching 'quantile'-like dim for consistent indexing below
        boundaries = xr.DataArray(
            abs_thresh, dims=["threshold"], coords={"threshold": abs_thresh}
        )
        
    spatial_nan_mask = np.isnan(obs).all([time_dim, "lead_time"])

    boundary_dim = "quantile" if quant_thresh is not None else "threshold"
    boundary_vals = boundaries[boundary_dim].values

    obs_category = xr.zeros_like(obs, dtype=int)
    for b in boundary_vals:
        obs_category = obs_category + (obs > boundaries.sel({boundary_dim: b}))

    #removing all nans
    obs_category = obs_category.where(~spatial_nan_mask)
    
    return obs_category


#######################################################################################
#
# callable functions to evaluate hindcast skill
#
#######################################################################################

def hindcast_probabilistic_skill(score, **inputs):


    def _find_family(score):
        for family, names in skill_scores.items():
            if score in names:
                return family
        return None
    
    skill_scores = {
        "prob_binary": ["brier", "2afc"],
        "ensemble_obs": ["crps"],
        "categorical": ["heidke"],
    }
    
    family = _find_family(score)
    if family is None:
        all_scores = [s for names in skill_scores.values() for s in names]
        raise ValueError(f"Unknown skill score '{score}'. Available: {all_scores}")

    func = PROB_SKILL_FUNCTIONS[score]

    if family == "categorical":
        hcst_prob = inputs["hcst_prob"]
        obs_cat = inputs["obs_cat"]
        skill = xr.apply_ufunc(
            func, hcst_prob, obs_cat,
            input_core_dims=[["valid_time","category"], ["valid_time"]],
            output_core_dims=[[]],
            vectorize=True,
            dask="parallelized",
            output_dtypes=[float],
        )

    elif family == "ensemble_obs":
        ens_fcst = inputs["ens_fcst"]
        obs = inputs["obs"]
        skill = xr.apply_ufunc(
            func, ens_fcst, obs,
            input_core_dims=[["member", "valid_time"], ["valid_time"]],
            output_core_dims=[[]],
            vectorize=True,
            dask="parallelized",
            output_dtypes=[float],
        )

    elif family == "prob_binary":
        prob_fcst = inputs["prob_fcst"]
        obs_binary = inputs["obs_binary"]
        skill = xr.apply_ufunc(
            func, prob_fcst, obs_binary,
            input_core_dims=[["valid_time"], ["valid_time"]],
            output_core_dims=[[]],
            vectorize=True,
            dask="parallelized",
            output_dtypes=[float],
        )

    else:
        raise ValueError(f"Unhandled family '{family}' for score '{score}'")

    return skill
    
    
def hindcast_deterministic_skill(hcst, obs, score):
    #both hcst and obs should come as array with (valid_time), 
    
    #checking if score is available
    if score not in DET_SKILL_FUNCTIONS:
        raise ValueError(
            f"Unknown skill score '{score}'. "
            f"Available: {list(SKILL_FUNCTIONS)}"
        )
        
    #picking up requested score
    func = DET_SKILL_FUNCTIONS[score]
    
    skill=xr.apply_ufunc(
        func,
        hcst,
        obs,
        input_core_dims=[["valid_time"], ["valid_time"]],
        output_core_dims=[[]],
        vectorize=True,
        dask="parallelized",
    )
    return skill
    


#######################################################################################
#
# skill score functions
#
#######################################################################################
    

PROB_SKILL_FUNCTIONS = {}

def register_prob_skill(name):
    """Register a core skill function under a name."""
    def wrapper(func):
        PROB_SKILL_FUNCTIONS[name] = func
        return func
    return wrapper

@register_prob_skill("heidke")
def heidke_skill_score(forecast_probs, obs_category):
        
    fcst=np.argmax(forecast_probs, axis=1)
    
    categories = np.unique(np.concatenate([obs_category, fcst]))
    K = len(categories)
    N_t = len(obs_category)
    
    # contingency counts per category
    N_f = np.array([np.sum(fcst == k) for k in categories])
    N_o = np.array([np.sum(obs_category == k) for k in categories])
    N_c = np.sum(obs_category == fcst)  # number of correct forecasts
    
    N_e = np.sum(N_f * N_o) / N_t  # expected correct by chance
    HSS = (N_c - N_e) / (N_t - N_e)
    return HSS

@register_prob_skill("brier")
def brier_skill_score(forecast_probs, obs_categories):    
    n_instances = len(obs_categories)
    n_categories = forecast_probs.shape[1]

    # one-hot encoding of observations
    obs_onehot = np.zeros_like(forecast_probs)
    obs_onehot[np.arange(n_instances), obs_categories] = 1
    
    brier = np.mean(np.sum((forecast_probs - obs_onehot)**2, axis=1))
    return brier


@register_prob_skill("2afc")
def two_afc_multicategory(forecast_probs, obs):
    """
    Compute generalized 2AFC score for 3-category forecast.
    forecast_probs: np.array of shape (n_samples, 3)
    obs: np.array of shape (n_samples,) with values 0, 1, 2
    """
    scores = []
    
    for cat in range(3):
        correct = 0
        total = 0
        
        # Indices where obs is in current category (event)
        idx_event = np.where(obs == cat)[0]
        # Indices where obs is not in current category (non-event)
        idx_nonevent = np.where(obs != cat)[0]
        
        for i in idx_event:
            for j in idx_nonevent:
                f_i = forecast_probs[i, cat]
                f_j = forecast_probs[j, cat]
                
                if f_i > f_j:
                    correct += 1
                elif f_i == f_j:
                    correct += 0.5
                total += 1
                
        score = correct / total if total > 0 else np.nan
        scores.append(score)
        
    return np.nanmean(scores)

@register_prob_skill("rps")
def rps_score(forecast_probs, observed_class, n_categories=3):
    # forecast_probs: array of shape (n_samples, n_categories)
    # observed_class: array of shape (n_samples,), with integer values 0, 1, ..., K-
    rps = 0
    for i in range(len(observed_class)):
        obs = np.zeros(n_categories)
        obs[observed_class[i]] = 1
        obs_cum = np.cumsum(obs)
        forecast_cum = np.cumsum(forecast_probs[i])
        rps += np.sum((forecast_cum - obs_cum) ** 2)
    return rps / len(observed_class)


@register_prob_skill("rpss")
def rpss_score(forecast_probs, climatology_probs, observed_class):
    rps_forecast = rps_score(forecast_probs, observed_class)
    rps_climatology = rps_score(np.tile(climatology_probs, (len(observed_class), 1)), observed_class)
    return 1 - rps_forecast / rps_climatology


@register_prob_skill("ignorance")
def ignorance_score(forecast_probs, observed_class):
    # Clip probabilities to avoid log(0)
    eps = 1e-15
    prob = np.clip(forecast_probs, eps, 1-eps)
    # Select the probability assigned to the observed category
    p_observed = prob[np.arange(len(observed_class)), observed_class]

    # Compute ignorance
    ignorance = -np.log2(p_observed)

    # Mean ignorance over all instances
    mean_ignorance = np.mean(ignorance)

    return mean_ignorance

@register_prob_skill("effintrate")    
def effective_interest_rate(forecast_probs, obs):

    # Clip probabilities to avoid log(0)
    eps = 1e-15
    prob = np.clip(forecast_probs, eps, 1-eps)

    # 1. Ignorance of forecast
    p_obs = prob[np.arange(len(obs)), obs]
    I_forecast = -np.log2(p_obs)

    # 2. Reference probabilities (climatology)
    obs_onehot = np.zeros_like(prob)
    obs_onehot[np.arange(len(obs)), obs] = 1
    clim_prob = obs_onehot.mean(axis=0)

    p_ref = clim_prob[obs]
    I_ref = -np.log2(p_ref)

    # 3. Effective information
    info_gain = I_ref - I_forecast
    mean_info_gain = np.mean(info_gain)
    
    return mean_info_gain

@register_prob_skill("groc")
def groc_score(probs, obs):
    """
    Calculate the Generalized ROC (GROC) skill score.
    
    Parameters
    ----------
    probs : np.ndarray
        Array of forecast probabilities with shape (N, C),
        where N = number of forecasts, C = number of categories.
    obs : np.ndarray
        Array of observed categories with shape (N,), 
        integers in [0, C-1].
        
    Returns
    -------
    groc : float
        GROC value (0–1).
    groc_skill : float
        GROC skill score (-1–1).
    """
    N, C = probs.shape
    
    scores = []
    
    for i in range(N):
        p_obs = probs[i, obs[i]]
        
        for c in range(C):
            if c == obs[i]:
                continue
            p_other = probs[i, c]
            
            if p_obs > p_other:
                scores.append(1.0)
            elif p_obs == p_other:
                scores.append(0.5)
            else:
                scores.append(0.0)
    
    groc = np.mean(scores)
    groc_skill = 2 * (groc - 0.5)  # normalize to [-1, 1]
    
    return groc

@register_prob_skill("crps")
def _crps_core(ens_fcst, obs):
    import properscoring as ps
    return np.mean(ps.crps_ensemble(obs, ens_fcst.T))
    
    


    
# registry of available deterministic skill functions
DET_SKILL_FUNCTIONS = {}

def register_det_skill(name):
    """Decorator to register an aggregation function under a name."""
    def wrapper(func):
        DET_SKILL_FUNCTIONS[name] = func
        return func
    return wrapper


@register_det_skill("rmse")
def rmse(hc_1d, ob_1d):
    
    hc_1d = hc_1d[~np.isnan(hc_1d)]
    ob_1d = ob_1d[~np.isnan(ob_1d)]
    if len(hc_1d) < 2 or len(ob_1d) < 2:
        return np.nan

    rmse=np.mean((hc_1d-ob_1d)**2)**0.5
    return rmse

