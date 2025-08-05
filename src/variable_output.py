# output suitable ECDS variables in light of requested forecasts.

def output_leadtime_hour(variable):
    '''
    Given variable (variable abbreivation), output suitable leadtime_hour. The leadtime_hour will request all avaliable steps. Users should be able to pre-define leadtime_hour if they do not want all output.
    return: leadtime_hour
    '''
    leadtime_hour=6
    return leadtime_hour

def output_sfc_or_plev(variable):
    '''
    Given variable (variable abbreivation), output whether variable is sfc level or on pressure levels?
    return: level_type
    '''
    
    level_type='pl'
    
    return level_type

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
    plevs=[1000,925]
    return plevs
