# output suitable ECDS variables in light of requested forecasts.
from acacia_s2s_toolkit import variable_dict, argument_check
from datetime import datetime, timedelta
from importlib import resources
import numpy as np
import pandas as pd
import ast

def read_lookup_table(fcdate='20250828'):
    # convert fcdate to a time field. 
    fc_dt = datetime.strptime(fcdate,'%Y%m%d')
    csv_dir = "acacia_s2s_toolkit.lookup_tables"
   
    first_lookup_table_date = '20240514'
    first_lookup_table_time = datetime.strptime(first_lookup_table_date,'%Y%m%d')

    ############ new lookup table directory ##### Select the most recent lookup table compared to the requested forecast date #####
    if fc_dt < first_lookup_table_time:
        csv_file = f'lookup_table_{first_lookup_table_date}.csv'
    else:
        # list all files in directory
        files = [f.name for f in resources.files(csv_dir).iterdir() if f.name.startswith("lookup_table_") and f.name.endswith(".csv")]

        file_dates = [(datetime.strptime(f.split("_")[-1].replace(".csv",""),"%Y%m%d"),f) for f in files] # outputs dates + name of files.

        # select valid dates (all less than fcdate)
        valid_dates = [(date,file) for date, file in file_dates if date <= fc_dt]
        if not valid_dates:
            raise FileNotFoundError(f"No lookup table found before {fcdate}")

        # pick the most recent one, then read that lookup table
        chosen_date, csv_file = max(valid_dates, key=lambda x:x[0])

    with resources.open_text(csv_dir,csv_file) as fc_info:
        df = pd.read_csv(fc_info)

    columns_to_eval = ["fcFreq", "dayfcLags", "rfRange", "rfLagDetail"]

    for col in columns_to_eval:
        # if the option is a list of numbers or zero.
        df[col] = df[col].apply(lambda x: int(x) if x == "0" else (ast.literal_eval(x) if isinstance(x, str) and (x.startswith("[") or x.startswith("(")) else x)) 
    return df

def get_single_parameter(origin_id,fcdate,parameter):
    # first read lookup table
    df = read_lookup_table(fcdate)
    # find forecast length for originID
    match = df.loc[df["Origin"] == origin_id, parameter]

    if match.empty:
        print (f"[ERROR] could not find {parameter} for originID '{origin_id}'.")
        return None

    return match.iloc[0]

def get_timeresolution(variable):
    # first find which sub-category the variable sits in
    time_resolution=None
    for category_name, category_dict in variable_dict.s2s_variables.items():
        for subcategory_name, subcategory_vars in category_dict.items():
            if variable in subcategory_vars:
                time_resolution = subcategory_name
                break # found correct time resolution
        if time_resolution:
            break # break outer loop

    if time_resolution is None:
        print (f"[ERROR] could not find variable '{variable}'.")
        return None
    return time_resolution

def output_leadtime_hour(variable,origin_id,fcdate,fc_enslags,start_time=0):
    '''
    Given variable (variable abbreivation), output suitable leadtime_hour. The leadtime_hour will request all avaliable steps. Users should be able to pre-define leadtime_hour if they do not want all output.
    return: leadtime_hour
    '''
    time_resolution = get_timeresolution(variable)

    # next find maximum end time
    end_time = get_single_parameter(origin_id,fcdate,'fcLength')

    # given time resolution, work out array of appropriate time values
    if time_resolution.endswith('6hrly'):
        leadtime_hour = np.arange(start_time,end_time+1,6)
    else:
        leadtime_hour = np.arange(start_time,end_time+1,24) # will output 0 to 1104 in steps of 24 (ECMWF example). 
 
    # take the minimum value in fc_enslags and multiply by 24
    #max_endtime = end_time+(24*np.min(fc_enslags)) # so 1104 + (24*-2) = 1056
    #leadtime_hour = leadtime_hour[leadtime_hour <= max_endtime]

    return leadtime_hour

def output_sfc_or_plev(variable):
    '''
    Given variable (variable abbreivation), output whether variable is sfc level or on pressure levels?
    return: level_type
    '''
    # Flatten all variables from nested dictionary
    level_type=None
    for category_name, category_dict in variable_dict.s2s_variables.items():
        for subcategory_vars in category_dict.values():
            if variable in subcategory_vars:
                level_type = category_name
                return level_type
    if level_type == None:
        print (f"[ERROR] No leveltype found for '{variable}'.")
        return level_type

def output_webapi_variable_name(variable):
    ''' 
    Given variable abbreviation, output webAPI paramID.
    return webAPI paramID.

    '''
    for variable_abb, webapi_code in variable_dict.webAPI_params.items():
        if variable == variable_abb:
            return webapi_code
    print (f"[ERROR] No webAPI paramID found for '{variable}'.")
    return None

def output_originID(model,fcdate):
    '''
    Given model name, output originID.
    return originID.

    '''
    # first read lookup table
    df = read_lookup_table(fcdate)
    # find forecast length for originID
    match = df.loc[df["Model"] == model, "Origin"]

    if match.empty:
        print (f"[ERROR] could not find for originID for model '{model}'.")
        return None

    return match.iloc[0]

def output_ECDS_variable_name(variable):
    '''
    Given variable name, output the matching ECDS variable name
    
    return ECDS_varname (ECMWF Data Store)
    '''
    ECDS_varname='10m_uwind'
    return ECDS_varname

def output_plevs(variable):
    '''
    Output suitable plevs, if q, (1000, 925, 850, 700, 500, 300, 200) else add 100, 50 and 10 hPa. 
    '''
    all_plevs=[1000,925,850,700,500,300,200,100,50,10]
    if variable == 'q':
        plevs=all_plevs[:-3] # if q is chosen, don't download stratosphere
    else:
        plevs=all_plevs
    print (f"Selected the following pressure levels: {plevs}")
    
    return plevs

def output_fc_lags(origin_id,fcdate):
    '''
    Given origin_id, output lagged ensemble forecasts.
    return array with day lag positions, i.e. [0,-1,-2].
    '''
    fclags = get_single_parameter(origin_id,fcdate,'dayfcLags')

    # Special handling for CPTEC (sbsj). Initialisation only given for Wednesday and Thursday.
    if origin_id == 'sbsj':
        date_obj = datetime.strptime(fcdate, '%Y%m%d')
        weekday = date_obj.weekday()+1  # Monday = 1, ..., Sunday = 7
        if weekday == 4:  # Thursday
            return [0, -1]
        else:
            return [0]
    # Return the list from the dictionary
    return fclags

def output_hc_lags(origin_id,fcdate):
    '''
    Given origin_id, outputted the best lags for downloading reforecasts
    '''
    lag_type = get_single_parameter(origin_id,fcdate,'rfLagType')
    rf_freq_info = get_single_parameter(origin_id,fcdate,'rfLagDetail')

    fcdate_obj = datetime.strptime(fcdate, '%Y%m%d')
    weekday = fcdate_obj.weekday()+1  # Monday = 1, ..., Sunday = 7
    dayofmonth = fcdate_obj.day

    # ---- Nearest DOM (single closest) -------
    if "nearestDOM" == lag_type: # DOMs. get closest lags
        # Build candidate reforecast dates in prev/current/next month
        candidates = []
        for offset_month in [-1, 0, 1]:
            # Month/year shift
            month = (fcdate_obj.month - 1 + offset_month) % 12 + 1
            year = fcdate_obj.year + ((fcdate_obj.month - 1 + offset_month) // 12)
            for dom in rf_freq_info:
                try:
                    candidates.append(datetime(year, month, dom))
                except ValueError:
                    continue  # skip invalid dates (e.g., Feb 30)

        # Find the one with smallest abs(lag)
        closest_rf = min(candidates, key=lambda d: abs((d - fcdate_obj).days))
        lag = (closest_rf - fcdate_obj).days
        return lag
    # ------ Before/after DOM -----------------
    if "before_after_DOM" == lag_type:
        # Build candidate reforecast dates in prev/current/next month
        candidates = []
        for offset_month in [-1, 0, 1]:
            # Month/year shift
            month = (fcdate_obj.month - 1 + offset_month) % 12 + 1
            year = fcdate_obj.year + ((fcdate_obj.month - 1 + offset_month) // 12)
            for dom in rf_freq_info:
                try:
                    candidates.append(datetime(year, month, dom))
                except ValueError:
                    continue  # skip invalid dates (e.g., Feb 30)

        lags = [(c-fcdate_obj).days for c in candidates]

        neg_lags = [l for l in lags if l < 0]
        pos_lags = [l for l in lags if l >= 0]

        largest_neg = max(neg_lags) if neg_lags else None
        smallest_pos = min(pos_lags) if pos_lags else None

        return [largest_neg,smallest_pos] # before and after lags
    # ------ daily reforecast initialisations ------
    if "daily_lagged" == lag_type:
        return rf_freq_info

    # ------ Weekday based (i.e. only Monday and Thursday reforecasts)-----
    if "weekday_based" == lag_type:
        # two options depending on whether fcdate is a Monday or Thursday. 
        if fcdate_obj >= datetime(2023,6,27) and origin_id == 'ecmf': # for ecmwf between 20230627 and 20241112, ECMWF ran daily forecasts but MoThMo reforecasts. 
            return two_Monday_Thursday_rfdates(fcdate_obj)
        else:
            if weekday == 4: # Thursday
                return [-3,0]
            elif weekday == 1: # Monday
                return [0,3]
            else:
                raise ValueError(f"[ERROR] For origin_id '{origin_id}' forecasts are only every Monday and Thursday, therefore a Monday or Thursday forecast date must be selected.")

    # ---- Unique modes  ------
    if "unique" == lag_type:
        # ECMWF ---- odd day reforecasts.
        if rf_freq_info == 'odddates':
            if (dayofmonth % 2 == 0) or (dayofmonth == 29 and fcdate_obj.month() == 2):
                return [-1,1] # for even fcdates (or 29th Feb) chosen rfdate before and after forecast date.
            else:
                return [-2,0] # for odd dates, choosen current day, minus 2. 
        if rf_freq_info == 'CNRevery5days': # roughly five days
            # make an array of dates from 2020-01-01 to 2020-12-27
            DOM = {1:[1,6,11,16,21,26,31],2:[5,10,15,20,25],3:[2,7,12,17,22,27],4:[1,6,11,16,21,26],5:[1,6,11,16,21,26,31],6:[5,10,15,20,25,30],7:[5,10,15,20,25,30],8:[4,9,14,19,24,29],9:[3,8,13,18,23,28],10:[3,8,13,18,23,28],11:[2,7,12,17,22,27],12:[2,7,12,17,22,27]}
            CNR_rf_dates = []
            for year in (2020,2021):
                for month, days in DOM.items():
                    for day in days:
                        CNR_rf_dates.append(datetime(year,month,day))
            # change year of fcdate to 2020-fcdate(MM)-fcdate(DD)
            fc_date_2020 = datetime.strptime(f"2020{fcdate[4:]}",'%Y%m%d')
            # nearest date to altered fcdate is rf_date
            closest_day=min(CNR_rf_dates,key=lambda x:abs(fc_date_2020-x))
            lag = (closest_day - fc_date_2020).days
            return lag
        if rf_freq_info == 'JMAtwicepermonth': # twice per month
            # make an array of dates from 2020-01-01 to 2020-12-27
            DOM = {1:[16,31],2:[10,25],3:[12,27],4:[11,26],5:[16,31],6:[15,30],7:[15,30],8:[14,29],9:[13,28],10:[13,28],11:[12,27],12:[12,27]}
            JMA_rf_dates = []
            for year in (2019,2020,2021):
                for month, days in DOM.items():
                    for day in days:
                        JMA_rf_dates.append(datetime(year,month,day))
            # change year of fcdate to 2020-fcdate(MM)-fcdate(DD)
            fc_date_2020 = datetime.strptime(f"2020{fcdate[4:]}",'%Y%m%d')

            lags = [(c-fc_date_2020).days for c in JMA_rf_dates]
            neg_lags = [l for l in lags if l < 0]
            pos_lags = [l for l in lags if l >= 0]

            largest_neg = max(neg_lags) if neg_lags else None
            smallest_pos = min(pos_lags) if pos_lags else None

            return [largest_neg,smallest_pos] 

def two_Monday_Thursday_rfdates(fcdate):
    '''
    Given a fcdate, output the appropriate three reforecast start dates. Relevant for ECMWF operations between 27th June 2023 and 12th November 2024
    '''
    # create a list of dates +- 14 days around fcdate
    pos_dates = [fcdate + timedelta(days=delta) for delta in range(-14,15)]
    # keep only Mondays and Thursdays
    mon_thurs = [date for date in pos_dates if date.weekday() in (0,3)]
    days_delta = [(md-fcdate).days for md in mon_thurs]
    # then sort by abs value
    days_delta.sort(key=lambda x: (abs(x)))

    return days_delta[:2]


def get_hindcast_model_date(origin_id,fcdate):
    ''' Given origin_id, output appropriate date for reforecast dataset. This is the hindcast model version, not the set of reforecast dates.
    '''
    rf_model_freq = get_single_parameter(origin_id,fcdate,'rfModelFreq')
    rf_model_date = get_single_parameter(origin_id,fcdate,'rfModelDate')
    
    if rf_model_freq == "fixed":
        mrf_date = str(rf_model_date)
    else:
        mrf_date = fcdate

    return mrf_date
        
def get_hindcast_year_span(origin_id,fcdate):
    ''' Given origin_id, output appropriate set of years for reforecasts.
    '''
    rfType = get_single_parameter(origin_id,fcdate,'rfType')
    rf_yrs = get_single_parameter(origin_id,fcdate,'rfRange')

    if rfType == "fixed":
        start, end = rf_yrs
        rf_years = np.arange(start,end+1) # give full set of years, i.e. 1981, 1982, ..., 2013.
    elif rfType == "dynamic":
        fc_year = int(fcdate[:4]) # get year component of date.
        rf_years = np.arange(fc_year - int(rf_yrs),fc_year)
    else:
        raise ValueError(f"[ERROR] Couldn't compute appropriate reforecast years for origin_id '{origin_id}'.")

    return rf_years

def output_formatted_leadtimes(leadtime_hour,fcdate,variable,origin_id,lag=0,fc_enslags=0):
    ''' lag is always negative for forecast. Function always uses lag=0 for reforecast download'''

    print (fc_enslags)

    # create new fcdate based on lag
    new_fcdate = datetime.strptime(fcdate, '%Y%m%d')+timedelta(days=float(lag))
    convert_fcdate = new_fcdate.strftime('%Y-%m-%d')

    # check last leadtime is small enough to handle
    # first get fcLength
    fc_length = get_single_parameter(origin_id,fcdate,'fcLength')
    if np.max(leadtime_hour) > fc_length-(24.0*np.min(fc_enslags)):
        raise ValueError(f"[ERROR] The maximum requested leadtime hour is greater than the forecast length - the largest change in lagged ensemble (hours).")

    # convert leadtimes
    # is it an average field?
    time_resolution = get_timeresolution(variable)

    # get standard, all leadtime hours avaliable
    leadtime_hour_ALL = output_leadtime_hour(variable,origin_id,fcdate,fc_enslags)

    # find the indexes of the requested leadtimes (leadtime_hour)
    idx = np.asarray([np.where(leadtime_hour_ALL == lt)[0][0] for lt in leadtime_hour]) # get the indexes of where the requested leadtime hours are

    # if an average field, use '0-24/24-48/48-72...'
    leadtime_hour_copy = leadtime_hour[:]

    if time_resolution.endswith('6hrly'):
        nsteps_per_day = 4
        new_idx = idx-lag*nsteps_per_day
    else: # instantaneous field
        new_idx = idx-lag

    # check index is no larger than forecast length
    if np.max(new_idx) > len(leadtime_hour_ALL):
        raise ValueError(f"[ERROR] The maximum requested leadtime hour is greater than the forecast length, i.e. when performing lagged forecast ensemble, it can reach the last few timesteps.")

    leadtime_hour_copy=leadtime_hour_ALL[new_idx]

    if time_resolution.startswith('aver'):
        leadtimes='/'.join(f"{leadtime_hour_copy[i]}-{leadtime_hour_copy[i]+24}" for i in range(len(leadtime_hour_copy)-1))
    else: # instantaneous field
        leadtimes = '/'.join(str(x) for x in leadtime_hour_copy)
    
    print (leadtimes)
    
    return leadtimes, convert_fcdate

def create_reforecast_dates(rfyears,rfdate):
    ''' function that produces a list of reforecast dates given set of years and chosen reforecast date
    '''
    if np.size(rfdate) == 1: # for a single reforecast date that is then repeated for all reforecast years
        DOY = rfdate[4:]
        rf_dates = '/'.join(f"{int(year)}{DOY}" for year in rfyears)
    else:
        rf_dates = '/'.join(f"{date}" for date in rfdate) 
    return rf_dates
 

def check_and_output_all_fc_arguments(variable,model,fcdate,area,data_format,grid,plevs,leadtime_hour,fc_enslags):
    # check variable name. Is the variable name one of the abbreviations?
    argument_check.check_requested_variable(variable)
    # is it a sfc or pressure level field. # output sfc or level type
    level_type = output_sfc_or_plev(variable)

    # if level_type == plevs and plevs=None, output_plevs. Will only give troposphere for q. 
    # work out appropriate pressure levels
    if level_type == 'pressure':
        if plevs is None:
            plevs = output_plevs(variable)
        else:
            print (f"Downloading the requested pressure levels: {plevs}") # if not, use request plevs.
        # check plevs
        argument_check.check_plevs(plevs,variable)
    else:
        print (f"Downloading the following level type: {level_type}")
        plevs=None

    # get ECDS version of variable name. - WILL WRITE UP IN OCTOBER 2025!
    #ecds_varname = variable_output.output_ECDS_variable_name(variable)
    ecds_varname=None

    # get webapi param
    webapi_param = output_webapi_variable_name(variable) # temporary until move to ECDS (Aug - Oct).

    # check model is in acceptance list and get origin code!
    argument_check.check_model_name(model,fcdate)
    # get origin id
    origin_id = output_originID(model,fcdate)

    # get fc_enslags
    # get lagged ensemble details
    if fc_enslags is None:
        fc_enslags = output_fc_lags(origin_id,fcdate)
    # after gathering fc_enslags, check all ensemble lags are negative or zero and whole numbers as they can be user-inputted.
    argument_check.check_fc_enslags(fc_enslags)

    # if leadtime_hour = None, get leadtime_hour (output all hours).
    if leadtime_hour is None:
        leadtime_hour = output_leadtime_hour(variable,origin_id,fcdate,fc_enslags) # the function outputs an array of hours. This is the leadtime used during download.
    else:
        leadtime_hour = np.array(leadtime_hour) # make leadtime hour an array
    print (f"For the following variable '{variable}' using the following leadtimes '{leadtime_hour}'.")

    # check leadtime_hours (as individuals can choose own leadtime_hours).
    argument_check.check_leadtime_hours(leadtime_hour,variable,origin_id,fcdate)

    # check fcdate.
    argument_check.check_fcdate(fcdate,origin_id)

    # check dataformat
    argument_check.check_dataformat(data_format)

    # check area selection
    argument_check.check_area_selection(area)

    return level_type, plevs, webapi_param, ecds_varname, origin_id, leadtime_hour, fc_enslags

def check_and_output_all_hc_arguments(variable,origin_id,fcdate,rfyears=None):
    ''' Function that will output all the necessary arguments to download reforecast data
    '''
    # get the date of the reforecast model
    rf_model_date = get_hindcast_model_date(origin_id,fcdate)

    # get the reforecast years
    if rfyears is None:
        rfyears = get_hindcast_year_span(origin_id,fcdate)
    # after computing reforecast years, check the chosen set
    argument_check.check_requested_reforecast_years(rfyears,origin_id,fcdate)

    return rf_model_date, rfyears


