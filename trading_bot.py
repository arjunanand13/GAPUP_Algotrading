from ks_api_client import ks_api
import numpy as np
import pandas as pd
from tvDatafeed import TvDatafeed, Interval
import time as t
from datetime import *
import copy
import datetime as dt
from authorize_arjun import login
import sys
import math
from funds_kotak import get_funds
# import telegram_send


tv = TvDatafeed(auto_login=(True))
print('Arjun')

today = str(dt.datetime.today().date())

"""Login to Kotak Trading api"""
try:
    client = login.author()
except Exception as e:
    temp = today + " Couldn't Login due to error : %s\n" % e
    print(temp)
    # telegram_send.send(messages=[temp])

a = client.margin()
funds = float(a['Success']['equity'][0]['cash']['availableCashBalance'])

temp2 = today + '     Balance = '+str(funds)
print(temp2)
# telegram_send.send(messages=[temp2])

"""Getting the required stocks/tickers"""
cur_time_init = dt.datetime.now()
pm_init=datetime.timestamp(dt.datetime(cur_time_init.year, cur_time_init.month, cur_time_init.day, 9, 9, 30))
if t.time() < pm_init:
    sleep_init = pm_init - t.time()
    t.sleep(sleep_init)

scripdf = pd.read_excel('Kotak_intraday.xlsx')
scrip=pd.DataFrame()
scrip = scripdf.iloc[:,[0,1,4]]
scrip.dropna(inplace=True)

stocks = scrip['Instrument_name'].tolist()

scrip.set_index('Instrument_name', inplace=True)

    

"""Getting Data from Trading View"""
req_list=[]
st=t.time()
ohlc = {}

for ticker in stocks:
    print(ticker)
    ohlc[ticker] = tv.get_hist(ticker, 'NSE', Interval.in_5_minute, 10)
en = t.time()
print(en-st)
"""Function to round off to left integer"""
def round_down(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n * multiplier) / multiplier

"""Defining Functions that process data and return trade signal"""
def data(ohlc_dict, stocks):        #returns ohlv_data
    ohlv_df = copy.deepcopy(ohlc_dict)
    for ticker in stocks:
        ohlv_df[ticker].drop(['symbol'], axis=1, inplace=True)
        ohlv_df[ticker].columns = ['Open','High','Low','Close','Volume']
    return ohlv_df

def trade_signal(ohlv_df, stocks, scrip, total):   #Gives the trade signal=1 for defined gap up condition
    signal_scrip = scrip.copy()
    signal_scrip['Signal'] = 0
    signal_scrip['Quantity'] = 0
    signal_scrip['Current_price'] = float(0)
    for ticker in stocks:
        for i in range(len(ohlv_df[ticker])):
            if ohlv_df[ticker].index[i].time() == dt.time(9, 5) and \
                ohlv_df[ticker]['Open'][i] >= 1.0225*(ohlv_df[ticker]['Close'][i-1]) and \
                    ohlv_df[ticker]['Open'][i] < 1.05*(ohlv_df[ticker]['Close'][i-1]) and \
                        ohlv_df[ticker]['Open'][i]>=1.02*(ohlv_df[ticker]['Open'][i-1]):
                            signal_scrip['Signal'][ticker] = 1
                            signal_scrip['Current_price'][ticker] = round(float(ohlv_df[ticker]['Open'][i]),1)

                            print('Short signal recieved for',ticker)
                            # if ohlv_df[ticker]['Open'][i] > 1000:
                            #     position = False
                            #     print('No position sizing')
    trades = len(signal_scrip[signal_scrip['Signal']!=0].index.tolist())
    if trades != 0:
        position = (0.9*total)/trades
    else:
        position=0
    if trades > 15:
        pos = False
        print('No position sizing')
    else:
        pos = True
    print('Number of trades : ',trades)
    print('Amount for each stock :',position)
    for ticker in stocks:
        if signal_scrip['Signal'][ticker] == 1 and position != 0:
            price = float(signal_scrip['Current_price'][ticker])
            margin = float(signal_scrip['Margin'][ticker])
            if pos == True:
                qty = int(round_down((position/(price/margin)), 0))
            else:
                qty = 1
            signal_scrip['Quantity'][ticker] = qty
            
    return signal_scrip, position, pos

def signals():      #Function to initialize ohlv_data and return trade signal
    ohlc_df = data(ohlc, stocks)
    signal_df, position, pos = trade_signal(ohlc_df, stocks, scrip, funds)
    return ohlc_df, signal_df, position, pos

def short(client, stocks, signal, position, pos):
    """Entry/shorting of stocks is done by this function"""
    for ticker in stocks:
        if signal['Signal'][ticker] == 1 and dt.datetime.now().time()<dt.time(9,20):
            print(ticker,signal['Ticker'][ticker])
            tick = int(signal['Ticker'][ticker])
            # margin = float(signal['Margin'][ticker])
            # price = round(float(client.quote(instrument_token = tick, quote_type='LTP')['success'][0]['lastPrice']),2)
            qty = int(signal['Quantity'][ticker])
            # signal['Quantity'][ticker] = qty
            
            try:
                client.place_order(order_type = "MIS", instrument_token = tick, transaction_type = "SELL",\
                   quantity = qty, price = 0, disclosed_quantity = 0, trigger_price = 0,\
                        validity = "GFD", variety = "REGULAR", tag = "string")
                # stoploss = round((1.02*float(client.quote(instrument_token = tick)['success'][0]['open_price'])),1)
                print('Shorted ',ticker, 'Quantity :',qty)
            except Exception as e:
                print("Exception when calling OrderApi->place_order: %s\n" % e)
                continue

def target_order(client, stocks, signal, pos, sl_positions):
    """Function to place target at 9.15"""
    signal_scrip = signal.copy()
    signal_scrip['exit_price'] = float(0)
    for ticker in stocks:
        if signal['Signal'][ticker] == 1 and ticker in pos:
            for i in range(len(sl_positions['Success'])):
                if sl_positions['Success'][i]['symbol'] == ticker:
                    targ_price = round(0.994*(float(sl_positions['Success'][i]['averageStockPrice'])), 1)
            
            # signal_scrip['exit_price'][ticker] = targ_930
            tick = int(signal['Ticker'][ticker])
            qty = int(signal['Quantity'][ticker])
            
            try:
                client.place_order(order_type = "MIS", instrument_token = tick, transaction_type = "BUY",\
                   quantity = qty, price = targ_price, disclosed_quantity = 0, trigger_price = targ_price,\
                        validity = "GFD", variety = "REGULAR", tag = "string")
                print('Placed target order for',ticker,'price =',targ_price)
            except Exception as e:
                print("Exception when calling OrderApi->place_order: %s\n" % e)
                continue
            
    for ticker in stocks:
        if signal['Signal'][ticker] == 1 and ticker in pos:
            targ_930 = round(0.994*(float(sl_positions['Success'][i]['averageStockPrice'])), 1)
            signal_scrip['exit_price'][ticker] = targ_930
    
    return signal_scrip
    
    
def sl_order(client, stocks, signal, pos, sl_positions):
    """Function places stop loss order at 9:20 am"""
    for ticker in stocks:
        if signal['Signal'][ticker] == 1 and ticker in pos and dt.datetime.now().time()>dt.time(9,20):
            for i in range(len(sl_positions['Success'])):
                if sl_positions['Success'][i]['symbol'] == ticker:
                    sl_price = round_down(1.01*(float(sl_positions['Success'][i]['averageStockPrice'])), 1)                
            tick = int(signal['Ticker'][ticker])
            qty = int(signal['Quantity'][ticker])
            print(sl_price)
            try:
                client.place_order(order_type = "MIS", instrument_token = tick, transaction_type = "BUY",\
                   quantity = qty, price = sl_price, disclosed_quantity = 0, trigger_price = sl_price,\
                        validity = "GFD", variety = "REGULAR", tag = "string")
                print('Placed stoploss order for',ticker,'price =',sl_price)
            except Exception as e:
                print("Exception when calling OrderApi->place_order: %s\n" % e)
                continue
            
def internal_target(client, stocks, signal, pos):
    """Function to exit on target internally"""
    for ticker in stocks:
        if signal['Signal'][ticker] == 1 and ticker in pos:
            tick = int(signal['Ticker'][ticker])
            cur_price = float(client.quote(instrument_token = tick, quote_type='LTP')['success'][0]['lastPrice'])
            if cur_price <= float(signal['exit_price'][ticker]):
                qty = int(signal['Quantity'][ticker])
                cancel_stoploss(client, ticker)
                try:
                    client.place_order(order_type = "MIS", instrument_token = tick, transaction_type = "BUY",\
                       quantity = qty, price = 0, disclosed_quantity = 0, trigger_price = 0,\
                            validity = "GFD", variety = "REGULAR", tag = "string")
                    # stoploss = round((1.02*float(client.quote(instrument_token = tick)['success'][0]['open_price'])),1)
                    print('Exited ',ticker, 'Quantity :',qty)
                except Exception as e:
                    print("Exception when calling OrderApi->place_order: %s\n" % e)
                    continue

def square_off(client, stocks, signal, positions):
    """Exit/square off at 10:55 am done by this function"""
    for ticker in stocks:
        if signal['Signal'][ticker]==1 and ticker in positions:
            tick = int(signal['Ticker'][ticker])
            qty = int(signal['Quantity'][ticker])
            try: 
                client.place_order(order_type = "MIS", instrument_token = tick, transaction_type = "BUY",\
                   quantity = qty, price = 0, disclosed_quantity = 0, trigger_price = 0,\
                        validity = "GFD", variety = "SQUAREOFF", tag = "string")
                print('Exited position for ',ticker)
            except Exception as e:
                print("Exception when calling OrderApi->place_order: %s\n" % e)
                continue
    
   # b=client.quote(instrument_token = 8658) 

def pos(client):
    """Returns the list of Open positions"""
    openpos = client.positions(position_type='OPEN')
    pos_list = []
    for i in range(len(openpos['Success'])):
        # if openpos['Success'][i]['buyOpenQtyLot'] != 0:
        pos_list.append(openpos['Success'][i]['symbol'])
    return pos_list

def open_pos(client):
    """Returns the list of Open positions"""
    openpos = client.positions(position_type='OPEN')
    pos_list = []
    for i in range(len(openpos['Success'])):
        if openpos['Success'][i]['netTrdQtyLot'] != 0:
            pos_list.append(openpos['Success'][i]['symbol'])
    return pos_list

def order_cancel(client):
    """Cancelling all the Open Stop Loss orders"""
    orders_sl = client.order_report()
    ord_id=[]
    
    for i in range(len(orders_sl['success'])):
        if orders_sl['success'][i]['status'] == 'SLO' or orders_sl['success'][i]['status'] == 'OPN':
            ord_id.append(orders_sl['success'][i]['orderId'])
        
    for j in range(len(ord_id)):
        print(j,' : ',ord_id[j])
        try:
            client.cancel_order(order_id=ord_id[j])
            print('Cancelled Order id :',ord_id[j],'\n')
        except:
            print('Not able to cancel - Stop Loss hit\n')
            continue
        
def cancel_stoploss(client, ticker):
    """Cancel Stop loss order before exiting at internal target"""
    orders_sl = client.order_report()
    for i in range(len(orders_sl['success'])):
        if orders_sl['success'][i]['status'] == 'SLO' and \
            orders_sl['success'][i]['instrumentName'] == ticker:
                temp = orders_sl['success'][i]['orderId']
                try:
                    client.cancel_order(order_id=temp)
                    print('Cancelled order for ',ticker)
                except:
                    print('Not able to cancel - Stop Loss hit\n')
                    continue

"""Execution starts from HERE"""      
"""Getting the dataframe and trading signal"""
samp1 = t.time()
ohlc_data, signal, position_size, position_bool = signals()
sam2 = t.time()
print(sam2-samp1)
print('\n')
"""Exit the code if no signals are there for today"""
sig_list = signal[signal['Signal']!=0].index.tolist()
sig_tick = signal['Ticker'][signal['Signal']!=0].tolist()
if len(sig_list) == 0:
    temp = 'No trades today'
    print(temp)
    message = today + "\n\n" + temp
    # telegram_send.send(messages=[message])      #Telegram message
    client.logout()
    print('Logged Out')
    sys.exit()

print('Stocks that gapped up and generated signals are : ') #Today's signals
print(sig_list,'\n')
message = today + "\n"
for tick_message in sig_list:
    message = message + '\n' + tick_message
# telegram_send.send(messages=[message])      #Telegram message
print(message)
"""Sleep if time != 9.15 am """
cur_time = dt.datetime.now()
pm11=datetime.timestamp(dt.datetime(cur_time.year, cur_time.month, cur_time.day, 9, 15, 2))
pm920=datetime.timestamp(dt.datetime(cur_time.year, cur_time.month, cur_time.day, 9, 20, 0))

if t.time()<pm11:
    sl = pm11-t.time()
    print('Sleeping untill 9:15 for',sl,'seconds')
    try:
        t.sleep(sl)
    except:
        print(dt.datetime.now().time())
        
    
"""Start shorting for stocks that generated signals"""
starttime = t.time()
endtime = datetime.timestamp(dt.datetime(cur_time.year, cur_time.month, cur_time.day, 9, 25, 0))

while t.time() < endtime:
    if t.time()>=pm11 and t.time()<pm920:
        short(client, stocks, signal, position_size, position_bool)
        # init_pos = pos(client)
        print(dt.datetime.now().time())
        break
        # t.sleep(300-((t.time()-starttime)%300.0))
    # if t.time()>=sq_time:
    #     square_off(client, stocks, signal, traded)
    #     break;
    # t.sleep(180-((t.time()-starttime)%180.0))
t.sleep(4)

pos_int = pos(client)
if len(pos_int) == 0:
    print('No positions')
    sys.exit()
print(pos_int)    
print('\n')

init_open_pos = open_pos(client)
print('Initial Positions:-')
print(init_open_pos)

pos_sl_init = client.positions(position_type='OPEN')
exit_signal = target_order(client, stocks, signal, init_open_pos, pos_sl_init)

am920 = datetime.timestamp(dt.datetime(cur_time.year, cur_time.month, cur_time.day, 9, 30, 0))
if t.time() < am920:
    sl3 = am920-t.time()
    print('Sleeping untill 9:30 for',sl3,'seconds')
    t.sleep(sl3)


"""Cancelling the initial target orders"""
order_cancel(client)

"""Client.positions for getting price for stop loss order"""
pos_sl = client.positions(position_type='OPEN')
print(t.localtime(t.time()).tm_hour,':',t.localtime(t.time()).tm_min, \
          ':',t.localtime(t.time()).tm_sec)

sl_order(client, stocks, signal, pos_int, pos_sl)

am930 = datetime.timestamp(dt.datetime(cur_time.year, cur_time.month, cur_time.day, 9, 31, 0))
if t.time()<am930:
    sl2 = am930-t.time()
    print('Sleeping untill 9:31 for',sl2,'seconds')
    t.sleep(sl2)


"""Run the while loop and Exit positions for entered trade if time = 10:55 am"""
start = t.time()
end = datetime.timestamp(dt.datetime(cur_time.year, cur_time.month, cur_time.day, 15, 15, 0))
sq_time = datetime.timestamp(dt.datetime(cur_time.year, cur_time.month, cur_time.day, 15, 0, 0))
while t.time() < end:
    print(t.localtime(t.time()).tm_hour,':',t.localtime(t.time()).tm_min, \
          ':',t.localtime(t.time()).tm_sec)
    try:
        final_pos = open_pos(client)
        print('Positions:-')
        print(final_pos)
    except Exception as e:
        print('Skipped the loop')
    internal_target(client, stocks, exit_signal, final_pos)
    if t.time() >= sq_time:
        order_cancel(client)
        t.sleep(10)
        square_off(client, stocks, signal, final_pos)
        print('\nSquared off all positions\n')
        break
    print('\n\n')
    t.sleep(7-((t.time()-start)%7.0))



exit_pos = open_pos(client)
print('After Exiting :',exit_pos)

"""Succesful - Exit Code"""
print('\nDone For Today :)')
client.logout()
print('Logged Out')
sys.exit()

    

