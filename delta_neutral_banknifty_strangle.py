import logging
import datetime
import pandas as pd
import sys
import os
import time
import pytz
from datetime import date
from kiteconnect import KiteConnect
from influxdb import InfluxDBClient
import def_autotrading as CALL
import calendar
from alice_blue import *

logging.basicConfig(level=logging.DEBUG)

common_location="autotrading/config/common.txt"
common_location = os.path.join(os.path.expanduser('~'), 'documents', 'python', common_location)
param_file=open(common_location,"r")
lines=param_file.readlines()

auto_trade=int(lines[14].split('=')[1].rstrip('\n'))
param_file.close()
print(auto_trade)

q_mul=int(lines[18].split('=')[1].rstrip('\n'))
param_file.close()
print(q_mul)

broker=(lines[20].split('=')[1].rstrip('\n'))
param_file.close()
print(broker)

if(broker=="all"):
    broker=(lines[21].split('=')[1].rstrip('\n'))
    param_file.close()
    print(broker)

#auto_trade=0 ## 1 if actual trade in Kite

dirpath = os.getcwd()
pd.set_option('display.max_columns',20)
print("\nRun Started.......... : ", datetime.datetime.now())

# assuming now contains a timezone aware datetime
now = datetime.datetime.now()
tz = pytz.timezone('Asia/Kolkata')
ind_time=now
ind_time = now.astimezone(tz)
print(ind_time.now().strftime("%Y-%m-%d %H:%M:%S"))

my_date = date.today()
weekday_name = calendar.day_name[my_date.weekday()]
print(weekday_name)

location="autotrading/logs/"+"delta_neutral_banknifty_strangle"+str(datetime.datetime.now())[:-16]+".txt"
script_log_path = os.path.join(os.path.expanduser('~'), 'documents', 'python', location)
print(script_log_path)

stock_name="BANKNIFTY"
script_name="NIFTY BANK"
exchange = "NFO" # CDS NFO NSE
product_type="MIS"
risk_per_trade = 100 # if stoploss gets triggers, you loss will be this, trade quantity will be calculated based on this
trailing_loss = 5
interval="3min"
strategy_name="Delta Neutral Banknifty Strangle"
auto_strategy_name="Delta Neutral Banknifty Auto"
lot_size=CALL.get_lotsize()

f= open(script_log_path,"a+")
f.write("Script started - "+ind_time.now().strftime("%d%m%Y %H:%M:%S")+"\n\n")
f.close()

kite = KiteConnect(api_key="")

###############################################################################
if(broker=="alice" or broker=="all"):
    credentials="autotrading/config/"
    credentials = os.path.join(os.path.expanduser('~'), 'documents', 'python', credentials)
    df=pd.read_csv(credentials+"credentials_active.txt")
    alice = []
    for i in df.index:
        a = AliceBlue(username=str(df['username'][i]),password=df['password'][i],access_token=df['access_token'][i])
        alice.append(a)
###############################################################################

location="autotrading/logs/access_token/token_"+str(date.today())+".txt"
access_token_path = os.path.join(os.path.expanduser('~'), 'documents', 'python', location)
print(access_token_path)

f = open(access_token_path, "r")
get_access_token=f.read(32)
print(get_access_token)
f.close()

kite.set_access_token(get_access_token)

#print(kite.profile())

try:
    db  = InfluxDBClient(host="localhost", port = 8086)
    #db.drop_database(dbname='tradedb')
    #db.create_database('tradedb') # if running first time, remove # to create new database
    db.switch_database('tradedb')
    print(db.get_list_measurements())
except Exception as e:
    location="soft/influxdb/influxd.exe"
    exe_log_path = os.path.join(os.path.expanduser('~'), 'documents', 'python', location)
    print(exe_log_path)
    os.startfile(exe_log_path)
    time.sleep(15)
    db  = InfluxDBClient(host="localhost", port = 8086)
    db.switch_database('tradedb')
    print(db.get_list_measurements())

# db.query("drop measurement daily_trades_status")
# print(db.query("show measurements"))
###############################################################################
def insert_net_db(data,net,net_lot):

    now = datetime.datetime.now()
    tz = pytz.timezone('Asia/Kolkata')
    ind_time = now
    ind_time = now.astimezone(tz)
    ind=0
    json_body = [
                    {
                        "measurement": "daily_trades_status",
                        "tags": {
                            "strategy": data['strategy_name'][ind],
                            "date": (ind_time.now().strftime("%d-%m-%Y"))
                        },
                        "time": ind_time,
                        "fields": {
                            "date": (ind_time.now().strftime("%d-%m-%Y")),
                            "strategy": data['strategy_name'][ind],
                            "hh_mm":data['hh_mm'][ind],
                            "net_pl":net,
                            "net_pl_lot": net/net_lot
                        }
                    }
                    ]
    db.write_points(json_body)
###############################################################################
def insert_db(data,net,net_lot):

    now = datetime.datetime.now()
    tz = pytz.timezone('Asia/Kolkata')
    ind_time = now
    ind_time = now.astimezone(tz)
    ind=0
    json_body = [
                    {
                        "measurement": "daily_trades",
                        "tags": {
                            "strategy": data['strategy_name'][ind],
                            "date": (ind_time.now().strftime("%d-%m-%Y"))
                        },
                        "time": ind_time,
                        "fields": {
                            "date": (ind_time.now().strftime("%d-%m-%Y")),
                            "strategy": data['strategy_name'][ind],
                            "hh_mm":data['hh_mm'][ind],
                            "net_pl":net,
                            "net_pl_lot": net/net_lot
                        }
                    }
                    ]
    db.write_points(json_body)

    sold_premium=0
    for ind in data.index:
        sold_premium=sold_premium+(float(data['ltp'][ind]))
    json_body = [
                    {
                        "measurement": "daily_trades_detail",
                        "tags": {
                            "strategy": data['strategy_name'][0],
                            "date": (ind_time.now().strftime("%d-%m-%Y"))
                        },
                        "time": ind_time,
                        "fields": {
                            "date": (ind_time.now().strftime("%d-%m-%Y")),
                            "strategy": data['strategy_name'][0],
                            "timestamp":data['timestamp'][0],
                            "sold_premium":sold_premium,
                            "net_pl":net
                        }
                    }
                    ]
    db.write_points(json_body)
###############################################################################
script_list = []
def place_order(trans_type,symbol,qty,ltp):
    if(broker=="kite" or broker=="all"):
        global script_list
        order_id=-1
        status="NA"
        message=""
        try:
            order_id = kite.place_order(tradingsymbol=symbol,
                                        exchange=exchange,
                                        transaction_type=trans_type,
                                        quantity=qty,
                                        order_type="MARKET",
                                        price=0,
                                        product=product_type,
                                        validity="DAY",
                                        variety="regular")
            logging.info("Order placed. ID is: {}".format(order_id))
            s=kite.order_history(order_id)
            s=s[-1]
            status= s['status']
            message=s['status_message']
            if message is None:
                message="NA"
            script_list.append(str(order_id)+"|"+symbol+"|"+trans_type+"|"+str(qty)+"|"+str(ltp)+"|"+status+"|"+message)

            try:
                if(status=="COMPLETE"):
                    if(trans_type=="SELL"):
                        trans_type="BUY"
                        sl_mul=1.9
                    else:
                        trans_type="SELL"
                        sl_mul=0.7
                    current_price=CALL.get_ltp(exchange,symbol)
                    order_id = kite.place_order(tradingsymbol=symbol,
                                                exchange=exchange,
                                                transaction_type=trans_type,
                                                quantity=qty,
                                                order_type="SL",
                                                price=int(current_price*sl_mul),
                                                trigger_price=int(current_price*sl_mul),
                                                product=product_type,
                                                validity="DAY",
                                                variety="regular")
                    logging.info("Order placed. ID is: {}".format(order_id))
                    print(order_id)
                    s=kite.order_history(order_id)
                    s=s[-1]
                    status= s['status']
                    message=s['status_message']
                    if message is None:
                        message="NA"
                    script_list.append(str(order_id)+"|"+symbol+"|"+trans_type+"|"+str(qty)+"|"+str(ltp)+"|"+status+"|"+message)
            except Exception as e:
                print(e)

            f= open(script_log_path,"a+")
            f.write(ind_time.now().strftime("%d%m%Y %H:%M:%S"))
            f.write("\n\nKite Orders have been placed. here is the details:\n\n")
            f.write("\n \nOrder_Id|Trading_Symbol|Transaction|Quantity|LTP|Status|Message\n")
            for item in script_list:
                    f.write("%s\n" % item)
            f.close()

        except Exception as e:
         print(e)
         CALL.send_email(symbol+" Order is not completed - " + str(ind_time.now().strftime("%d%m%Y %H:%M:%S")))
         sys.exit()

    if((broker=="alice" or broker=="all") and alice != [] ):
        instruments=alice[0].search_instruments(exchange,stock_name)
        instruments=pd.DataFrame(instruments)
        get_monthly_expiry=instruments['expiry'].tail(3)
        get_monthly_expiry=min(get_monthly_expiry)
        weekly_expiry=instruments.expiry.unique()
        get_weekly_expiry=min(weekly_expiry)

        ce_pe=symbol[-2:]
        if(ce_pe=="CE"):
            ce_pe=True
        else:
            ce_pe=False
        strike=symbol[14:]
        strike=strike[:-2]

        for a in alice:
            instrument = a.get_instrument_for_fno(symbol = stock_name, expiry_date=get_weekly_expiry, is_fut=False, strike=strike, is_CE = ce_pe)
            try:
                a.place_order(transaction_type = TransactionType.Sell,
                                     instrument = instrument,
                                     quantity = qty,
                                     order_type = OrderType.Limit,
                                     product_type = ProductType.Intraday,
                                     price = ltp,
                                     trigger_price = None,
                                     stop_loss = None,
                                     square_off = None,
                                     trailing_sl = None,
                                     is_amo = False)
            except Exception as e:
                print(e)

def place_bo_order(exchange,trans_type,symbol,qty,ltp,target,stoploss,trailing_loss):
    global script_list
    order_id=-1
    status="NA"
    message=""
    try:
        order_id = kite.place_order(exchange=exchange,
                            tradingsymbol=symbol,
                            transaction_type=trans_type,
                            quantity=qty,
                            price=0,
                            product=product_type,
                            order_type="MARKET",
                            validity="DAY",
                            trigger_price="0",
                            # disclosed_quantity=None,
                            squareoff=target,
                            stoploss=stoploss,
                            trailing_stoploss=trailing_loss,
                            variety="bo"
                            )
        logging.info("Order placed. ID is: {}".format(order_id))
        s=kite.order_history(order_id)
        s=s[-1]
        status= s['status']
        message=s['status_message']
        if message is None:
            message="NA"
        script_list.append(str(order_id)+"|"+symbol+"|"+trans_type+"|"+str(qty)+"|"+str(ltp)+"|"+status+"|"+message)

        f= open(script_log_path,"a+")
        f.write(ind_time.now().strftime("%d%m%Y %H:%M:%S"))
        f.write("\n\nKite Orders have been placed. here is the details:\n\n")
        f.write("\n \nOrder_Id|Trading_Symbol|Transaction|Quantity|LTP|Status|Message\n")
        for item in script_list:
                f.write("%s\n" % item)
        f.close()

    except Exception as e:
     print(e)
     CALL.send_email(symbol+" Order is not completed - " + str(ind_time.now().strftime("%d%m%Y %H:%M:%S")))
     sys.exit()

def order_check(script_name,profit_perc,mins,profit):
    global net_pl
    global pl_diff
    pl_diff=0
    net_pl=0
    log_cal = pd.read_csv(csv_file)
    log_cal_new= log_cal.groupby(['symbol']).agg({'ltp': 'mean', 'qty': 'sum', 'sell_price': 'mean', 'buy_price': 'mean', 'profit/loss': 'sum'}).reset_index()
    log_cal=log_cal_new

    try:
        live = kite.positions()
        live = live['net']
        live_pos = [(d['tradingsymbol'],CALL.get_trans_type(d['quantity']),abs(d['quantity']),d['pnl'],d['last_price'],d['exchange'],d['product']) for d in live]
        position_list = live_pos
    except:
        pass

    for ind in log_cal.index:
        symbol=(log_cal['symbol'][ind])
        try:
            net = int(sum(d['pnl'] for d in live if d['tradingsymbol'] == symbol and d['exchange'] == exchange and d['quantity'] != 0))
            #net = int(sum(d['pnl'] for d in live if d['exchange'] == exchange and d['quantity'] != 0))
            net_pl=net_pl+net
        except:
            pass

    d=(ind_time.now().strftime("%d-%m-%Y"))
    query="SELECT max(net_pl) as max_pl FROM daily_trades WHERE (strategy ="+"'"+strategy_name+"'"+" AND date = "+"'"+d+"'"+")"
    print(query)
    result = db.query(query)
    lst = list(result.get_points(measurement='daily_trades'))
    if(lst == [] ):
        max_pl=0
    else:
        max_pl=lst[0]['max_pl']
    print(max_pl)
    pl_diff=max_pl-net_pl

    if(pl_diff>2000):
            CALL.send_telegram("Alert !! - Nifty Current PL: " + str(net_pl) + " Max PL: " + str(max_pl) + " at "+ ind_time.now().strftime("%d%m%Y %H:%M:%S"),"-324028282")

    exit_list=[]
    try:
        print(position_list)
        net = int(sum(d['pnl'] for d in live if d['tradingsymbol'] == script_name))
        net_all = int(sum(d['pnl'] for d in live if d['product'] == product_type))
        msg=script_name+" | Net Position: "+str(net)
        print(msg)
    except:
        net_all=0
        pass

    order_id=-99
    sl_ind=0

    if(net_all>10000):
        CALL.send_telegram("All Nifty Position can be closed: " + str(net_all) + " at "+ ind_time.now().strftime("%d%m%Y %H:%M:%S"),"-324028282")

    ##Real trading
    if((mins<10 and net>1500) or (mins<60 and net>2500) or (mins<120 and net>4000) or (mins<180 and net>6000) or net>8000):
        print(script_name+" - Position can be closed: " + str(net) + " at "+ ind_time.now().strftime("%d%m%Y %H:%M:%S"))
        sl_ind=1
        #CALL.send_telegram(script_name+" - Position can be closed: " + str(net) + " Profit %:"+str(profit_perc)+ " Mins:"+str(mins),"-324028282")

    ##Mock trading
    if(profit_perc>30 or (mins<10 and profit>1500) or (mins<60 and profit>2500) or (mins<120 and profit>4000) or (mins<180 and profit>6000)):
        sl_ind=1
        sl_mul=1.5
        #CALL.send_telegram(script_name+" - Winning Position can be closed: " + str(profit) + " Profit %:"+str(profit_perc)+ " Mins:"+str(mins),"-324028282")

    if(profit_perc>60):
        sl_ind=1
        sl_mul=1.4

    if(profit_perc>70):
        sl_ind=1
        sl_mul=1.3

    if(profit_perc>80):
        sl_ind=1
        sl_mul=1.2

    if(profit<-2500 or profit_perc<-50):
        CALL.send_telegram(script_name+" - Losing Position can be closed: " + str(profit) + " Profit %:"+str(profit_perc)+ " Mins:"+str(mins),"-324028282")

    if(sl_ind==1):
        try:
            current_price=CALL.get_ltp(exchange,script_name)
            orders = kite.orders()
            for order in orders:
                if (order['product']=='MIS' and order['tradingsymbol']==script_name and order['status'] == 'TRIGGER PENDING'):
                    print(order['tradingsymbol'])
                    quantity=order['quantity']
                    transaction_type=order['transaction_type']
                    if(transaction_type=="SELL"):
                        sl_mul=2-sl_mul
                    order_id=order['order_id']
                    kite.modify_order(variety="regular",
                                        order_id=order_id,
                                        quantity=quantity,
                                        order_type="SL",
                                        price=int(current_price*sl_mul),
                                        trigger_price=int(current_price*sl_mul),
                                        validity="DAY")
            s=kite.order_history(order_id)
            s=s[-1]
            status= s['status']
            message=s['status_message']
            if message is None:
                message="NA"
            exit_list.append("close_position"+"|"+order_id+"|"+script_name+"|"+transaction_type+"|"+str(quantity)+"|"+str(current_price)+"|"+status+"|"+message)
            print(exit_list)
        except:
            pass

        # f= open(script_log_path,"a+")
        # f.write("\nClosing position...")
        # f.write("\n \nFunction_Name|Order_Id|Trading_Symbol|Transaction_Completed|Quantity|Price\n")
        # for item in exit_list:
        #     f.write("%s\n" % item)
        # f.write("\nPosition Closed: " + str(net) + " at "+ ind_time.now().strftime("%d%m%Y %H:%M:%S"))
        # f.close()
    print(script_name+": " + str(net) + " at "+ ind_time.now().strftime("%d%m%Y %H:%M:%S"))
    print("--------------------------------------------------------------------")
    print("Total Profit/Loss: " + str(net_pl))
    print("--------------------------------------------------------------------")
###############################################################################
def technical_check(stock_name):
    global trade
    try:
        RSI_Score=CALL.get_RSI(float(CALL.get_technical("RSI",stock_name,"5min",14)))+CALL.get_RSI(float(CALL.get_technical("RSI",stock_name,"10min",14)))
        print(RSI_Score) #>6 bullish and <-6 bearish

        lst=CALL.get_technical("ADX",stock_name,"5min",14)
        print(lst)
        if(lst[1]>27 and lst[1]>lst[2] and lst[0]>27 and lst[2]<15):
            adx_5="Buy"
        elif(lst[2]>27 and lst[1]<lst[2] and lst[0]>27 and lst[1]<15):
            adx_5="Sell"
        else:
            adx_5="Neutral"
        print(adx_5)

        if((RSI_Score>=5 and adx_5=="Buy") or RSI_Score>=6):
            trade="Buy"
        elif((RSI_Score<=-5 and adx_5=="Sell") or RSI_Score<=-6):
            trade="Sell"
        else:
            trade="Neutral"

        token=CALL.get_token("NSE","INDIA VIX")
        quote=CALL.get_quote(token)
        vix_close=quote[str(token)]['ohlc']['close']
        net_change=quote[str(token)]['net_change']
        per_change=(net_change/vix_close)*100
        print(per_change)

        if(per_change>10):
            trade="High Vix"

    except Exception as e:
        print(e)
        print(CALL.get_technical("RSI","NIFTY","5min",14))
        print(CALL.get_technical("ADX","NIFTY","5min",14))

    return trade
###############################################################################
orderslist = []
buylist =[]
selllist = []

location="autotrading/data/pl/"
csv_file_path= os.path.join(os.path.expanduser('~'), 'documents', 'python', location)
print(csv_file_path)

hh_mm="09-35"#(ind_time.now().strftime("%H-%M"))
csv_file=csv_file_path+strategy_name+"_"+stock_name.lower()+"_"+str(date.today())+"_"+hh_mm+".csv"
print(csv_file)
total_qty=0
pl_diff=0
trade="Neutral"
tt_ind=0
###############################################################################
prev_ltp=0
position="close"
def run_strategy():
    global idx
    global runcount
    global prev_ltp
    global position
    global tt_ind
    ready="N"

    if(position=="close"):

        market=CALL.check_market(stock_name)
        print(market)

        trade=technical_check(stock_name)
        print(trade)

        if(market=="Perfect Sideways"):
            lot=-2*q_mul
        elif(market=="Sideways" or market=="Neutral"):
            lot=-2*q_mul
        elif(market=="Bullish" or market=="Bearish" or trade!="Neutral"):
            lot=-1*q_mul
        else:
            lot=-2*q_mul

        while(ready=="N" and runcount==0):
            c=CALL.get_ltp("NSE","NIFTY BANK")
            r=100*round(float(c)/100)
            trade=technical_check(stock_name)
            if((abs(c-r)<30) and trade=="Neutral"):
                ready="Y"
            else:
                print("Waiting for ready state!!"+str(c)+"|"+str(r)+"|"+str(prev_ltp))
                time.sleep(10)

        try:
            log = pd.read_csv(csv_file)
            idx= log['timestamp'].count()
        except Exception as e:
            print(e)
            log = pd.DataFrame(columns=['csv_file','auto_strategy_name','strategy_name','hh_mm','timestamp','symbol','ltp','qty','sell_price','buy_price','profit/loss','sl-hit','high','low','volume'])
            idx=0

        if((trade=="Buy" or trade=="Sell") and tt_ind==0 and (weekday_name=="Monday" or weekday_name=="Friday")):
            if(trade=="Buy"):
                item=CALL.get_delta_leg(0.22)
                print(item)
                item1=CALL.get_delta_leg(0.36)
                print(item1)
                item2=CALL.get_delta_leg(-0.20)
                print(item2)
            elif(trade=="Sell"):
                item=CALL.get_delta_leg(-0.22)
                print(item)
                item1=CALL.get_delta_leg(-0.36)
                print(item1)
                item2=CALL.get_delta_leg(0.20)
                print(item2)

            qty=lot_size*lot
            try:
                ltp=CALL.get_ltp(exchange,item)
            except Exception as e:
                print(e)
                ltp=CALL.get_ltp(exchange,item)
            if(auto_trade==1):
                    place_order("SELL",item,abs(qty),ltp)

            log.loc[idx]=[csv_file,auto_strategy_name,strategy_name,hh_mm,ind_time.now(),item,ltp,qty,ltp,0,0,'No',0,0,0]
            idx=idx+1

            item=item1
            qty=lot_size*int(abs(lot)/2)
            try:
                ltp=CALL.get_ltp(exchange,item)
            except Exception as e:
                print(e)
                ltp=CALL.get_ltp(exchange,item)
            if(auto_trade==1):
                    place_order("BUY",item,abs(qty),ltp)

            log.loc[idx]=[csv_file,auto_strategy_name,strategy_name,hh_mm,ind_time.now(),item,ltp,qty,0,ltp,0,'No',0,0,0]
            idx=idx+1

            item=item2
            qty=lot_size*lot
            try:
                ltp=CALL.get_ltp(exchange,item)
            except Exception as e:
                print(e)
                ltp=CALL.get_ltp(exchange,item)
            if(auto_trade==1):
                    place_order("SELL",item,abs(qty),ltp)

            log.loc[idx]=[csv_file,auto_strategy_name,strategy_name,hh_mm,ind_time.now(),item,ltp,qty,ltp,0,0,'No',0,0,0]
            idx=idx+1

            tt_ind=1
        else:
            symbol_ce_name=CALL.get_delta_leg(0.25)
            symbol_pe_name=CALL.get_delta_leg(-0.22)

            try:
                symbol_ce_ltp=CALL.get_ltp(exchange,symbol_ce_name)
                symbol_pe_ltp=CALL.get_ltp(exchange,symbol_pe_name)
            except Exception as e:
                print(e)
                symbol_ce_ltp=CALL.get_ltp(exchange,symbol_ce_name)
                symbol_pe_ltp=CALL.get_ltp(exchange,symbol_pe_name)

            if(symbol_pe_ltp==0 or symbol_ce_ltp==0):
                print("LTP can not be zero")
                sys.exit()

            qty=lot_size*lot

            if(auto_trade==1):
                place_order("SELL",symbol_ce_name,abs(qty),symbol_ce_ltp)
                place_order("SELL",symbol_pe_name,abs(qty),symbol_pe_ltp)

            log.loc[idx]=[csv_file,auto_strategy_name,strategy_name,hh_mm,ind_time.now(),symbol_ce_name,symbol_ce_ltp,qty,symbol_ce_ltp,0,0,'No',0,0,0]
            idx=idx+1
            log.loc[idx]=[csv_file,auto_strategy_name,strategy_name,hh_mm,ind_time.now(),symbol_pe_name,symbol_pe_ltp,qty,symbol_pe_ltp,0,0,'No',0,0,0]
            idx=idx+1

        log.to_csv(csv_file, index=False)

        prev_ltp=CALL.get_ltp("NSE","NIFTY BANK")
        position="open"

    cal_pl(csv_file)
    #check_delta_neutral(csv_file)

    print('     Waiting for schedule interval...', datetime.datetime.now())
###############################################################################
check_points=220
def cal_pl(csv_file):
    global total_qty
    global prev_ltp
    global position
    global check_points
    global runcount
    #prev_ltp=11950
    try:
        log_cal = pd.read_csv(csv_file)
        Net_PL=0
        Pos_PL=0
        total_qty=0
        stop_time = int(15) * 60 + int(22)  # square off all open positions
        all_pos_list=''

        index_ltp=CALL.get_ltp("NSE","NIFTY BANK")

        if(abs(index_ltp-prev_ltp)>check_points):
            position="close"
            runcount=0
            check_points=220
            print("Ready to close the current position...")
        else:
            print("Monitoring the current position...")

        for ind in log_cal.index:
            try:
                token=CALL.get_token(exchange,log_cal['symbol'][ind])
                quote=CALL.get_quote(token)
            except Exception as e:
                print(e)
                token=CALL.get_token(exchange,log_cal['symbol'][ind])
                quote=CALL.get_quote(token)

            high=quote[str(token)]['ohlc']['high']
            low=quote[str(token)]['ohlc']['low']
            ltp=quote[str(token)]['last_price']

            log_cal['ltp'][ind]=ltp

            log_cal['high'][ind]=float(high)
            log_cal['low'][ind]=float(low)

            if(int(log_cal['qty'][ind])<0):
                sell_price=float(log_cal['sell_price'][ind])
                qty=abs(int(log_cal['qty'][ind]))
                log_cal['buy_price'][ind]=ltp

                if(log_cal['sl-hit'][ind]=='No'):
                    log_cal['profit/loss'][ind]=(sell_price-ltp)*qty

                if(position=="close" and log_cal['sl-hit'][ind]=='No'):
                    sl_time=ind_time.now().strftime("%H:%M:%S")
                    if(auto_trade==1):
                        close_all(csv_file)
                    log_cal['sl-hit'][ind]='Yes - '+str(ltp)+' - '+str(sl_time)
                    print("Closing the current position...")

            if(int(log_cal['qty'][ind])>0):
                buy_price=float(log_cal['buy_price'][ind])
                qty=abs(int(log_cal['qty'][ind]))
                log_cal['sell_price'][ind]=ltp

                if(log_cal['sl-hit'][ind]=='No'):
                    log_cal['profit/loss'][ind]=(ltp-buy_price)*qty

                if(position=="close" and log_cal['sl-hit'][ind]=='No'):
                    sl_time=ind_time.now().strftime("%H:%M:%S")
                    if(auto_trade==1):
                        close_all(csv_file)
                    log_cal['sl-hit'][ind]='Yes - '+str(ltp)+' - '+str(sl_time)
                    print("Closing the current position...")

            if(log_cal['sl-hit'][ind]=='No'):
                Pos_PL = Pos_PL + log_cal['profit/loss'][ind]

            Net_PL = Net_PL + log_cal['profit/loss'][ind]
            total_qty=total_qty + qty
            all_pos_list=all_pos_list+log_cal['symbol'][ind]+": "+str(log_cal['profit/loss'][ind])+"\n"

            if(position=="close"):
                print("--------------------------------------")
                print("Ready to close the current position...")
                print("Closed: " + str(log_cal['symbol'][ind]) +" | PL: "+str(log_cal['profit/loss'][ind]))
                print("Prev LTP: "+str(prev_ltp)+" | LTP: "+str(index_ltp)+" | Check Points: "+str(check_points))
                print("--------------------------------------")
            else:
                print("--------------------------------------")
                print("Monitoring the current position...")
                print("Open: " + str(log_cal['symbol'][ind]) +" | PL: "+str(log_cal['profit/loss'][ind]))
                print("Prev LTP: "+str(prev_ltp)+" | LTP: "+str(index_ltp)+" | Check Points: "+str(check_points))
                print("--------------------------------------")

        print("Open Postions Net Profit/Loss: "+ str(Pos_PL))
        net_lot=int(total_qty/lot_size)
        log_cal.to_csv(csv_file,index=False)
        insert_db(log_cal,Net_PL,net_lot)
        print("Net Profit/Loss: "+ str(Net_PL))

        if(position=="close" and Net_PL>15000*q_mul):
            insert_net_db(log_cal,Net_PL,net_lot)
            CALL.send_telegram(("Delta Neutral Banknifty Strangle"+" - Net Profit/Loss: "+ str(Net_PL) +"\n\n"+ all_pos_list),"369004870")
            if(auto_trade==1):
                close_all(csv_file)
            sys.exit()
        elif(position=="close" and Pos_PL>5000*q_mul):
            CALL.send_telegram(("Alert - Delta Neutral Banknifty Strangle"+" - Net Profit/Loss: "+ str(Pos_PL) +"\n\n"+ all_pos_list),"369004870")
            print('     Waiting for 15 Mins...', datetime.datetime.now())
            time.sleep(900)
        elif(position=="close" and Pos_PL>3000*q_mul):
            print('     Waiting for 15 Mins...', datetime.datetime.now())
            time.sleep(900)
        elif(position=="close"):
            print('     Waiting for 10 Mins...', datetime.datetime.now())
            time.sleep(600)

        if(position=="open"):
            if(Pos_PL>5000*q_mul and check_points==100):
                check_points=50
            elif(Pos_PL>3500*q_mul and check_points==140):
                check_points=100
            elif(Pos_PL>2500*q_mul and check_points==180):
                check_points=140
            elif(Pos_PL>1500*q_mul and check_points==220):
                check_points=180

        no_trade_time=int(14) * 60 + int(45)
        if(position=="close" and (datetime.datetime.now().hour * 60 + datetime.datetime.now().minute) >= no_trade_time and weekday_name!="Thursday"):
            print('     Waiting for Closing the Market...', datetime.datetime.now())
            time.sleep(1000)

        if (datetime.datetime.now().hour * 60 + datetime.datetime.now().minute) >= stop_time:
            insert_net_db(log_cal,Net_PL,net_lot)
            #update_gsheet(log_cal)
            csv_name=((csv_file.rsplit('/',1))[1])
            print(csv_name+" - Net Profit/Loss: "+ str(Net_PL))
            CALL.send_telegram(("Delta Neutral Banknifty Strangle"+" - Net Profit/Loss: "+ str(Net_PL) +"\n\n"+ all_pos_list),"369004870")
            if(auto_trade==1):
                send_status(csv_file)

    except Exception as e:
        print(e)
###############################################################################
def check_delta_neutral(csv_file):
    lst = []
    log = pd.read_csv(csv_file)
    global idx
    global pl_diff
    global total_qty
    trade_time=int(12) * 60 + int(35)
    no_trade_time=int(14) * 60 + int(40)

    try:
        live = kite.positions()
        live = live['net']
        live_pos = [(d['tradingsymbol'],CALL.get_trans_type(d['quantity']),abs(d['quantity']),d['pnl'],d['last_price'],d['exchange'],d['product']) for d in live]
        position_list = live_pos
    except:
        pass

    if(auto_trade==1):
        for ind in log.index:
            for item in position_list:
                if(item[0]==(log['symbol'][ind]) and item[1]!="XX" and item[6]==product_type):
                    qty=item[2]
                    if(item[1]=="SELL"):
                        lst.append(log['symbol'][ind]+"|"+str(qty))
                        lst=list(dict.fromkeys(lst))
    else:
        for ind in log.index:
            if(log['sl-hit'][ind]=="No"):
                if(log['qty'][ind]<0):
                    lst.append(log['symbol'][ind]+"|"+str(abs(log['qty'][ind])))

    print(lst)

    total_delta = CALL.get_total_delta(lst)
    print(total_delta)

    ref_p=0.20
    ref_n=-0.18

    if((datetime.datetime.now().hour * 60 + datetime.datetime.now().minute) <= no_trade_time):
        if(total_delta>ref_p or total_delta<ref_n): #pl_diff>2000

            delta=total_delta

            new_leg=CALL.get_delta_leg(delta*-1)
            symbol=new_leg

            try:
                ltp=CALL.get_ltp(exchange,symbol)
            except Exception as e:
                print(e)
                ltp=CALL.get_ltp(exchange,symbol)

            qty=lot_size*-1 #int(abs(delta)/ref_p)

            if(auto_trade==1):
                place_order("SELL",symbol,abs(qty),ltp)
                #place_bo_order(exchange,"SELL",symbol,abs(qty),ltp,ltp*0.2,ltp*2,trailing_loss)

            log.loc[idx]=[csv_file,auto_strategy_name,strategy_name,hh_mm,ind_time.now(),symbol,ltp,qty,ltp,0,0,'No',0,0,0]
            idx=idx+1
            log.to_csv(csv_file,index=False)

            CALL.send_telegram(("Delta Neutral: \n"+"Total Delta: "+ str(total_delta)+"\nPosition Added: "+symbol+"|"+str(qty)+"\nDelta: "+str(delta*-1)+"\nPL Diff: "+ str(pl_diff)),"-324028282")

        elif(total_qty<450 and ((datetime.datetime.now().hour * 60 + datetime.datetime.now().minute) > trade_time)):

            symbol_ce_name=CALL.get_delta_leg(0.20)
            symbol_pe_name=CALL.get_delta_leg(-0.18)

            try:
                symbol_ce_ltp=CALL.get_ltp(exchange,symbol_ce_name)
                symbol_pe_ltp=CALL.get_ltp(exchange,symbol_pe_name)
            except Exception as e:
                print(e)
                symbol_ce_ltp=CALL.get_ltp(exchange,symbol_ce_name)
                symbol_pe_ltp=CALL.get_ltp(exchange,symbol_pe_name)

            ce_qty=lot_size*-2
            pe_qty=lot_size*-2

            if(symbol_pe_ltp==0 or symbol_ce_ltp==0):
                print("LTP can not be zero")
                sys.exit()

            if(auto_trade==1):
                place_order("SELL",symbol_ce_name,abs(ce_qty),symbol_ce_ltp)
                place_order("SELL",symbol_pe_name,abs(pe_qty),symbol_pe_ltp)

            log.loc[idx]=[csv_file,auto_strategy_name,strategy_name,hh_mm,ind_time.now(),symbol_ce_name,symbol_ce_ltp,ce_qty,symbol_ce_ltp,0,0,'No',0,0,0]
            idx=idx+1
            log.loc[idx]=[csv_file,auto_strategy_name,strategy_name,hh_mm,ind_time.now(),symbol_pe_name,symbol_pe_ltp,pe_qty,symbol_pe_ltp,0,0,'No',0,0,0]
            idx=idx+1

            log.to_csv(csv_file,index=False)
        else:
            print("No adjustment required. Total Delta: "+ str(total_delta)+" PL Diff: "+ str(pl_diff))
    else:
        cal_pl(csv_file)
        print("No adjustment required. Total Delta: "+ str(total_delta)+" PL Diff: "+ str(pl_diff))
###############################################################################
def close_all(csv_file):
    if(broker=="kite" or broker=="all"):
        exit_list=[]
        position_list=[]
        log_cal = pd.read_csv(csv_file)
        log_cal_new= log_cal.groupby(['symbol']).agg({'ltp': 'mean', 'qty': 'sum', 'sell_price': 'mean', 'buy_price': 'mean', 'profit/loss': 'sum'}).reset_index()
        log_cal=log_cal_new
        pending_list=[]

        try:
            live = kite.positions()
            live = live['net']
            live_pos = [(d['tradingsymbol'],CALL.get_trans_type(d['quantity']),abs(d['quantity']),d['pnl'],d['last_price'],d['exchange'],d['product']) for d in live if d['exchange'] == exchange and d['product'] == product_type]
            position_list = live_pos
        except:
            live = kite.positions()
            live = live['net']
            live_pos = [(d['tradingsymbol'],CALL.get_trans_type(d['quantity']),abs(d['quantity']),d['pnl'],d['last_price'],d['exchange'],d['product']) for d in live]
            position_list = live_pos
            pass

        for item in position_list:
            for ind in log_cal.index:
                symbol=(log_cal['symbol'][ind])
                if (item[0] == symbol and item[1]!="XX" and item[6]==product_type):
                    pending_list.append(item)
        print("-------------------------Outside While------------------------")
        print(pending_list)
        print("--------------------------------------------------------------")

        while(pending_list != []):
            try:
                live = kite.positions()
                live = live['net']
                live_pos = [(d['tradingsymbol'],CALL.get_trans_type(d['quantity']),abs(d['quantity']),d['pnl'],d['last_price'],d['exchange'],d['product']) for d in live if d['exchange'] == exchange and d['product'] == product_type]
                position_list = live_pos
            except:
                pass

            for item in position_list:
                for ind in pending_list:
                    if (item[0] == ind[0] and item[1]=="XX" and item[6]==product_type):
                        print(item)
                        try:
                            pending_list.remove(ind)
                        except:
                            pass
            print("-------------------------Inside While ------------------------")
            print(pending_list)
            print("--------------------------------------------------------------")

            orders = kite.orders()
            for ind in log_cal.index:
                symbol=(log_cal['symbol'][ind])
                for order in orders:
                    if (order['tradingsymbol']==symbol and order['product']==product_type and order['exchange']==exchange and (order['status'] == 'TRIGGER PENDING' or order['status'] == 'OPEN')):
                        print(order['tradingsymbol'])
                        cancel_id = kite.cancel_order(variety=order['variety'], order_id=order['order_id'],
                                                      parent_order_id=order['parent_order_id'])
                        print('cancelled', cancel_id)


            if(pending_list != []):
                for ind in log_cal.index:
                    for item in pending_list:
                        if(item[0]==(log_cal['symbol'][ind]) and item[1]!="XX" and item[6]==product_type):
                            symbol=(log_cal['symbol'][ind])
                            quantity=abs((log_cal['qty'][ind]))
                            qty=item[2]
                            trans_type=item[1]
                            current_price=CALL.get_ltp(exchange,symbol)
                            order_id = kite.place_order(tradingsymbol=symbol,
                                                        exchange=exchange,
                                                        transaction_type=trans_type,
                                                        quantity=qty,
                                                        order_type="LIMIT",
                                                        price=current_price,
                                                        product=product_type,
                                                        validity="DAY",
                                                        variety="regular")
                            logging.info("Order placed. ID is: {}".format(order_id))
                            print(order_id)
                            s=kite.order_history(order_id)
                            s=s[-1]
                            status= s['status']
                            message=s['status_message']
                            if message is None:
                                message="NA"
                            exit_list.append("close_position"+"|"+order_id+"|"+symbol+"|"+"BUY"+"|"+str(quantity)+"|"+str(current_price)+"|"+status+"|"+message)

            print(exit_list)
            f= open(script_log_path,"a+")
            f.write("\nFinal Closing of the Day !!!")
            f.write("\n \nFunction_Name|Order_Id|Trading_Symbol|Transaction_Completed|Quantity|Price\n")
            for item in exit_list:
                f.write("%s\n" % item)
            f.close()
            
            time.sleep(1)
        print("Closed Kite Positions...")

    if((broker=="alice" or broker=="all") and alice != [] ):
        position_list=[]
        instruments=alice[0].search_instruments(exchange,stock_name)
        instruments=pd.DataFrame(instruments)
        get_monthly_expiry=instruments['expiry'].tail(3)
        get_monthly_expiry=min(get_monthly_expiry)
        weekly_expiry=instruments.expiry.unique()
        get_weekly_expiry=min(weekly_expiry)

        log_cal = pd.read_csv(csv_file)
        log_cal_new= log_cal.groupby(['symbol']).agg({'ltp': 'mean', 'qty': 'sum', 'sell_price': 'mean', 'buy_price': 'mean', 'profit/loss': 'sum'}).reset_index()
        log_cal=log_cal_new

        for a in alice:
            pending_list=[]
            try:
                live = a.get_daywise_positions()
                live = live['data']
                live= live['positions']
                live_pos = [(d['trading_symbol'],CALL.get_trans_type(d['net_quantity']),abs(d['net_quantity']),d['m2m'],d['ltp'],d['exchange'],d['product']) for d in live if d['exchange'] == exchange and d['product'] == product_type]
                position_list = live_pos
            except:
                live = a.get_daywise_positions()
                live = live['data']
                live= live['positions']
                live_pos = [(d['trading_symbol'],CALL.get_trans_type(d['net_quantity']),abs(d['net_quantity']),d['m2m'],d['ltp'],d['exchange'],d['product']) for d in live]
                position_list = live_pos
                pass

            for item in position_list:
                for ind in log_cal.index:
                    symbol=(log_cal['symbol'][ind])
                    if (item[0] == symbol and item[1]!="XX" and item[6]==product_type):
                        print(item)
                        pending_list.append(ind)
                        
            print("-------------------------Outside While -----------------------")
            print(pending_list)
            print("--------------------------------------------------------------")

            while(pending_list != []):

                try:
                    live = a.get_daywise_positions()
                    live = live['data']
                    live= live['positions']
                    live_pos = [(d['trading_symbol'],CALL.get_trans_type(d['net_quantity']),abs(d['net_quantity']),d['m2m'],d['ltp'],d['exchange'],d['product']) for d in live if d['exchange'] == exchange and d['product'] == product_type]
                    position_list = live_pos
                except:
                    pass

                for item in position_list:
                    for ind in pending_list:
                        if (item[0] == ind[0] and item[1]=="XX" and item[6]==product_type):
                            print(item)
                            try:
                                pending_list.remove(item)
                            except:
                                pass
                
                print("-------------------------Inside While ------------------------")
                print(pending_list)
                print("--------------------------------------------------------------")

                orders = a.get_order_history()
                orders=orders['data']
                orders=orders['pending_orders']

                for ind in log_cal.index:
                    symbol=(log_cal['symbol'][ind])
                    for order in orders:
                        if (order['trading_symbol']==symbol):
                            print(order['trading_symbol'])
                            cancel_id = a.cancel_order(order['oms_order_id'])
                            print('cancelled', cancel_id)
                if(pending_list != []):
                    for ind in log_cal.index:
                        for item in pending_list:
                            if(item[0]==(log_cal['symbol'][ind]) and item[1]!="XX" and item[6]==product_type):
                                symbol=(log_cal['symbol'][ind])
                                ce_pe=symbol[-2:]
                                if(ce_pe=="CE"):
                                    ce_pe=True
                                else:
                                    ce_pe=False
                                strike=symbol[14:]
                                strike=strike[:-2]
                                instrument = a.get_instrument_for_fno(symbol = stock_name, expiry_date=get_weekly_expiry, is_fut=False, strike=strike, is_CE = ce_pe)

                                quantity=abs((log_cal['qty'][ind]))
                                qty=item[2]
                                trans_type=item[1]
                                if(trans_type=="BUY"):
                                    order_id = a.place_order(transaction_type = TransactionType.Buy,
                                                                    instrument = instrument,
                                                                    quantity = qty,
                                                                    order_type = OrderType.Market,
                                                                    product_type = ProductType.Intraday,
                                                                    price = 0.0,
                                                                    trigger_price = None,
                                                                    stop_loss = None,
                                                                    square_off = None,
                                                                    trailing_sl = None,
                                                                    is_amo = False)
                                if(trans_type=="SELL"):
                                    order_id = a.place_order(transaction_type = TransactionType.Sell,
                                                                    instrument = instrument,
                                                                    quantity = qty,
                                                                    order_type = OrderType.Market,
                                                                    product_type = ProductType.Intraday,
                                                                    price = 0.0,
                                                                    trigger_price = None,
                                                                    stop_loss = None,
                                                                    square_off = None,
                                                                    trailing_sl = None,
                                                                    is_amo = False)
                                logging.info("Order placed. ID is: {}".format(order_id))
                time.sleep(1)
        print("Closed Alice Positions...")
###############################################################################
def send_status(csv_file):
    log_cal = pd.read_csv(csv_file)
    log_cal_new= log_cal.groupby(['symbol']).agg({'ltp': 'mean', 'qty': 'sum', 'sell_price': 'mean', 'buy_price': 'mean', 'profit/loss': 'sum'}).reset_index()
    log_cal=log_cal_new
    if((broker=="alice" or broker=="all") and alice != []):
        for a in alice:
            profile=a.get_profile()
            profile=profile['data']
            aliceuser=profile['name']
            net_pl=0
            try:
                live = a.get_daywise_positions()
                live = live['data']
                live= live['positions']
                live_pos = [(d['trading_symbol'],CALL.get_trans_type(d['net_quantity']),abs(d['net_quantity']),d['m2m'],d['ltp'],d['exchange'],d['product']) for d in live]
                position_list = live_pos
            except:
                pass

            for ind in log_cal.index:
                symbol=(log_cal['symbol'][ind])
                try:
                    net = int(sum(float(d['m2m']) for d in live if d['trading_symbol'] == symbol and d['exchange'] == exchange and d['product'] == product_type))
                    net_pl=net_pl+net
                except:
                    pass
            print("Total Profit/Loss: " + str(net_pl))
            CALL.send_telegram(("Status: "+aliceuser+"\n\n"+"Delta Neutral Banknifty Strangle"+" - Net Profit/Loss: "+ str(net_pl)),"369004870")

    if(broker=="kite" or broker=="all"):
        try:
            profile=kite.profile()
            username=profile['user_name']
        except:
            username="Jaydeep Patel"
        net_pl=0
        try:
            live = kite.positions()
            live = live['net']
            live_pos = [(d['tradingsymbol'],CALL.get_trans_type(d['quantity']),abs(d['quantity']),d['pnl'],d['last_price'],d['exchange'],d['product']) for d in live]
            position_list = live_pos
        except:
            pass

        for ind in log_cal.index:
            symbol=(log_cal['symbol'][ind])
            try:
                net = int(sum(d['pnl'] for d in live if d['tradingsymbol'] == symbol and d['exchange'] == exchange and d['product'] == product_type))
                net_pl=net_pl+net
            except:
                pass
        CALL.send_telegram(("Status: "+username+"\n\n"+"Delta Neutral Banknifty Strangle"+" - Net Profit/Loss: "+ str(net_pl)),"369004870")
###############################################################################

def run():
    global runcount
    global prev_ltp
    global position
    start_time = int(9) * 60 + int(25)  # specify in int (hr) and int (min) foramte
    end_time = int(14) * 60 + int(59)  # do not place fresh order
    stop_time = int(15) * 60 + int(23)  # square off all open positions
    last_time = start_time
    schedule_interval = 60  # run at every 3 min
    missed_time=int(12) * 60 + int(50)

    if((datetime.datetime.now().hour * 60 + datetime.datetime.now().minute) > missed_time):
        runcount = 3
        prev_ltp=CALL.get_ltp("NSE","NIFTY BANK")
        position="open"


    while True:
        if (datetime.datetime.now().hour * 60 + datetime.datetime.now().minute) >= end_time:
            if (datetime.datetime.now().hour * 60 + datetime.datetime.now().minute) >= stop_time:
                if(auto_trade==1):
                    close_all(csv_file)
                cal_pl(csv_file)
                break

        elif (datetime.datetime.now().hour * 60 + datetime.datetime.now().minute) >= start_time:
            if time.time() >= last_time:
                last_time = time.time() + schedule_interval
                print("\n\n {} Run Count : Time - {} ".format(runcount, datetime.datetime.now()))
                if runcount >= 0:
                    try:
                        run_strategy()
                    except Exception as e:
                        print("Run error", e)
                runcount = runcount + 1
        else:
            print('     Waiting...', datetime.datetime.now(),'|prev_ltp:',str(prev_ltp))
            time.sleep(1)
runcount = 0

run()
