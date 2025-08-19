# scripts relevant for merging multiple forecast
import xarray as xr
import numpy as np

def merge_all_ens_members(filename,leveltype):
    # open all ensemble members. drop step and time variables. Just use valid time.
    all_fcs = xr.open_mfdataset(f'{filename}_allens_*',engine='cfgrib',combine='nested',concat_dim='step') # open mfdataset but have step as a dimension
    all_fcs = all_fcs.drop_vars(['step','time'])
    all_fcs = all_fcs.rename({'valid_time':'time'})

    # make step == valid time
    if np.size(all_fcs.time)==1: # means only one set of forecasts/hindcasts have been chosen
        all_fcs = all_fcs.rename_dims({'step': 'member'})
    else:
        if 'time' not in all_fcs.dims:
            all_fcs = all_fcs.swap_dims({'step':'time'}) # change step dimension to time

    member_based_fcs = []

    # go through every time stamp and make a dataset with a 'member' dimension that combines all that have the same time.
    if np.size(all_fcs.time) > 1: # only if you have more than one forecast time period
        for time, group in all_fcs.groupby('time'):
            member_stack = group.stack(member=('number','time'))
            member_stack = member_stack.assign_coords(member=np.arange(np.size(group['time'])*np.size(group['number'])))
            member_stack = member_stack.expand_dims(time=[time])
            member_based_fcs.append(member_stack)
        combined = xr.concat(member_based_fcs,dim='time')
    else:
        combined = all_fcs.expand_dims(time=[all_fcs.time.values])

    if leveltype == 'pressure':
        combined = combined.rename({'isobaricInhPa':'level'})
        combined = combined.transpose('time','member','level','latitude','longitude')
    else:
        combined = combined.transpose('time','member','latitude','longitude')

    return combined


