# scripts relevant for merging multiple forecast
import xarray as xr
import numpy as np

def merge_all_ens_members(filename,leveltype):
    # open all ensemble members. drop step and time variables. Just use valid time.
    all_fcs = xr.open_mfdataset(f'{filename}_allens_*',engine='cfgrib',combine='nested',concat_dim='fc_init_member') # open mfdataset but have fc_init_member as a dimension
        
    if "fc_init_member" not in all_fcs.dims: # in case only one member is downloaded
        all_fcs = all_fcs.expand_dims("fc_init_member")

    if np.size(all_fcs.fc_init_member) == 1: # if only one forecast member is present
        if "valid_time" not in all_fcs.dims:
            if "valid_time" not in all_fcs.coords:
                all_fcs = all_fcs.expand_dims("valid_time")
            else:
                all_fcs = all_fcs.swap_dims({"step":"valid_time"})
        all_fcs = all_fcs.drop_vars(['step','time'])
    else: # concatenating forecasts from lagged ensemble. 
        all_data = []
        for fc_member in all_fcs.fc_init_member:
            single_mem = all_fcs.sel(fc_init_member=fc_member)
            nan_mask = ~np.isnan(single_mem['valid_time'].values)
            single_mem_sel = single_mem.sel(step=nan_mask)
            single_mem_sel = single_mem_sel.swap_dims({"step":"valid_time"})
            single_mem_sel = single_mem_sel.drop_vars(['step','time'])
            all_data.append(single_mem_sel)
        all_fcs = xr.concat(all_data,dim='fc_init_member')

    # stack, forecast init member and nunber
    combined = all_fcs.stack(member=("fc_init_member", "number")).reset_index("member", drop=True)
    combined = combined.rename({'valid_time':'time'})

    # put forecast initialisation time as an attribute
    try: # try adding forecast initialisation time (slightly off if lagged ensemble) - something to fix. 
        if np.size(all_fcs['time']) == 1:
            combined.attrs['Forecast_initialisation_time'] = str(all_fcs['time'].values)
    except:
        pass

    if leveltype == 'pressure':
        combined = combined.rename({'isobaricInhPa':'level'})
        combined = combined.transpose('time','member','level','latitude','longitude')
    else:
        combined = combined.transpose('time','member','latitude','longitude')

    return combined

def merge_all_ens_hindcasts(filename,leveltype):
    all_fcs = xr.open_mfdataset(f'{filename}_allens_*',combine='nested',concat_dim='fc_init_member') # open mfdataset but have fc_init_member as a dimension, i.e. number of forecast initialisations used.

    if "fc_init_member" not in all_fcs.dims:
        all_fcs = all_fcs.expand_dims("fc_init_member") # expand a fc_init_member if only one file is download. it will have a dimension of 1. 

    combined = all_fcs.stack(member=("fc_init_member", "number")).reset_index("member", drop=True)

    if leveltype == 'pressure':
        combined = combined.rename({'isobaricInhPa':'level'})
        combined = combined.transpose('time','member','level','latitude','longitude')
    else:
        print (combined)
        combined = combined.transpose('time','member','latitude','longitude')

    return combined

