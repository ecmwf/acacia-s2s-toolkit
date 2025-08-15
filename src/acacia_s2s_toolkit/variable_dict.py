# a dictionary with all the variable abbreviations in the appropriate categories for plev/sfc, six_hourly, 24 hour instanteous.

s2s_variables = {
        "pressure": {
            "instantaneous_parameters": ["gh","t","u","v","q","w"],
            "potential_temp_level": ["pv"]
            },
        "single_level": {
            "instantaneous_6hrly":["10u","10v","mx2t6","mn2t6",],
            "averaged_24hrs":["cape","skt","sd","rsn","asn","sm20","sm100","st20","st100","2t","2d","wtmp","ci","tcc","tcw",],
            "accumulated_24hrs":["sf","ttr","slhf","ssr","str","sshf","ssrd","strd","cp","nsss","ewss","ro","sro"],
            "instantaneous_24hrs":["sp","msl","lsm","orog","slt"],
            "accumulated_6hrly":["tp"]
            }
        }

webAPI_params={
        "gh":"156",
        "t":"130",
        "u":"131",
        "v":"132",
        "q":"133",
        "w":"135",
        "pv":"60",
        "10u":"165",
        "10v":"166",
        "mx2t6":"121",
        "mn2t6":"122",
        "cape":"59",
        "skt":"235",
        "sd":"228141",
        "rsn":"33",
        "asn":"228032",
        "sm20":"228086",
        "sm100":"228087",
        "st20":"228095",
        "st100":"228096",
        "2t":"167",
        "2d":"168",
        "wtmp":"34",
        "ci":"31",
        "tcc":"228164",
        "tcw":"136",
        "sf":"228144",
        "ttr":"179",
        "slhf":"147",
        "ssr":"176",
        "str":"177",
        "sshf":"146",
        "ssrd":"169",
        "strd":"175",
        "cp":"228143",
        "nsss":"181",
        "ewss":"180",
        "ro":"228205",
        "sro":"174008",
        "sp":"134",
        "msl":"151",
        "lsm":"172",
        "orog":"228002",
        "slt":"43",
        "tp":"228228"
        }

ECDS_varnames={}

model_origin={
        "ECMWF":"ecmf",
        "ECCC":"cwao",
        "HMCR":"rums",
        "JMA":"rjtd",
        "KMA":"rksl",
        "NCEP":"kwbc",
        "BOM":"ammc",
        "CMA":"babj",
        "CNR-ISAC":"isac",
        "CNRM":"lfpw", 
        "CPTEC":"sbsj",
        "IAP-CAS":"anso",
        "UKMO":"egrr"
        }

origin_latency_hours={
        "ammc":168,
        "babj":48,
        "isac":48,
        "lfpw":168,
        "sbsj":48,
        "cwao":48,
        "ecmf":48,
        "rums":48,
        "anso":48,
        "rjtd":48,
        "rksl":48,
        "kwbc":48,
        "egrr":504
        }

# which days of the week are forecasts initialised. 1 = Monday, 2 = Tuesday,..., Sunday = 7
fc_weekday_initials={
        "ammc":[4,7],
        "babj":[1,4],
        "isac":[4],
        "lfpw":[4],
        "sbsj":[3,4],
        "cwao":[1,4],
        "ecmf":[1,2,3,4,5,6,7],
        "rums":[4],
        "anso":[1,2,3,4,5,6,7],
        "rjtd":[1,2,3,4,5,6,7],
        "rksl":[1,2,3,4,5,6,7],
        "kwbc":[1,2,3,4,5,6,7],
        "egrr":[1,2,3,4,5,6,7]
        }

# forecast length
forecast_length_hours={
        "ammc":1488,
        "babj":1440,
        "isac":840,
        "lfpw":1128,
        "sbsj":840,
        "cwao":936,
        "ecmf":1104,
        "rums":1104,
        "anso":1560,
        "rjtd":816,
        "rksl":1440,
        "kwbc":1056,
        "egrr":1440
        }

# forecast members
forecast_pert_members={
        "ammc":32,
        "babj":3,
        "isac":40,
        "lfpw":24,
        "sbsj":10,
        "cwao":20,
        "ecmf":100,
        "rums":40,
        "anso":48,
        "rjtd":4,
        "rksl":7,
        "kwbc":15,
        "egrr":4
        }

# default_lag_ensemble
day_fclag_ensemble={
        "ammc":[0],
        "babj":[0],
        "isac":[0],
        "lfpw":[0],
        "sbsj":[0],
        "cwao":[0],
        "ecmf":[0],
        "rums":[0],
        "anso":[0],
        "rjtd":[0,-1,-2],
        "rksl":[0,-1,-2],
        "kwbc":[0,-1],
        "egrr":[0,-1,-2]
        }

# reforecast years. options include fixed (lower year, upper year) and dynamic (number of previous years)
reforecast_years={
        "ammc":{'fixed':(1981,2013)},
        "babj":{'dynamic':15},
        "isac":{'fixed':(2001,2020)},
        "lfpw":{'fixed':(1993,2017)},
        "sbsj":{'fixed':(1999,2018)},
        "cwao":{'fixed':(2001,2020)},
        "ecmf":{'dynamic':20},
        "rums":{'fixed':(1991,2020)},
        "anso":{'fixed':(1999,2018)},
        "rjtd":{'fixed':(1991,2020)},
        "rksl":{'fixed':(1993,2016)},
        "kwbc":{'fixed':(1999,2010)},
        "egrr":{'fixed':(1993,2016)}
        }

# describes whether there is a single model version or whether on the fly versions are used and how to describe them. 
reforecast_model_freq={
        "ammc":{'fixed':'20140101'},
        "babj":'otf', # on the fly
        "isac":{'fixed':'20231016'},
        "lfpw":{'fixed':'20190701'},
        "sbsj":{'fixed':'20230104'},
        "cwao":'otf',
        "ecmf":'otf',
        "rums":'otf',
        "anso":{'fixed':'20190101'},
        "rjtd":{'fixed':'20220930'},
        "rksl":'otf',
        "kwbc":{'fixed':'20110301'},
        "egrr":'otf'
        }


# describes reforecast freq, different to model frequency as some models remain constant, i.e. ammc, same model version [20140101] but reforecast frequency is six per month
reforecast_freq={
        "ammc":[1,6,11,16,21,26], # DOMs for reforecasts
        "babj":'rf_model_date', # the reforecast model date will be the same as the reforecast frequency
        "isac":'CNRevery5days',
        "lfpw":'CNRMevery7days',
        "sbsj":'CPTECevery7days',
        "cwao":'rf_model_date',
        "ecmf":'rf_model_date',
        "rums":'rf_model_date',
        "anso":'fcdate', # when rf model version is fixed but reforecast freq is same as forecast freq.
        "rjtd":'JMA2permonth',
        "rksl":'rf_model_date', # DOMs for reforecasts
        "kwbc":'fcdate',
        "egrr":'rf_model_date'
        }

reforecast_pert_members={
        "ammc":32,
        "babj":3,
        "isac":7,
        "lfpw":9,
        "sbsj":10,
        "cwao":3,
        "ecmf":10,
        "rums":10,
        "anso":3,
        "rjtd":4,
        "rksl":6,
        "kwbc":3,
        "egrr":6        
        }

rf_lag_info={
        "ammc":{'nearestDOM': [1,6,11,16,21,26]}, # DOMs, just choose closest day.
        "babj":{'weekday_based':'ThMoTh'}, # Thursday, Monday, Thursday, lag depends on chosen fcdate
        "isac":{'unique':'CNRevery5days'},
        #"lfpw":[0],
        #"sbsj":[0],
        "cwao":{'weekday_based':'ThMoTh'},
        "ecmf":{'unique':'odddates'}, # ecmwf has reforecasts every odd day (expect feb 29th). for odd day: -2 and 0, even day: -1 and 1
        "rums":{'daily_lagged':[0]},
        "anso":{'daily_lagged':[-4,-2,0,2,4]},
        "rjtd":{'unique':'JMAtwicepermonth'}, # chosen two lags where reforecast is before and after forecast date
        "rksl":{'before_after_DOM':[1,9,17,25]}, # DOMs. will choose before and after day
        "kwbc":{'daily_lagged':[-4,-2,0,2,4]},
        "egrr":{'before_after_DOM':[1,9,17,25]}
        }

