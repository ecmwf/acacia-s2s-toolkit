# SPDX-FileCopyrightText: 2024 European Centre for Medium-Range Weather Forecasts (ECMWF)
# SPDX-License-Identifier: Apache-2.0

# scripts relevant for merging multiple forecast
import xarray as xr
import numpy as np
import pandas as pd
from glob import glob
from pathlib import Path

def cleanup_idx_files(filename_prefix):
    for path_str in glob(f"{filename_prefix}*.idx"):
        path = Path(path_str)
        if path.is_file():
            path.unlink()

def refine_combined_array(combined,leveltype,rf=False):
    if rf:
        if leveltype == 'pressure':
            if 'isobaricInhPa' in combined.dims:
                combined = combined.rename({'isobaricInhPa':'level'})
            # Only transpose dims that actually exist
            combined = combined.transpose(
                *[d for d in ['hc_init_date','lead_time','member','level','latitude','longitude'] if d in combined.dims]
            )
        else:
            combined = combined.transpose(
                *[d for d in ['hc_init_date','lead_time','member','latitude','longitude'] if d in combined.dims]
            )
    else:
        if leveltype == 'pressure':
            if 'isobaricInhPa' in combined.dims:
                combined = combined.rename({'isobaricInhPa':'level'})
            # Only transpose dims that actually exist
            combined = combined.transpose(
                *[d for d in ['valid_time','member','level','latitude','longitude'] if d in combined.dims]
            )
        else:
            combined = combined.transpose(
                *[d for d in ['valid_time','member','latitude','longitude'] if d in combined.dims]
            )
    return combined

def merge_all_ens_members(filename, leveltype):
    filenames = sorted(
        glob(f"{filename}_allens_*.nc"),
        key=lambda x: int(x.split("_allens_")[-1].replace(".nc", "")),
    )  # sort filenames so largest lag goes first
    prepared = []
    member_offset = 0

    for fn in filenames:
        with xr.open_dataset(fn) as ds_in:
            n_members = ds_in.sizes["number"]

            # Preserve the original step as lead_time before replacing the dimension
            ds = ds_in.assign_coords(lead_time=("step", ds_in["step"].values))

            # Use the existing valid_time as the dimension
            ds = (
                ds.swap_dims({"step": "valid_time"})
                .drop_vars("step")
                .rename({"number": "member"})
            )

            # Give every member a unique index across all lagged forecasts
            ds = ds.assign_coords(
                member=np.arange(
                    member_offset, member_offset + n_members, dtype=np.int32
                )
            )

            # Each lag has a different initialisation time.
            # Expand it so it becomes time(member).
            init_time = ds["time"].values
            ds = ds.drop_vars("time").assign_coords(
                fc_init_date=("member", np.full(n_members, init_time))
            )

            # Expand lead_time(valid_time) to lead_time(valid_time, member)
            lead_time, _ = xr.broadcast(ds["lead_time"], ds["member"])
            ds = ds.assign_coords(lead_time=lead_time)

            # Load into memory so data remains valid after file closes
            ds = ds.load()

            prepared.append(ds)
            member_offset += n_members

    if np.size(filenames) == 1:
        combined = prepared[0]
    else:
        combined = xr.concat(
            prepared,
            dim="member",
            join="exact",  # Require identical valid_time values
            data_vars="minimal",
            coords="minimal",
            compat="override",
        )

    return combined

def merge_all_ens_hindcasts(filename, leveltype):
    filenames = sorted(
        glob(f"{filename}_allens_*.nc"),
        key=lambda x: int(x.split("_allens_")[-1].replace(".nc", "")),
    )  # sort filenames so largest lag goes first
    prepared = []

    for fn in filenames:
        with xr.open_dataset(fn) as ds_in:
            n_members = ds_in.sizes["number"]

            # Preserve the original step as lead_time before replacing the dimension
            ds = ds_in.assign_coords(lead_time=("step", ds_in["step"].values))

            # Use the existing lead_time as the dimension
            ds = (
                ds.swap_dims({"step": "lead_time"})
                .drop_vars("step")
                .rename({"number": "member"})
            )

            # Give every member a unique index across all lagged forecasts
            ds = ds.assign_coords(member=np.arange(ds.sizes["member"], dtype=np.int32))

            # Each lag has a different initialisation time.
            # Use hc_init_date as the dimension.
            ds = ds.assign_coords(hc_init_date=("time", ds["time"].values))
            ds = ds.swap_dims({"time": "hc_init_date"}).drop_vars("time")

            # Expand lag(member) to lag(hc_init_date, member)
            lag_2d = np.broadcast_to(
                ds["lag"].values,
                (ds.sizes["hc_init_date"], ds.sizes["member"]),
            )
            ds = ds.drop_vars("lag").assign_coords(
                lag=(("hc_init_date", "member"), lag_2d)
            )

            # Load into memory so data remains valid after file closes
            ds = ds.load()

        prepared.append(ds)

    if np.size(filenames) == 1:
        combined = prepared[0]
    else:
        combined = xr.concat(
            prepared,
            dim="hc_init_date",
            join="exact",  # Require identical lead_time values
            coords="minimal",
            compat="override",
        )

    return combined

