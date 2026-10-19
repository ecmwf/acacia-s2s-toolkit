# SPDX-FileCopyrightText: 2024 European Centre for Medium-Range Weather Forecasts (ECMWF)
# SPDX-License-Identifier: Apache-2.0

import xarray as xr
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import datetime
import os,sys,glob
import pooch

from functools import partial

from xsdba_corrector import BiasCorrector, XsdbaCorrector


#this is for readthedocs to work correctly. These packages cannot be installed by pip, so one has to mock import them
autodoc_mock_imports = []

#this determines with functions will be publicly visible in the installed package
__all__=["bias_correct"]


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
        



# ---------


# --------------------------------------------------------------------------- bespoke method
class MeanVarCorrector(BiasCorrector):
    """
    Correction of mean and spread, per lead time and grid point.
 
    kind="+" (default; temperature and other unbounded variables) - mean/variance scaling:
        corrected = (sim - mean_hist) / std_hist * std_ref + mean_ref
    kind="*" (precipitation and other non-negative variables) - power transformation
    (Leander & Buishand 2007, J. Hydrol. 332):
        corrected = a * sim**b
        b is chosen so that the coefficient of variation (std/mean) of hist**b equals that of
        ref, then a so that the means match. Output is never negative and zeros stay zero.
        b is searched in [b_min, b_max]; where the target is outside that range, b is clipped
        and the spread is only partly corrected. Negative input values are set to 0.
 
    Statistics always pool all years (and, for the hindcast, all members). Pooling across
    lead times, as in XsdbaCorrector:
        "lead"    : statistics per lead time
        "rolling" : per lead time, from a centred window of `window_size` leads
                    (truncated at the first and last leads)
        "blocks"  : one set of statistics per block of `window_size` leads, used for every
                    lead in the block; a short last block is merged into the previous one
    """
 
    POOLINGS = ("lead", "rolling", "blocks")
 
    def __init__(self, lead_dim="effective_lead_time", member_dim="member",
                 pooling="lead", window_size=7, kind="+", b_min=0.1, b_max=4.0):
        if pooling not in self.POOLINGS:
            raise ValueError(f"pooling must be one of {self.POOLINGS}")
        if kind not in ("+", "*"):
            raise ValueError("kind must be '+' or '*'")
        self.lead_dim, self.member_dim = lead_dim, member_dim
        self.pooling, self.window_size, self.kind = pooling, int(window_size), kind
        self.b_grid = np.linspace(b_min, b_max, int(round((b_max - b_min) / 0.05)) + 1)
 
    def _stats(self, da, dims, power=None):
        """Mean and std of da (or da**power) over `dims`, pooled across leads per `pooling`.
        `power` may be a scalar or an array along (lead, ...); in a rolling window each
        window uses the power of its central lead."""
        L = self.lead_dim
        if self.pooling == "lead":
            x = da if power is None else da ** power
            return x.mean(dims), x.std(dims)
        if self.pooling == "rolling":
            w = da.rolling({L: self.window_size}, center=True).construct("_win")
            w = w if power is None else w ** power
            return w.mean(dims + ["_win"]), w.std(dims + ["_win"])
        # blocks: statistics per block, then mapped back onto every lead of the block
        # (power is constant within a block, because the statistics it is fitted to are)
        x = da if power is None else da ** power
        blocks = make_lead_blocks(da.sizes[L], self.window_size)
        block_of_lead = np.concatenate([np.full(len(b), i) for i, b in enumerate(blocks)])
        idx = xr.DataArray(block_of_lead, dims=L)
        g = x.assign_coords(_block=(L, block_of_lead)).groupby("_block")
        mean = g.mean(dims + [L]).isel(_block=idx).drop_vars("_block")
        std = g.std(dims + [L]).isel(_block=idx).drop_vars("_block")
        return mean.assign_coords({L: da[L]}), std.assign_coords({L: da[L]})
 
    def _fit_power(self, ref, hist, hdims):
        """Exponent b with CV(hist**b) = CV(ref), by linear interpolation on b_grid."""
        r_mean, r_std = self._stats(ref, [self.init_dim])
        target = r_std / r_mean
        cv = xr.concat([(lambda m, s: s / m)(*self._stats(hist, hdims, power=b))
                        for b in self.b_grid], dim="_b")          # increases with b
        target = target.broadcast_like(cv.isel(_b=0))
        cvv = cv.transpose("_b", *target.dims).values
        tv = target.values
        above = cvv >= tv[None]
        k = np.clip(np.argmax(above, axis=0), 1, len(self.b_grid) - 1)  # first b with cv >= target
        k = np.where(above.any(axis=0), k, len(self.b_grid) - 1)
        lo = np.take_along_axis(cvv, (k - 1)[None], 0)[0]
        hi = np.take_along_axis(cvv, k[None], 0)[0]
        frac = np.clip(np.where(hi > lo, (tv - lo) / (hi - lo), 1.0), 0, 1)
        b = self.b_grid[k - 1] + frac * (self.b_grid[k] - self.b_grid[k - 1])
        b = np.where(np.isfinite(tv) & np.isfinite(cvv).all(axis=0), b, np.nan)
        b = xr.DataArray(b, dims=target.dims, coords=target.coords)
        h_mean_b, _ = self._stats(hist, hdims, power=b)
        a = (r_mean / h_mean_b).where(h_mean_b > 0, 0.0)
        return a, b
 
    def fit(self, ref, hist):
        self._lead = hist[self.lead_dim].values
        hdims = [self.init_dim, self.member_dim]
        if self.kind == "*":
            hist, ref = hist.clip(min=0), ref.clip(min=0)
            self.a, self.b = self._fit_power(ref, hist, hdims)
        else:
            self.h_mean, self.h_std = self._stats(hist, hdims)
            self.r_mean, self.r_std = self._stats(ref, [self.init_dim])
        return self
 
    def apply(self, sim):
        # arithmetic aligns on lead labels; mismatched leads would silently disappear
        if not np.array_equal(sim[self.lead_dim].values, self._lead):
            raise ValueError(f"'{self.lead_dim}' of sim differs from the training data")
        if self.kind == "*":
            out = self.a * sim.clip(min=0) ** self.b
        else:
            out = (sim - self.h_mean) / self.h_std * self.r_std + self.r_mean
        return out.transpose(*sim.dims).assign_attrs(sim.attrs)
 



# --------------------------------------------------------------------------- registry
REGISTRY: dict[str, object] = {}
 
 
def register(name, corrector):
    """Make a corrector available to bias_correct under `name`.
    corrector : class (or callable) returning a BiasCorrector; called with
                lead_dim=..., member_dim=... and the user's options."""
    REGISTRY[name] = corrector
 
 
for _m in ("eqm", "scaling", "dqm"):
    register(_m, partial(XsdbaCorrector, _m))
register("meanvar", MeanVarCorrector)
 


def _match_leads(fcst, hcst, lead_dim):
    """Restrict the forecast to the hindcast's lead times. Staggered inits can leave the
    forecast with extra leads; leads the hindcast has but the forecast lacks are an error."""
    f, h = fcst[lead_dim].values, hcst[lead_dim].values
    missing = h[~np.isin(h, f)]
    if missing.size:
        raise ValueError(f"forecast lacks hindcast lead times {missing}")
    extra = f[~np.isin(f, h)]
    if extra.size:
        _log(f"bias_correct: dropping {extra.size} forecast lead times not in the hindcast: {extra}")
        fcst = fcst.sel({lead_dim: h})
    return fcst
    
def _to_points(da: xr.DataArray, mask: xr.DataArray, *, lat: str = "latitude", lon: str = "longitude") -> xr.DataArray:
    """
    Replace (lat, lon) with a single 'point' dimension holding only cells where `mask` is True
    (e.g. land). lat/lon are kept as plain coordinates along 'point' (no MultiIndex, which
    xsdba cannot handle). Skipping masked cells avoids all-NaN warnings and wasted work.
    """
    st = da.stack(point=(lat, lon))
    keep = mask.stack(point=(lat, lon)).values.astype(bool)
    lats, lons = st[lat].values[keep], st[lon].values[keep]
    out = st.drop_vars(["point", lat, lon]).isel(point=np.flatnonzero(keep))
    return out.assign_coords({lat: ("point", lats), lon: ("point", lons)})

     
def _from_points(da: xr.DataArray, grid: xr.DataArray, *, lat: str = "latitude", lon: str = "longitude") -> xr.DataArray:
    """
    Inverse of to_points: put 'point' data back onto the full lat/lon grid, NaN in masked cells.
 
    grid : any array with `lat` and `lon` as dimensions that defines the full grid, e.g. the
           land mask or the original gridded data (not the output of to_points).
    The other dimensions keep their order; (lat, lon) take the place of 'point'.
    """
    if lat not in grid.dims or lon not in grid.dims:
        raise ValueError(f"`grid` must have '{lat}' and '{lon}' as dimensions "
                         "(pass the land mask or the original gridded array)")
    order = []
    for d in da.dims:
        order.extend([lat, lon] if d == "point" else [d])
    out = da.set_index(point=[lat, lon]).unstack("point")
    out = out.reindex({lat: grid[lat].values, lon: grid[lon].values})
    return out.transpose(*order).assign_coords({lat: grid[lat], lon: grid[lon]})
 

    
# --------------------------------------------------------------------------- format conversion
def _to_bc(da, mask, units, init_dim, member_dim):
    """Package format -> corrector format."""
    # non-index coords and member labels go (member labels would make xsdba align the
    # forecast against the hindcast's members); they are restored from the original later
    out = da.reset_coords(drop=True).drop_vars(member_dim, errors="ignore")
    out = out.rename({init_dim: "time"})
    if units is None:
        if "units" not in out.attrs:
            raise ValueError("data have no 'units' attribute; pass units=...")
    else:
        out = out.assign_attrs(units=units)
    if mask is None:
        return out
    lat, lon = mask.dims
    return _to_points(out, mask, lat=lat, lon=lon)
 
 
def _from_bc(da, like, mask, init_dim):
    """Corrector format -> package format of `like` (the original array)."""
    if mask is not None:
        lat, lon = mask.dims
        da = _from_points(da, grid=mask, lat=lat, lon=lon)
    out = da
    out = out.rename({"time": init_dim})
    out = out.assign_coords({c: like[c] for c in like.coords if c not in out.coords})
    out = out.transpose(*like.dims)
    if out.sizes != like.sizes:
        raise RuntimeError(f"size mismatch: {dict(out.sizes)} vs {dict(like.sizes)}")
    return out
 



import inspect
import warnings

def _accepted_options(factory, options):
    """Split options into those the corrector accepts and those it doesn't."""
    params = inspect.signature(factory).parameters
    if any(p.kind is p.VAR_KEYWORD for p in params.values()):    # takes **kwargs: pass all
        return options, {}
    used = {k: v for k, v in options.items() if k in params}
    unused = {k: v for k, v in options.items() if k not in params}
    return used, unused
    


# --------------------------------------------------------------------------- entry point
def bias_correct(obs, hcst, fcst=None, method="eqm", *, cv=True, pooling="lead", window_size=7, leave_out=1, mask="auto",
                 units=None, return_model=False, init_dim="valid_time",
                 lead_dim="effective_lead_time", member_dim="member", **options):
    """
    Bias-correct a hindcast and a forecast.
 
    Parameters
    ----------
    obs   : (valid_time, lead, lat, lon) observations aligned to hcst (see align_obs);
            a member dimension of identical copies is allowed
    hcst  : (valid_time, lead, member, lat, lon)
    fcst  : (valid_time, lead, member, lat, lon), optional; any number of members, same leads
    method : name in REGISTRY ("eqm", "scaling", "dqm", "meanvar", or your own)
    cv : if True the returned hindcast is cross-validated (leave_out years at a time), as
         needed for skill assessment; if False it is corrected in-sample. The forecast is
         always corrected with the model fitted on all years.
    mask : "auto" (cells where obs have any data), a boolean (lat, lon) array, or None.
           Cells outside the mask are not corrected and are NaN in the output.
    units : 'units' attribute if the data have none (required by xsdba methods).
    return_model : also return the corrector fitted on all years.
    **options : method options, e.g. pooling, window_size, nquantiles, kind, interp
                (see XsdbaCorrector for the xsdba methods).
 
    Returns
    -------
    hcst_bc, fcst_bc            (fcst_bc is None if fcst is None)
    hcst_bc, fcst_bc, model     if return_model
    """
    if method not in REGISTRY:
        raise ValueError(f"unknown method '{method}'; available: {list(REGISTRY)}")
 
    if member_dim in obs.dims:                                  # broadcast copies -> drop
        obs = obs.isel({member_dim: 0}, drop=True)
    if isinstance(mask, str) and mask == "auto":
        mask = obs.notnull().any([init_dim, lead_dim])
 
    ref = _to_bc(obs, mask, units, init_dim, member_dim)
    hist = _to_bc(hcst, mask, units, init_dim, member_dim)
    
    factory = REGISTRY[method]
    used, unused = _accepted_options(factory, options)
    if unused:
        warnings.warn(f"method '{method}' ignores options {sorted(unused)}")
    model = factory(lead_dim=lead_dim, member_dim=member_dim, **used).fit(ref, hist)

    
    if cv:
        hist_bc = model.fit_apply_loo(ref, hist, leave_out)
    else:
        hist_bc=model.apply(hist)
        
    hcst_bc = _from_bc(hist_bc, hcst, mask, init_dim)
 
    hcst_bc.attrs["S2STK_bc_method"]=method
    hcst_bc.attrs["S2STK_bc_pooling"]=pooling
    hcst_bc.attrs["S2STK_bc_window_size"]=window_size
    hcst_bc.attrs["S2STK_cv"]=str(cv)
    
    fcst_bc = None
    
    if fcst is not None:
        print("fcst")
        fcst = _match_leads(fcst, hcst, lead_dim)
        sim = _to_bc(fcst, mask, units, init_dim, member_dim)
        fcst_bc = _from_bc(model.apply(sim), fcst, mask, init_dim)
        
        fcst_bc.attrs["S2STK_bc_method"]=method
        fcst_bc.attrs["S2STK_bc_pooling"]=pooling
        fcst_bc.attrs["S2STK_bc_window_size"]=window_size
        
    
    if return_model:
        return (hcst_bc, fcst_bc, model) 
    else:
        return (hcst_bc, fcst_bc)





























