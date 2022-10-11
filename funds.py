from hyper.contrib import HTTP20Adapter
from ks_api_client import ks_api
import pandas as pd
from authorize_arjun import login
from tvDatafeed import TvDatafeed, Interval
import sys
import datetime as dt
from arjun_api import cred as arjun_cred
import requests

# temp = client.margin()

def get_funds(client):
    cred = arjun_cred()
   
    header_params = {}
    header_params['consumerKey'] = cred.consumer_key
    header_params['sessionToken'] = client.session_token
    body_params = None
    header_params['Authorization'] = "Bearer "+ cred.access_token
    
    s = requests.session()
    s.mount('https://', HTTP20Adapter())
    res = s.get("https://tradeapi.kotaksecurities.com/apim/margin/1.0/margin",data=body_params, headers=header_params)    
    res = res.json()
    
    if "Success" in res:
        if "equity" in res["Success"]:
            eq = res["Success"]["equity"]
            if (len(eq) >0):
                if 'cash' in eq[0]:
                    if "marginAvailable" in eq[0]['cash']:
                        return round(float(res["Success"]["equity"][0]["cash"]["marginAvailable"]),2)
                
