# scripts relevant for merging multiple forecast
import xarray as xr
import numpy as np
import pandas as pd
import glob as glob
import os

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
        os.system(f'rm {filename}*.idx') # annoying index files. these appear when reading the file in 'cfgrib'
        all_data = []
        # reopen files individually
        files = glob.glob(f'{filename}_allens_*')
        for file in files:
            single_fc = xr.load_dataset(file,engine='cfgrib')
            single_fc = single_fc.swap_dims({"step":"valid_time"})
            single_fc = single_fc.drop_vars(['step','time'])

            all_data.append(single_fc)
        all_fcs = xr.concat(all_data,dim='fc_init_member')

# OLD - ALL FCS! 
        #    # check for duplicate time points (common for accumulations)
        #    # SORT FOR LAGGED ENSEMBLE (NCEP for instance)
        #    if len(single_mem_sel['valid_time'].values) != len(pd.unique(single_mem_sel['valid_time'].values)):
        #        # There are duplicates → merge them along 'number'
        #        print ('Please note. There are still multiple values of the same time after merging valid_time (most likely due to an accumulation field that takes into consideration forecast step). To manually fix, we put all forecasts with the same timestamp in the same ensemble set. Further investigation needed to understand effect but for accumulation, you will most likely subtract from another time stamp')
        #        unique_times = pd.unique(single_mem_sel['valid_time'].values)

        #        slices = [single_mem_sel.sel(valid_time=t).stack(member=("number","valid_time")).reset_index("member", drop=True).assign_coords(valid_time=t) for t in unique_times]
        #        single_mem_sel = xr.concat(slices, dim='valid_time')
        #        single_mem_sel = single_mem_sel.rename({'member':'number'})

         #   all_data.append(single_mem_sel)
        #all_fcs = xr.concat(all_data,dim='fc_init_member')

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
        if 'isobaricInhPa' in combined.dims:
            combined = combined.rename({'isobaricInhPa':'level'})
        # Only transpose dims that actually exist
        combined = combined.transpose(
            *[d for d in ['time','member','level','latitude','longitude'] if d in combined.dims]
        )
    else:
        combined = combined.transpose(
            *[d for d in ['time','member','latitude','longitude'] if d in combined.dims]
        )

    return combined

def merge_all_ens_hindcasts(filename,leveltype):
    all_fcs = xr.open_mfdataset(f'{filename}_allens_*',combine='nested',concat_dim='fc_init_member') # open mfdataset but have fc_init_member as a dimension, i.e. number of forecast initialisations used.

    if "fc_init_member" not in all_fcs.dims:
        all_fcs = all_fcs.expand_dims("fc_init_member") # expand a fc_init_member if only one file is download. it will have a dimension of 1. 

    combined = all_fcs.stack(member=("fc_init_member", "number")).reset_index("member", drop=True)

    if leveltype == 'pressure':
        if 'isobaricInhPa' in combined.dims:
            combined = combined.rename({'isobaricInhPa':'level'})
        # Only transpose dims that actually exist
        combined = combined.transpose(
            *[d for d in ['time','member','level','latitude','longitude'] if d in combined.dims]
        )
    else:
        print (combined)
        combined = combined.transpose(
            *[d for d in ['time','member','latitude','longitude'] if d in combined.dims]
        )

    return combined

