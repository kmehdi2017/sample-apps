# -*- coding: utf-8 -*-
"""

Author: Mehdi Khan

"""
import os
import matplotlib 
matplotlib.use('Agg')
import time
import pandas as pd
import numpy as np
import requests
import datetime
import pymongo
from flask import Flask, render_template, request 
import base64
import io
import matplotlib.pyplot as plt

#libraries for ARIMA
from statsmodels.tsa.stattools import acf, pacf
#from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.arima_model import ARIMA

#Libraries for LSTM
import keras
from keras.models import Sequential #load_model
from keras.layers import Activation, Dense
from keras.layers import LSTM
from keras.layers import Dropout
from sklearn.preprocessing import MinMaxScaler
#from sklearn.metrics import mean_squared_error
#from sklearn.model_selection import train_test_split
from sklearn.utils import shuffle

app = Flask(__name__)
keras.backend.backend()
# Shows the main page
@app.route("/")
def show_main_page():
    return render_template('main.html', msg = "!! WELCOME !!")

# calls reset_account() function, which connects to mongoDB and deletes all the trading history 
# and profit/loss information and finally sets the initial cash account to its original value of $1000,000
@app.route("/reset")
def reset_account():
    msgreset= db_reset()
    return render_template('main.html', msg = msgreset)

# route to url of trade.html, which contains the main functionalities of the site  
@app.route("/trade")
def show_trade_screen():
    marketlist = get_Markets()['MarketCurrency']
    plot_url="/static/coinlogo.png"
    return render_template('trade.html', tickerlist=marketlist,plot_url=plot_url)


# trigers the execute_trade2 function when user wants to see the price, market status 
# and statistics or execute the trade from inside the trade.html. other functions are called such as
# get_Markets() to get the market and currency information, find_price_crypto() to get the price
# information, plotdata() to create the chart and graphics, get_twentyfourhr_stat() to get 24 hours statistics
# of the selected currency. At the end, the output of all these functions are sent as variables to be rendered 
# in the html    


@app.route("/submitTrade",methods=['POST'])
def execute_trade2():
    
    marketlist = get_Markets()['MarketCurrency']      
    ticker = request.form['symbol']
    option = request.form['side'] 
    if option=='B':    
        Side = 'Buy'       
    elif option == 'S':
        Side = 'Sell' 
          
    if request.form['trade']=="View Current Data and Prediction":        
        price_info = find_price_crypto(ticker,option)
        price = price_info['price']
        msg=""
        if price == 0:
            msg = price_info['msg']
            return render_template('trade.html', msg = msg,tickerlist=marketlist)
        else:
            future_price,dockermsg = get_predicted_price(ticker)
            
            price= str(round(price,2))            
            plot_url = plotdata(ticker)
            labelsymbol = "Your selected currency: " 
            predictedsymbol = "Predicted closing price for next 7 days"
            labelside = "Trading option: "
            labelprice = "Price: $" 
            plot_url = plot_url.decode('utf8')
            plot_url = "data:image/png;base64,"+ plot_url
            statistics = get_twentyfourhr_stat(ticker)
            titleStat = "24 hours open, close, low and high price statistics for "+ticker
            mx = statistics.loc[statistics.Statistics=="Maximum price"]["high"]
            mn = statistics.loc[statistics.Statistics=="Minimum price"]["low"]
            n = statistics.loc[statistics.Statistics=="count"]["low"]  
            mx =float(mx)
            mn = float(mn)
            n = float(n)
            av = round(mx+mn/n,2)
            titleStat2 = "24 Hour Maximum: "+str(mx)+" || 24 Hour Minimum: "+str(mn)+" || 24 Hour average: "+ str(av)
            statisticsDF=statistics[1:]
            return render_template('trade.html',dockerError=dockermsg,predictprice=predictedsymbol,predicted=future_price.to_html(index=False,classes="tradeTbl"),tickerlist=marketlist, txtStat=titleStat,txtStat2=titleStat2,plot_url=plot_url,currentSymbol=ticker,side=option,price=price,tradeopt=Side,lblside=labelside, lblsymbol=labelsymbol,lblprice=labelprice, stat=statisticsDF.to_html(index=False,classes="statTable"))
        
    if request.form['trade']== "Execute Trade":            
        if (ticker is None) or (ticker==""):
            ticker = request.form['currency']
            if (ticker is None) or (ticker==""):
                msg = "No Symbol information was entered...!!"
                return render_template('trade.html', msg = msg,tickerlist=marketlist)        
            option = request.form['opt']
            if (option is None) or (option ==""):                
                option = request.form['side'] 
                 
        quantity = request.form['quantity']        
        msg =  execute_BuySell(option,ticker,quantity)
        return render_template('trade.html', msg = msg,tickerlist=marketlist)
   


##background process happening without any refreshing
@app.route('/background_process_test')
def background_process_test():
    print ("Hello")
    return "nothing" 
        
 
# show_blotter() function is called when routed to the url for blotter page. This function calls get_BlotterData()
# to get trading information in a dataframe which is passed as a variable to be rendered in the html page as a table.
@app.route("/blotter")
def show_blotter():
    show = get_BlotterData()
    return render_template("blotter.html", data=show.to_html(index=False,classes="tradeTbl"))

# execute_pl() function is called when routed to the url for PL page. This function calls updateUpl()  
# to get PL information in a dataframe which is passed as a variable to be rendered in the html page as a table.
@app.route("/pl")
def execute_pl():      
    statusDF = updateUpl() 
    wap_plot,portfolioPL_plot,cash_price_pl = plot_PL_timeSeries()
    wap_plot = wap_plot.decode('utf8')
    wap_plot = "data:image/png;base64,"+ wap_plot
    portfolioPL_plot = portfolioPL_plot.decode('utf8')
    portfolioPL_plot = "data:image/png;base64,"+ portfolioPL_plot
    cash_price_pl = cash_price_pl.decode('utf8')
    cash_price_pl = "data:image/png;base64,"+ cash_price_pl
    return render_template('pl.html',data=statusDF.to_html(index=False,classes="tradeTbl"),wapgraph=wap_plot,plgraph=portfolioPL_plot,price_cashgraph=cash_price_pl) 
# The application uses mongoDB to store and retrieve all trading information. This mongoDB in hosted in the cloud
#  (mongoDB Atlas ), the below statement connects to the mongoDB. Note: for this project no effort was made to hide
# the connection string
myMongo = pymongo.MongoClient("mongodb://data602:Assignment2018@khandb-shard-00-00-gwmns.mongodb.net:27017,khandb-shard-00-01-gwmns.mongodb.net:27017,khandb-shard-00-02-gwmns.mongodb.net:27017/test?ssl=true&replicaSet=khanDB-shard-0&authSource=admin")

    

# The do_transaction() takes four parameters: the type of trade, the quantity, trading price and
# the symbol information. This function does all the actions relevant to trading i.e. updates
# inventory and cash values, updates RPL if the trading option is a sell, retrieve and store 
# all data into  mongoDB and finally returns all the transaction information as a DICT object. 
# It calls get_statusDF() function that returns a dataframe with the current trading status of a currency and 
# information are checked and updated based on the current status     
def do_transaction(side,qty,price,ticker):
    
    # referencing mongoDB
    db = myMongo.predictionDB    
    
    statusDF = get_statusDF()
    
    #get cash amount before the transaction
    cash = round(get_currentBalance(),2)
    msg = ""     
    try:        
        qua = int(qty)
        if qua < 1:
            msg = "The quantity must be positive and at least 1 !!"
            return msg
    except ValueError:    
            msg = "Invalid quantity...please try again !!"            
            return msg   
    else:
        # cost calculation
        cost = qua * price
        if side == 'Buy':
            # update cash and quantity information for a buy
            if cash >= cost:
                cash =  cash - cost
                db.Status_data.update_one({"Ticker":ticker},{"$inc":{"Inventory":qua}})
                update_currentBalance(cash)                 
                
            else:
                msg = "!!!! you don't have enough fund to buy !!!!"                        
                return msg
        
        elif side == 'Sell':
            # update cash and quantity and RPL information for a sell and writes to the database
            if statusDF[statusDF.Ticker == ticker].Inventory.iloc[0] >= qua:
                cash =  cash + cost
                update_currentBalance(cash)                
                db.Status_data.update_one({"Ticker":ticker},{"$inc":{"Inventory":-qua}})
                wap = statusDF[statusDF.Ticker == ticker].WAP.iloc[0]                
                p_rpl = statusDF[statusDF.Ticker == ticker].RPL.iloc[0]               
                rpl = round((p_rpl + (qua * (price-wap))),2)               
                
                db.Status_data.update_one({"Ticker":ticker},{"$set":{"RPL":rpl}})
            else:
                msg = "!!!! you don't have enough "+ ticker + " to sell !!!!"                
                return msg    
        
        db.Status_data.update_one({"Ticker":ticker},{"$set":{"Market Price":price}})
        
        t = time.strftime("%m/%d/%Y %I:%M %p")
        # cretae and returns a dict oobject with transaction information
        transaction = {"Side":side,"Ticker":ticker,"Quantity":qua,"Price":price,"Time":t,"Money_IN/OUT":cost,"Cash":cash}
       
    return transaction


# updateWap takes five parameters: previous wap, previous quantity, trading price, 
# current quantity and the trading currency. It does an arithmetic  operation to calculate the WAP after the
# current buy of the selected currency and update the WAP information in the database.
def updateWap(oldwap,oldqty,price,newqty,stock):
    db = myMongo.predictionDB
    WAP = ((oldwap * oldqty) + (price * newqty))/(oldqty+newqty)
    # round WAP to 2 decimals
    WAP = round(WAP,2)
    db.Status_data.update_one({"Ticker":stock},{"$set":{"WAP":WAP}})
    
    # creating record for wap update history
    collection = db.Wap_data
    t = time.strftime("%m/%d/%Y %I:%M %p")
    collection.insert_one({'Ticker':stock, 'WAP':WAP, 'time':t})
    return  
      

# updateUpl() function calls get_statusDF() and find_price_crypto function() to get the most recent trading price, current WAP and
# inventory information, estimate UPL values of the currencies and update UPL column of statusDF dataframe with 
# updated UPL values. Since this information is dynamic and recalculated every time the function is called this function
# does not store any value in the database. It returns all these information in dataframe to be viewed in P/L screen
def updateUpl():      
    statusDF = get_statusDF()
    
      
    mkt =[]
    wap =[]
    pos =[]
     
    # collect the most up to date price for each currency
    # and relavnt wap and stock volume to calculate UPL 
    for index,item in enumerate(statusDF.Ticker):
         if statusDF.Ticker.values[index] == 'CASH':             
             statusDF = statusDF[statusDF.Ticker != 'CASH']
         elif statusDF.iloc[index]['Inventory'] == 0:
             mkt.append(0)
             wap.append(0)
             pos.append(0)
             statusDF.loc[index, "WAP"] = 0
         else:    
             mkt.append(find_price_crypto(item,'S')['price'])
             wap.append(statusDF.iloc[index]['WAP'])
             pos.append(statusDF.iloc[index]['Inventory']) 
             
             # round WAP to 2 decimals
             wap = [round(elem,2) for elem in wap]
             
    # estimate UPL value
    diff = np.subtract(mkt,wap)
    upl = np.multiply(diff,pos)
    
    # round UPL to 2 decimals
    upl = [round(elem,2) for elem in upl]
  
    # update UPL column in the statusDF dataframe
    statusDF['UPL'] = upl
    
    statusDF['Total PL'] =  statusDF.RPL + upl 
    alloShare = round((statusDF.Inventory/sum(pos)) * 100,2)   
    alloDollar = round((statusDF.WAP/sum(wap)) * 100,2)      
    statusDF['Share Allocation'] = alloShare.astype(str)+"%"
    statusDF['Dollar Allocation'] = alloDollar.astype(str)+"%"
    # add available cash amount
    remaining_cash = round(get_currentBalance(),2)
    statusDF.loc[len(statusDF.index)+1] = ['CASH','$'+str(remaining_cash),"","","","","","",""]
    
    # add a record for total P/L history
    db = myMongo.predictionDB
    collection = db.Portfolio_PL
    t = time.strftime("%m/%d/%Y %I:%M %p")
    sum_pl = np.float64(statusDF['Total PL'].values[:len(statusDF['Total PL'].values)-1])
    sum_pl = np.round(sum_pl.sum(),3)
    collection.insert_one({'Portfolio PL':sum_pl, 'time':t})
    
    return statusDF
 
        
# The find_price_crypto function takes two parameters: the ticker and the trading option. The function uses Bitterex API to 
# retrieve cryptocurrency price based on the trading option (ask for buy and bid for sell) from the BITTEREX exchange. 
# This function collects data only from currencies in USDT market. If for any reason the price information is not available 
# it show a message asking to try trading later. After retrieving the price information it converts the price into float. It
# finally returns the price value ( price = 0 if no valid price is found) along with a message string as a dict object.  
def find_price_crypto(name,opt): 
    
    url="https://bittrex.com/api/v1.1/public/getticker?market=USDT-"+ name
   
    msg=""
    
    if (name is None) or (name == "") or (opt is None) or (opt==""):
        price = 0
        msg = "Symbol or a trading option was not entered....please check !!"
    else:
        req = requests.get(url).json()
        if req['success'] == True:   
            if opt=='B':
                price = req['result']['Ask']
            elif opt=='S':
                price = req['result']['Bid']
            try:
                if type(price) != float:
                    price = float(price)                     
            except ValueError:
                msg = "Price is NOT available!!!....try again later...."   
            
        else:
            msg = "Price is NOT available!!!....try again later...."
            price = 0
   
    priceinfo = {'price': price, 'msg':msg}        
       
    return priceinfo


# The project is limited to only the USDT market in the BITTEREX exchange. The get_Markets() function finds the 
# market information and returns only the USDT market information in a dataframe. It uses API provided by BITTEREX
def get_Markets():
    market = requests.get("https://bittrex.com/api/v1.1/public/getmarkets").json()
    marketDF = pd.DataFrame(market['result'])
    marketDF = marketDF.loc[marketDF['BaseCurrency']=='USDT']
    return marketDF


# get_marketHistory () uses cryptocompare.com is used to get the historical information of a given currency through API provided by cryptocompare.com 
# the crytocompare.com was selected since it collects information from several exchanges and provides  better insights 
# of a currency's trading information and market status. The function returns historical data based on the time specified. 
def get_marketHistory(name, timespan):
    hist_data = requests.get("https://min-api.cryptocompare.com/data/histoday?fsym="+name+"&tsym=USDT&limit="+timespan+"&aggregate=1&e=CCCAGG").json()
    historyDF = pd.DataFrame(hist_data['Data'])   
    return historyDF

# get_twentyfourhr_stat() collects 24 hours trading information of a given currency through API provided by cryptocompare.com
# the crytocompare.com was selected since it collects information from several exchanges and provides a better insight 
# of a currency's trading information and market status. The function returns statistical information of the data
# in a dataframe
def get_twentyfourhr_stat(ticker):    
    hourlydata = requests.get("https://min-api.cryptocompare.com/data/histohour?fsym="+ticker+"&tsym=USDT&limit=24&aggregate=3&e=CCCAGG").json()
    hourlyDF= pd.DataFrame(hourlydata['Data']) 
    hourlyDF = hourlyDF.iloc[:,0:4].describe().reset_index()   
    statDF = round(hourlyDF,2).iloc[[0,1,2,3,7]]
    statDF['index']=  ["count","Mean price","Standard Deviation","Minimum price","Maximum price"]
    statDF = statDF.rename(columns={'index':'Statistics'})    
    return statDF


# moving_average() function takes two parameters- a pandas Series with 100 day price information and a number (for number of days)
# and uses numpy's convolve method to create moving average price for the given number of days. 
def moving_average(data, days):
    data = np.asarray(data)   
    weight = np.ones(days) 
    wt = weight.sum()
    weight /= wt    
    mv = np.convolve(data, weight, mode='full')[:len(data)]
    mv[:days] = mv[days]
    return mv

# plotdata() function takes the selected currency as its parameter and calls get_marketHistory() function
# to get the 100 day market history. It also calls moving_average() function for moving average data and uses
# matplotlib library to plot all those data. The resulting plot is saved in .png format and returned as Base64 
# encoded string.
def plotdata(currency):
    mkt_hist = get_marketHistory('BTC','100')
    mkt_hist = get_marketHistory(currency,'100')    
    mkt_hist.time = mkt_hist.time.astype(int)
    mkt_hist.time = mkt_hist.time.apply(lambda x: datetime.datetime.fromtimestamp(x).strftime('%m/%d/%Y'))

    mkt_hist['moving average'] = moving_average(mkt_hist.low, 20)
    mkt_hist.reset_index()   
    
    fig, (ax,ax2,ax3) = plt.subplots(nrows = 3, ncols=1)    
    ax.set(xlabel="Date", ylabel="Value in USD")
    ax2.set(xlabel="Date", ylabel="Value in USD")    
    ax3.set(xlabel="Date", ylabel="Value in USD")
    
    mkt_hist.plot(x='time', y= ['high','low'],ax=ax, style=['r','k--'], grid=True, sharex=True, figsize=(10,8), title="100 days high and low")
    mkt_hist.plot(x='time', y= ['open','close'],ax=ax2, style=['b','g--'], grid=True, sharex=True,title="100 days open and close" )
    mkt_hist.plot.area(x='time', y=['moving average'],ax=ax3, style=['b'], alpha=0.25, grid=True, title="20 days moving average" )
    
    img = io.BytesIO()
    plt.savefig (img, format='png')
    img.seek(0)    
    plot_url =base64.b64encode(img.getvalue())
   
    return plot_url
   
    
    
#  write_Blotter_ToMongo () function connects to mongoDB in the cloud and save information of each transaction.
def write_Blotter_ToMongo(blotterData):
    db = myMongo.predictionDB
    collection = db.trade_data
    collection.insert_one(blotterData)
    return

#  get_BlotterData() function connects to mongoDB in the cloud, retrieve transaction data and return them
# as a dataframe
def get_BlotterData():
    db = myMongo.predictionDB
    collection = db.trade_data
    cursor = collection.find()
    blotterList = []
    for record in cursor:
        blotterList.append(record)
        
    blotterDF = pd.DataFrame(blotterList,columns=["Side","Ticker","Quantity","Price","Money_IN/OUT","Time","Cash"])  
    
    return blotterDF

# get_currentBalance() function connects to mongoDB in the cloud, retrieve the available fund data and return the
# fund/cash information
def get_currentBalance():
    db = myMongo.predictionDB
    balance = 0
    balance = float(db.cash_balance.find_one({},{"current_balance":1})['current_balance'])
    if balance is  None:
        print("Could access to available funds")          
    return balance

# update_currentBalance function takes the current balance as it's parameter, connects to mongoDB in the cloud, 
# and save current balance information in the database.
def update_currentBalance(balance):
    db = myMongo.predictionDB
    balance_id = db.cash_balance.find_one({},{'_id':1})['_id']
    db.cash_balance.update_one({"_id":balance_id},{"$set":{"current_balance":balance}})
    return


# write_StatusDF takes the currency name and trading option (sell or buy) as its parameter, connects to 
# mongoDB in the cloud and creates a record if the currency is being traded for the first time. 
def write_StatusDF(name, selloption):
    db = myMongo.predictionDB
    collection = db.Status_data
    try:
        test = len(collection.find_one({'Ticker':name}))
    except TypeError:
        collection.insert_one({'Ticker':name,'Inventory':0,'Market Price':0,'UPL':0,'RPL':0,'WAP':0,'Total PL':0,'Share Allocation':0,'Dollar Allocation':0}) 
        if selloption == 'S':
                print ("\n",(' ' *24),"!!!You do not own", name, "selcet another stock!!!...")
    return


# get_statusDF()connects to mongoDB in the cloud, retrieve trading information for each individual currency and return
# information as a dataframe.      
def get_statusDF():
    db = myMongo.predictionDB
    collection = db.Status_data
    cursor = collection.find()
    statusList = []
    for record in cursor:
        statusList.append(record)
        
    DF = pd.DataFrame(statusList,columns=["Ticker","Inventory","Market Price","UPL","RPL","WAP","Total PL","Share Allocation","Dollar Allocation"]) 
    return DF


# The execute_BuySell function takes three parameters - the symbol of a currency and trade option i.e. buy or sell
# and the quantity. The function calls other functions (find_price_crypto and do_transaction) to retrieve the latest price information and
# to complete the requested transaction. It looks at the previous position/inventory, and WAP information 
# and update WAP if the trading option is a buy. Finally the function saves transaction info) in the database and
# returns a message with success or error information. 
def execute_BuySell(tradeoption,name,qty):    
       
    if tradeoption=='B':    
        Side = 'Buy'       
    elif tradeoption == 'S':
        Side = 'Sell'
           
    # update data in mongoDB
    write_StatusDF(name, tradeoption)
   
    # get status information
    statusDF = get_statusDF()
    # get previous position and WAP information
    #if name in statusDF["Ticker"].values:
    p_inventory = statusDF[statusDF.Ticker == name].Inventory.iloc[0]
    p_wap = statusDF[statusDF.Ticker == name].WAP.iloc[0] 
    
    # get the current trading price
    s_price = find_price_crypto(name,tradeoption)['price']
    
    no_stocks = qty
    transaction = do_transaction(Side,no_stocks,s_price,name)                            
    
    # Write transaction data to mongoDB Atlas 
    if isinstance(transaction, dict):         
        write_Blotter_ToMongo(transaction)
    else:
        return transaction
    
    # update WAP after every buy
    if Side == "Buy":             
                try:
                    updateWap(p_wap,p_inventory,s_price,transaction['Quantity'],name)
                except TypeError:
                    msg = "!!Some invaild values were entered, please check!!"
                    return msg
            
            #check if sell transaction was valid
    try:
        was_transaction = transaction['Quantity']
    except TypeError:
        msg = "Transaction Error, Try again"
        return msg
    
    else:                
        msg = "!!!! Your transaction is complete !!!!"                
        return msg

#The function connects to mongoDB and deletes all the trading history and profit/loss information 
#and finally sets the initial cash account to its original value of $1000,000 and takes the user to the initial screen. 
def db_reset():
    db = myMongo.predictionDB
    rs = db.Status_data.delete_many({})
    rs2 = db.trade_data.delete_many({})   
       
    delblotter = rs2.deleted_count
    delpl = rs.deleted_count        
        
    balance_id = db.cash_balance.find_one({},{'_id':1})['_id']
    db.cash_balance.update_one({"_id":balance_id},{"$set":{"current_balance":1000000}})
    
    msg = "!!!Deleted "+str(delblotter)+ " blotter and "+str(delpl)+" P/L records, your cash account has been reset !!!"
    return msg


def get_PL_TimeSeriesData():
    price_and_cash = get_BlotterData()
    price_and_cash = price_and_cash[['Price','Cash','Time']]
    
    db = myMongo.predictionDB  
    
    cursor = db.Wap_data.find()
    Wap_history = []
    for record in cursor:
        Wap_history.append(record)
    WapDF = pd.DataFrame(Wap_history,columns=["Ticker","time","WAP"])
    
    cursor = db.Portfolio_PL.find()
    all_PL = []
    for record in cursor:
        all_PL.append(record)
    portfolio_PLDF = pd.DataFrame(all_PL,columns=["time","Portfolio PL"])    
    
    return price_and_cash, WapDF, portfolio_PLDF

def plot_PL_timeSeries():
    priceCash_historyDF, WAP_historyDF, PL_historyDF = get_PL_TimeSeriesData()
    WAP_historyDF = WAP_historyDF.assign(Time=pd.to_datetime(WAP_historyDF['time']))
    PL_historyDF = PL_historyDF.assign(Time=pd.to_datetime(PL_historyDF['time']))
    WAP_historyDF = WAP_historyDF.drop('time', axis=1)
    PL_historyDF = PL_historyDF.drop('time',axis=1)
    statusDF = get_statusDF()
       
    unique_ticker = WAP_historyDF['Ticker'].unique()
    fig, axes = plt.subplots(len(unique_ticker), 1,  figsize=(8,10)) 
    plt.subplots_adjust(hspace=.85)
    
    for i, name in enumerate(unique_ticker):
        axes[i].set(xlabel="Date", ylabel="Value in USD")
        axes[i].title.set_size(9)
        axes[i].tick_params(direction='out', length=6, width=2, color='g', labelsize=8)
        df_subset = WAP_historyDF[WAP_historyDF.Ticker==name]
        df_subset.plot(x='Time', y= ['WAP'],ax=axes[i], style=['r'], grid=True,  title="WAP for: "+ name,rot=15)
    
    img = io.BytesIO()
    plt.savefig (img, format='png')
    img.seek(0)    
    wapplot_url =base64.b64encode(img.getvalue())
    pfPL_url = plotPLgraphs(PL_historyDF,['Portfolio PL'],['g'],"Portfolio PL")
    cash_price_url = plotPLgraphs(priceCash_historyDF,['Price','Cash'],['b'],"Executed price and cash position")
    return wapplot_url,pfPL_url,cash_price_url
    
   
def plotPLgraphs(df,yval,stl,title):
    fig,ax = plt.subplots(nrows = 1, ncols=1)  
    ax.set(xlabel="Date/time", ylabel="Value in USD")  
    df.plot(x='Time', y= yval,ax=ax, style=stl, grid=True,figsize=(8,3), title=title,rot=35)
    img = io.BytesIO()
    plt.savefig (img, format='png')
    img.seek(0)    
    plt_url =base64.b64encode(img.getvalue())
    return plt_url
     

        
   
   

################ Machine learning algorithms######################

# TimeSeries Analaysis with ARIMA and LSTM RNN models

# collection of two years historic data  

# make a timeseris enabled dataset 
def get_ts(df): 
    historyDF = df
    historyDF.time = historyDF.time.apply(lambda x: datetime.datetime.fromtimestamp(x).strftime('%m/%d/%Y'))
    historyDF.time=pd.to_datetime(historyDF['time'], format='%m/%d/%Y')
    historyDF = historyDF.set_index('time')
    historyDF = historyDF[~(historyDF['close'] == 0)]
    return historyDF.close



### Decision making process with Time Series data
# The following functions were created to analize and visualize the data, the trend, and check stationarity, ways of finding and eliminating trends
# and finally find the right model (in this case ARIMA)

# plotting the data for a visual interpretation:
# ts_plots takes a cruptocurrency dataset (dataframe) as its parameter and create a histogram and line plot in respect to time  
# of the 'close' price of the currency. In this context both selected currencies clearly shows a trend over time.
def ts_plots(historyDF):
    historyDF.plot(historyDF.index,'close')
    
    bns = int(historyDF.shape[0]/15)
    lowest =  min(historyDF['close'].astype(int));
    highest =  max(historyDF['close'].astype(int))
    #breaks = np.linspace(lowest, highest, num=bns+1)
    data = historyDF['close'].astype(int)
    matplotlib.pyplot.hist(data, bins=bns, range=(lowest,highest))
    
# the check_stationarity function was taken from online blogs (see the reference) below that 
#takes a timeseries datas as input and use  
# rolling statistics  along with Dickey-Fuller test to check the stationarity
# of the data. It plots and prints all the relevant data to explore data stationarity 
# reference: https://www.analyticsvidhya.com/blog/2016/02/time-series-forecasting-codes-python/
def check_stationarity(ts):
    
    #Determing rolling statistics
    rolmean = pd.rolling_mean(ts, window=40)
    rolstd = pd.rolling_std(ts, window=40)

    #Plot rolling statistics:
    orig = matplotlib.pyplot.plot(ts, color='blue',label='Original')
    mean = matplotlib.pyplot.plot(rolmean, color='red', label='Rolling Mean')
    std = matplotlib.pyplot.plot(rolstd, color='black', label = 'Rolling Std')
    matplotlib.pyplot.legend(loc='best')
    matplotlib.pyplot.title('Rolling Mean & Standard Deviation')
    matplotlib.pyplot.show(block=False)
    
    #Perform Dickey-Fuller test:
    print ('Results of Dickey-Fuller Test:')
    dftest = adfuller(ts, autolag='AIC')
    dfoutput = pd.Series(dftest[0:4], index=['Test Statistic','p-value','#Lags Used','Number of Observations Used'])
    for key,value in dftest[4].items():
        dfoutput['Critical Value (%s)'%key] = value
    print (dfoutput)
 
#Note: After checking the selected currencies' stationarity at appeared that 
      # the standrad deviation, the mean all are changing with time, so the data is not stationary. 
    
# Trend and seasonality elimination 
   
      
      
      
# After checking several process it was decided that data will be log transformed so the difference between higher and lower values are atjusted, then differencing 
# will be used to smooth the data, a 15 days (two weeks) lag was used. The  transformation_differencing functiobn take timeseried data
# and do the job as mentioned above abd return a log transformed data with difference in time lags
      
def transformation_differencing(ts):
    data_log =np.log(ts)
    difference = data_log - data_log.shift(1)
    difference.dropna(inplace=True)
    return difference, data_log      

# The create_acf_pcf function returns and plot auto corelation function and partial autocorelatioin  functions to decide the 
# p and q parametaers of an ARIMA model
# p – The lag value where the PACF chart crosses the upper confidence interval for the first time. 
# q – The lag value where the ACF chart crosses the upper confidence interval for the first time. 

def create_acf_pcf (difference):
    acf_ = acf(difference, nlags=15)
    pacf_ = pacf(difference, nlags=15, method='ols')

#Plot ACF: 
    matplotlib.pyplot.subplot(121) 
    matplotlib.pyplot.plot(acf_)
    matplotlib.pyplot.axhline(y=0,linestyle='--',color='gray')
    matplotlib.pyplot.axhline(y=-1.96/np.sqrt(len(difference)),linestyle='--',color='gray')
    matplotlib.pyplot.axhline(y=1.96/np.sqrt(len(difference)),linestyle='--',color='gray')
    matplotlib.pyplot.title('Autocorrelation Function')

#Plot PACF:
    matplotlib.pyplot.subplot(122)
    matplotlib.pyplot.plot(pacf_)
    matplotlib.pyplot.axhline(y=0,linestyle='--',color='gray')
    matplotlib.pyplot.axhline(y=-1.96/np.sqrt(len(difference)),linestyle='--',color='gray')
    matplotlib.pyplot.axhline(y=1.96/np.sqrt(len(difference)),linestyle='--',color='gray')
    matplotlib.pyplot.title('Partial Autocorrelation Function')
    matplotlib.pyplot.tight_layout()


# While the acf and pcf plots generated by the above function suggests p = 2, and q = 2, in reallity 0 for both 
# values provided a better result

# The ARIMA model and forecasting
# The forecastpriceARIMA function creates an ARIMA model and forecast the closing price of the 
# currency for the next 7 days
def forecastpriceARIMA(tsdata,p,q):
    model = ARIMA(tsdata, order=(p, 1,q))  
    modelResult= model.fit(disp=-1)  
    next_dates = [ tsdata.index[-1] + datetime.timedelta(days=i) for i in range(7) ]
       
    forecast = pd.Series(modelResult.forecast(steps=7)[0],next_dates)
    forecast = np.exp(forecast)
    return forecast
 
    

############# LSTM RNN
## normalization of data with Min-Max scaling. With this scaling the crypto currency closeing price data 
# is scaled  to a fix range of 0 to 1. This is an alternative of z-score standardization although
# it can potentially cause suppresion of outlier effects because of smaller standard deviation.
# typical neural network algorithm require data that on a 0-1 scale
scaler = MinMaxScaler(feature_range=(0, 1))

# the moving_window takes a number (window size) and a dataframe as its parameters. It shifts 
# column by 1 each time until it reaches the number of times specfied in the window size
# and then concatenate the shifted column to the original data  and finally returns  a datafrme with number of columns 
#as specified by the window size plus one. 

# The concept:  Throgh this process a long series can be sliced intoto smaller sizes. The benefit
# of doing this isto reduce the length of the sequence. And it can be very useful by customizing the 
# number of previous timesteps to predict the current timestep that can give a LSTM model a better 
# learning experience.
# In this context a 30 days windows were considered. i.e 30 days of price data would be used in every single 
# input (X) to predict the 31nd day price (y) and so on. 
def moving_window(windowsize,ds):
    copy_ds = ds.copy()
    for i in range(windowsize):
        ds = pd.concat([ds, copy_ds.shift(-(i+1))], axis = 1)
    ds.dropna(axis=0,inplace=True)
    return ds

# The scaleddata function scaled down the input data beetween 0 to 1 
def scaleddata(ds):    
    dataset = scaler.fit_transform(ds.values)
    dataset = pd.DataFrame(dataset)
    return dataset

#  create_model_dataset returns 4 sets of dataset (train X,y and Test X,y), with 80% are for training the model and
# 20% for testing the model. 
def create_model_dataset(df,ratio =.8):
    size = round(df.shape[0] * ratio)
    train = df.iloc[:size,:]
    test = df.iloc[size:,:]
    train = shuffle(train)
    trainx = train.iloc[:,:-1].values
    trainy = train.iloc[:,-1].values
    testx = test.iloc[:,:-1].values
    testy = test.iloc[:,-1].values
    return trainx,trainy,testx,testy

# create_lstm_model creates the LSTM RNN model. 
# A double stacked LSTM layers are used, by setting return_sequences = True it was ensured that
# For every input to the first layer an output will be fed to second LSTM layer. 
def create_lstm_model(data, activation="linear",l="mse",opt="adam"):
    model = Sequential()
    model.add(LSTM(input_shape = (data.shape[1],data.shape[2]), output_dim= data.shape[1], return_sequences = True))
    model.add(Dropout(0.5))
    model.add(LSTM(256))
    model.add(Dropout(0.5))
    model.add(Dense(1))
    model.add(Activation(activation))
    model.compile(loss=l, optimizer=opt)
    #model.summary()
    return model
    
    
# sevendays_forecast function predict futre 7 days' prices. Basically the model predicts one at 
# a time for seven times, after each prediction the predicted data is added back to to the input dataset 
# (and the oldest data is removed from the stack) to make prediction for the next timestep.
def sevendays_forecast(testx, model):
    forecasts =[]
    pred_data = [testx[0,:].tolist()]
    pred_data = np.array(pred_data)
    for i in range(7):
        prediction = model.predict(pred_data)
        forecasts.append(prediction[0,0])
        prediction = prediction.reshape(1,1,1)
        pred_data = np.concatenate((pred_data[:,1:,:],prediction),axis=1)
    
    forecasts = np.array(forecasts)
    forecasts = forecasts.reshape(-1,1)
    forecasts = scaler.inverse_transform(forecasts)    
    return forecasts

# all_future_price function add all the predictions done by both models
# and returns a dataframe of the combined data. 
def all_future_price(arima,lmts,currency):
     ds = pd.DataFrame(arima)
     ds.index = ds.index.strftime('%m/%d/%Y')
     ds.columns=[currency+' ARIMA Price']
     ds.iloc[:,0] = round(ds.iloc[:,0],3)
     if lmts != 'NA':    
        lmts = lmts.astype('float64')
        ds[currency+' LSTM Price'] = lmts
        ds.iloc[:,1] = round(ds.iloc[:,1],3) 
        msg = ""
     else:
        msg = "LSTM model prediction could not be available because of DOCKER issue"
         
     ds = ds.reset_index()
     ds = ds.rename(columns={'index':'Prediction Dates'})        
     return ds, msg 
    

# get_predicted_price basically calls the previous function to create the historic
# dataset, create the LSTM model and finally predict the data along with all the 
# required intermediate steps

def get_predicted_price(name):
# collection of two years historic data 
    df = get_marketHistory(name, '730')

#########ARIMA model steps###################
    TS = get_ts(df)
    TSDiff, data_log = transformation_differencing(TS) 
    ARIMA_forecast = forecastpriceARIMA(data_log,0,1)



#LSTM RNN model steps
    LSTMds = TS.reset_index()
# no need for datetime data
    LSTMds = LSTMds.drop('time', axis=1)

# scale data
    LSTM_dataset = scaler.fit_transform(LSTMds.values)
    LSTM_dataset_scaled = pd.DataFrame(LSTM_dataset)

    LSTM_window = moving_window(30,LSTM_dataset_scaled)
    TrainX,TrainY,TestX,TestY = create_model_dataset(LSTM_window)

# reshape input to be [samples, time steps, features]
    TrainX = np.reshape(TrainX, (TrainX.shape[0], TrainX.shape[1], 1))
    TestX = np.reshape(TestX, (TestX.shape[0], TestX.shape[1],1))
    
    

    try:        
        LSTM_model = create_lstm_model(TestX, activation="linear",l="mse",opt="adam")
    except ValueError:         
        forecasted_price = all_future_price(ARIMA_forecast,'NA',name)            
        return forecasted_price  
    else:
        LSTM_model.fit(TrainX,TrainY,batch_size=512,epochs=3,validation_split=0.1)
        predicts = LSTM_model.predict(TestX)
        predicts = scaler.inverse_transform(predicts)
    
        LSTM_future_price = sevendays_forecast(TestX,LSTM_model)
    
        forecasted_price,msgstr = all_future_price(ARIMA_forecast,LSTM_future_price,name)
        keras.backend.clear_session()
        return forecasted_price, msgstr
    




if __name__ == '__main__':
     port = int(os.environ.get('PORT', 5000))
     app.run(host='0.0.0.0', port=port )
     
     